"""Finite I-11 checks for exact glyph-candidate recognition."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import contextlib
import io
import unittest

import core_0_1_glyph_encoding as encoding
import core_0_1_glyph_recognizer as recognizer
import core_0_1_lexical_frontend as lexical
import core_0_1_source_profile as source_profile


class GlyphRecognizerTests(unittest.TestCase):
    def test_outcome_spellings_are_exact_external_contract_terms(self) -> None:
        self.assertEqual(
            tuple(outcome.value for outcome in recognizer.RecognitionOutcome),
            ("RECOGNIZED", "UNRECOGNIZED", "INVALID_INPUT"),
        )

    def test_each_approved_scalar_recognizes_exact_design(self) -> None:
        for item in encoding.APPROVED_GLYPH_ENCODINGS:
            result = recognizer.recognize_glyph_candidate(item.scalar)
            self.assertIs(result.outcome, recognizer.RecognitionOutcome.RECOGNIZED)
            self.assertEqual(result.design_id, item.design_id)
            self.assertEqual(result.code_point_label, item.code_point_label)

    def test_ascii_candidate_is_unrecognized_without_repair(self) -> None:
        result = recognizer.recognize_glyph_candidate("rb.g2")
        self.assertIs(result.outcome, recognizer.RecognitionOutcome.UNRECOGNIZED)

    def test_unmapped_private_use_scalar_is_unrecognized(self) -> None:
        result = recognizer.recognize_glyph_candidate("\uE105")
        self.assertIs(result.outcome, recognizer.RecognitionOutcome.UNRECOGNIZED)

    def test_multiple_mapped_scalars_are_one_unrecognized_candidate(self) -> None:
        candidate = encoding.APPROVED_SCALARS[0] + encoding.APPROVED_SCALARS[1]
        result = recognizer.recognize_glyph_candidate(candidate)
        self.assertIs(result.outcome, recognizer.RecognitionOutcome.UNRECOGNIZED)
        self.assertIsNone(result.design_id)

    def test_surrounding_whitespace_is_not_trimmed(self) -> None:
        scalar = encoding.APPROVED_SCALARS[0]
        for candidate in (" " + scalar, scalar + " ", "\t" + scalar, scalar + "\n"):
            self.assertIs(
                recognizer.recognize_glyph_candidate(candidate).outcome,
                recognizer.RecognitionOutcome.UNRECOGNIZED,
            )

    def test_empty_candidate_is_invalid_input(self) -> None:
        self.assertIs(
            recognizer.recognize_glyph_candidate("").outcome,
            recognizer.RecognitionOutcome.INVALID_INPUT,
        )

    def test_surrogate_content_is_invalid_without_partial_mapping(self) -> None:
        for candidate in ("\ud800", "\udfff", encoding.APPROVED_SCALARS[0] + "\ud800"):
            result = recognizer.recognize_glyph_candidate(candidate)
            self.assertIs(result.outcome, recognizer.RecognitionOutcome.INVALID_INPUT)
            self.assertIsNone(result.design_id)

    def test_host_argument_misuse_is_not_a_recognition_outcome(self) -> None:
        for value in (None, b"\xee\x84\x80", 0xE100, ["\uE100"]):
            with self.assertRaises(TypeError):
                recognizer.recognize_glyph_candidate(value)  # type: ignore[arg-type]

    def test_string_subclasses_are_not_coerced_or_trusted(self) -> None:
        class Candidate(str):
            pass

        with self.assertRaises(TypeError):
            recognizer.recognize_glyph_candidate(Candidate("\uE100"))

    def test_host_limit_is_separate_from_three_outcomes(self) -> None:
        self.assertEqual(recognizer.MAX_CANDIDATE_SCALARS, 65_536)
        at_limit = "x" * recognizer.MAX_CANDIDATE_SCALARS
        self.assertIs(
            recognizer.recognize_glyph_candidate(at_limit).outcome,
            recognizer.RecognitionOutcome.UNRECOGNIZED,
        )
        with self.assertRaises(recognizer.CandidateLimitError):
            recognizer.recognize_glyph_candidate(at_limit + "x")

    def test_unknown_observation_retains_no_candidate(self) -> None:
        result = recognizer.recognize_glyph_candidate("private unknown candidate")
        self.assertIs(result.outcome, recognizer.RecognitionOutcome.UNRECOGNIZED)
        self.assertEqual(
            tuple(field.name for field in fields(result)),
            ("outcome", "design_id", "code_point_label"),
        )
        self.assertNotIn("private unknown candidate", repr(result))

    def test_invalid_observation_retains_no_candidate(self) -> None:
        result = recognizer.recognize_glyph_candidate("\ud800")
        self.assertNotIn("candidate", tuple(field.name for field in fields(result)))
        self.assertIsNone(result.code_point_label)

    def test_nomination_eligibility_is_unrecognized_only(self) -> None:
        recognized = recognizer.recognize_glyph_candidate("\uE100")
        unrecognized = recognizer.recognize_glyph_candidate("x")
        invalid = recognizer.recognize_glyph_candidate("")
        self.assertFalse(recognized.nomination_eligible)
        self.assertTrue(unrecognized.nomination_eligible)
        self.assertFalse(invalid.nomination_eligible)

    def test_nomination_eligibility_does_not_create_storage_or_promotion(self) -> None:
        first = recognizer.recognize_glyph_candidate("new")
        second = recognizer.recognize_glyph_candidate("new")
        self.assertEqual(first, second)
        self.assertIs(second.outcome, recognizer.RecognitionOutcome.UNRECOGNIZED)

    def test_recognition_is_deterministic_for_fixed_candidates(self) -> None:
        candidates = ("\uE100", "\uE104", "x", "\uE105", "", "\ud800")
        self.assertEqual(
            tuple(recognizer.recognize_glyph_candidate(value) for value in candidates),
            tuple(recognizer.recognize_glyph_candidate(value) for value in candidates),
        )

    def test_recognition_has_no_automatic_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            recognizer.recognize_glyph_candidate("\uE100")
            recognizer.recognize_glyph_candidate("unknown")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_source_profile_is_not_silently_expanded(self) -> None:
        result = source_profile.inspect_source_profile("\uE100")
        self.assertEqual(result.outcome, source_profile.CONTEXT_REQUIRED)

    def test_lexer_is_not_silently_expanded(self) -> None:
        result = lexical.lex_source("\uE100")
        self.assertEqual(result.outcome, lexical.CONTEXT_REQUIRED)
        self.assertIsNone(result.stream)

    def test_observation_records_are_frozen_and_internally_consistent(self) -> None:
        result = recognizer.recognize_glyph_candidate("\uE100")
        with self.assertRaises(FrozenInstanceError):
            result.design_id = 99  # type: ignore[misc]
        with self.assertRaises(ValueError):
            recognizer.GlyphRecognitionObservation(
                recognizer.RecognitionOutcome.UNRECOGNIZED,
                design_id=2,
            )


if __name__ == "__main__":
    unittest.main()
