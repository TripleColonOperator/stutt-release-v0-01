"""I-15: bounded checks for the first native-glyph source-integration slice."""
from __future__ import annotations

import unittest

import core_0_1_glyph_encoding as glyph_encoding
import core_0_1_glyph_source_integration as i15
import core_0_1_glyph_recognizer as recognizer
import core_0_1_source_profile as profile


class GlyphSourceIntegrationTests(unittest.TestCase):
    @staticmethod
    def _glyph(index: int = 0) -> str:
        return glyph_encoding.APPROVED_SCALARS[index]

    def test_01_standalone_recognized_glyph_is_observed(self):
        text = f"  \t{self._glyph(2)}\r\n"
        result = i15.observe_glyph_source_candidate(text)
        self.assertEqual(result.outcome, i15.OBSERVED)
        self.assertIsNotNone(result.observation)
        self.assertEqual(result.observation.outcome,
                         recognizer.RecognitionOutcome.RECOGNIZED.value)
        self.assertEqual(result.observation.design_id, 4)
        self.assertEqual(result.observation.code_point_label, "U+E102")
        self.assertEqual(result.reasons, ())

    def test_02_unrecognized_single_scalar_becomes_unknown_result(self):
        result = i15.observe_glyph_source_candidate("\U0001F604")
        self.assertEqual(result.outcome, i15.OBSERVED)
        self.assertIsNotNone(result.observation)
        self.assertEqual(result.observation.outcome,
                         recognizer.RecognitionOutcome.UNRECOGNIZED.value)
        self.assertIsNone(result.observation.design_id)
        self.assertEqual(tuple(r.code for r in result.reasons),
                         (i15.UNRECOGNIZED_GLYPH,))
        self.assertEqual(result.observation.candidate, "\U0001F604")

    def test_03_incomplete_relationship_with_two_source_tokens_is_rejected(self):
        text = f"{self._glyph(0)} {self._glyph(1)}"
        result = i15.parse_glyph_source_candidate(text)
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertEqual(len(result.reasons), 1)
        self.assertEqual(result.reasons[0].code, i15.INCOMPLETE_GLYPH_RELATIONSHIP)
        self.assertEqual(result.instruction, None)

    def test_04_authorized_and_candidate_form_validation_is_enforced(self):
        result = i15.parse_glyph_source_candidate("leg")
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertEqual(result.reasons[0].code, i15.UNAUTHORIZED_SOURCE_FORM)

    def test_05_empty_source_is_a_no_candidate_error(self):
        result = i15.parse_glyph_source_candidate("   //note\r\n\t\n")
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertEqual(result.reasons[0].code, i15.EMPTY_GLYPH_SOURCE)

    def test_06_source_profile_rejections_are_preserved(self):
        source = "leg\x00"
        parsed = i15.parse_glyph_source_candidate(source)
        direct = profile.inspect_source_profile(source)
        self.assertEqual(parsed.outcome, i15.SOURCE_REJECTED)
        self.assertEqual(parsed.source_profile_outcome, direct.outcome)
        self.assertEqual(tuple((r.code, r.location) for r in parsed.reasons),
                         tuple((r.code, r.location) for r in direct.reasons))

    def test_07_non_string_input_is_rejected_without_a_profile_check(self):
        result = i15.parse_glyph_source_candidate(b"\xe1")
        self.assertEqual(result.outcome, i15.INPUT_REJECTED)
        self.assertEqual(result.reasons[0].code, "GART.CORE_0_1.HOST.EXPECTED_STRING")

    def test_08_successful_parse_exposes_token_span_and_instruction_span(self):
        source = f"\n\t//c\r\n{self._glyph(3)} \t  "
        result = i15.parse_glyph_source_candidate(source)
        self.assertEqual(result.outcome, i15.PARSED)
        self.assertIsNotNone(result.instruction)
        if result.instruction is None:
            return
        token = result.instruction.candidate
        token_span = result.instruction.candidate_span
        self.assertEqual(token, self._glyph(3))
        self.assertEqual((token_span.start_offset, token_span.end_offset),
                         (len("\n\t//c\r\n"), len("\n\t//c\r\n") + 1))
        self.assertEqual((result.instruction.instruction_span.start_offset,
                          result.instruction.instruction_span.end_offset),
                         (0, len(source)))
        self.assertIs(result.instruction.source_map, profile.inspect_source_profile(source).source_map)

    def test_09_observation_outcome_is_deterministic(self):
        source = self._glyph(4)
        first = i15.observe_glyph_source_candidate(source)
        second = i15.observe_glyph_source_candidate(source)
        self.assertEqual(first, second)
        self.assertEqual(first.parse_result.outcome, i15.PARSED)
        self.assertEqual(second.parse_result.outcome, i15.PARSED)

    def test_10_parse_and_observe_do_not_leak_source_text_in_repr(self):
        source = self._glyph(1)
        parsed = i15.parse_glyph_source_candidate(source)
        observed = i15.observe_glyph_source_candidate(source)
        for value in (parsed, observed, parsed.instruction, observed.observation):
            self.assertNotIn(source, repr(value))

    def test_11_invariant_codes_look_like_host_reason_format(self):
        self.assertTrue(i15.EMPTY_GLYPH_SOURCE.startswith("GART.CORE_0_1.GLYPH_SOURCE"))
        self.assertTrue(i15.INCOMPLETE_GLYPH_RELATIONSHIP.startswith("GART.CORE_0_1.GLYPH_SOURCE"))
        self.assertTrue(i15.UNAUTHORIZED_SOURCE_FORM.startswith("GART.CORE_0_1.GLYPH_SOURCE"))
        self.assertTrue(i15.UNRECOGNIZED_GLYPH.startswith("GART.CORE_0_1.GLYPH_SOURCE"))


if __name__ == "__main__":
    unittest.main()
