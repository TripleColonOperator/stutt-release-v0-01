"""I-21: fixed reviewed-text end-to-end demonstration acceptance checks.

The orchestration in this file is test-only.  It supplies one instruction source
and one separately reviewed transcript value to already accepted interfaces; it
does not define a production wrapper, binding lookup, dispatcher, or serializer.
"""
from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import fields
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import core_0_1_lexical_frontend as lexical
import core_0_1_read_instruction as read
import core_0_1_source_profile as source_profile
import core_0_1_syntax_skeleton as syntax
import core_0_1_transcript_runtime as transcript
import core_0_1_transport_kernel as transport


FIXED_SOURCE_BYTES = b"leg transcriptA"
FIXED_SOURCE_ID = "core-0.1-i21-fixed-read"
FIXED_TARGET_NAME = "transcriptA"
FIXED_REVIEWED_PAYLOAD = "Core 0.1 observed text."


class ReviewedTextPathTests(unittest.TestCase):
    def _demonstrate(
        self,
        source_bytes: bytes = FIXED_SOURCE_BYTES,
        *,
        source_id: str = FIXED_SOURCE_ID,
        payload: object = FIXED_REVIEWED_PAYLOAD,
        reviewed: bool = True,
        accepted: bool = True,
        target_name: object = FIXED_TARGET_NAME,
    ) -> tuple[
        transport.TransportResult,
        transcript.AdmissionResult | None,
        read.ReadObservationResult | None,
    ]:
        """Run only the explicit test fixture, stopping at each failed seam."""

        transported = transport.inspect_source_bytes(source_bytes, source_id)
        if not transported.succeeded:
            return transported, None, None
        admitted = transcript.transcriptio(
            payload, reviewed=reviewed, accepted=accepted
        )
        if admitted.value is None:
            return transported, admitted, None
        observed = read.observe_read_unit(
            transported.decoded_text,
            target_name=target_name,
            target_value=admitted.value,
        )
        return transported, admitted, observed

    def test_01_fixed_path_reaches_the_exact_existing_observation(self) -> None:
        transported, admitted, result = self._demonstrate()

        self.assertIs(type(transported), transport.TransportResult)
        self.assertIs(type(admitted), transcript.AdmissionResult)
        self.assertIs(type(result), read.ReadObservationResult)
        self.assertTrue(transported.succeeded)
        self.assertEqual(admitted.outcome, transcript.ADMITTED)
        self.assertTrue(result.succeeded)
        self.assertEqual(result.outcome, transcript.OBSERVED)
        self.assertEqual(result.observation.outcome, transcript.OBSERVED)
        self.assertEqual(result.observation.payload, FIXED_REVIEWED_PAYLOAD)
        self.assertIsNone(result.observation.diagnostic)

    def test_02_every_existing_seam_receives_one_exact_input(self) -> None:
        original_inspect = source_profile.inspect_source_profile

        with (
            patch.object(transport, "inspect_source_bytes",
                         wraps=transport.inspect_source_bytes) as transport_call,
            patch.object(transcript, "transcriptio",
                         wraps=transcript.transcriptio) as admission_call,
            patch.object(source_profile, "inspect_source_profile",
                         wraps=original_inspect) as profile_call,
            patch.object(read.lexical, "lex_source",
                         wraps=read.lexical.lex_source) as lexer_call,
            patch.object(read, "parse_read_unit",
                         wraps=read.parse_read_unit) as parser_call,
            patch.object(read.runtime, "leg", wraps=read.runtime.leg) as leg_call,
        ):
            transported, admitted, result = self._demonstrate()

        transport_call.assert_called_once_with(FIXED_SOURCE_BYTES, FIXED_SOURCE_ID)
        admission_call.assert_called_once_with(
            FIXED_REVIEWED_PAYLOAD, reviewed=True, accepted=True
        )
        profile_call.assert_called_once_with("leg transcriptA")
        lexer_call.assert_called_once_with("leg transcriptA")
        parser_call.assert_called_once()
        leg_call.assert_called_once_with(admitted.value)
        self.assertIs(parser_call.call_args.args[0].stream.source_map,
                      result.parse_result.preparation.syntax_input.source_map)
        self.assertEqual(transported.decoded_text, "leg transcriptA")

    def test_03_success_retains_lexical_syntax_and_span_provenance(self) -> None:
        _, _, result = self._demonstrate()
        parsed = result.parse_result
        prepared = parsed.preparation
        instruction = parsed.instruction

        self.assertEqual(parsed.outcome, read.PARSED)
        self.assertEqual(parsed.source_profile_outcome,
                         source_profile.PROFILE_CHECKED)
        self.assertEqual(prepared.outcome, syntax.PREPARED)
        self.assertEqual(prepared.upstream_outcome, lexical.LEXED)
        self.assertEqual(instruction.target_name, FIXED_TARGET_NAME)
        items = prepared.syntax_input.items
        self.assertEqual(
            tuple((item.kind, item.lexeme) for item in items),
            (("WORD", "leg"), ("SPACE_TAB", " "),
             ("WORD", "transcriptA"), ("EOF", "")),
        )
        self.assertEqual(
            (instruction.head_range.span.start_offset,
             instruction.head_range.span.end_offset),
            (0, 3),
        )
        self.assertEqual(
            (instruction.target_range.span.start_offset,
             instruction.target_range.span.end_offset),
            (4, 15),
        )
        self.assertEqual(
            (instruction.instruction_range.span.start_offset,
             instruction.instruction_range.span.end_offset),
            (0, 15),
        )
        self.assertEqual(instruction.unit_range, instruction.instruction_range)
        self.assertEqual(instruction.unit_range.end_item, len(items) - 1)

    def test_04_transport_failures_stop_before_admission_or_reading(self) -> None:
        vectors = (
            (b"\xffleg transcriptA", transport.INVALID_UTF8),
            (b"\xef\xbb\xbfleg transcriptA", transport.UTF8_BOM_FORBIDDEN),
        )
        for source_bytes, reason in vectors:
            with self.subTest(reason=reason):
                with (
                    patch.object(transcript, "transcriptio",
                                 wraps=transcript.transcriptio) as admission_call,
                    patch.object(read, "observe_read_unit",
                                 wraps=read.observe_read_unit) as read_call,
                ):
                    transported, admitted, observed = self._demonstrate(source_bytes)
                self.assertFalse(transported.succeeded)
                self.assertIn(reason, tuple(item.code for item in transported.reasons))
                self.assertIsNone(admitted)
                self.assertIsNone(observed)
                admission_call.assert_not_called()
                read_call.assert_not_called()

    def test_05_review_and_acceptance_are_explicit_separate_requirements(self) -> None:
        cases = (
            (False, False, transcript.REVIEW_REQUIRED),
            (True, False, transcript.ACCEPTANCE_REQUIRED),
        )
        for reviewed, accepted, reason in cases:
            with self.subTest(reviewed=reviewed, accepted=accepted):
                with patch.object(read, "observe_read_unit",
                                  wraps=read.observe_read_unit) as read_call:
                    transported, admitted, observed = self._demonstrate(
                        reviewed=reviewed, accepted=accepted
                    )
                self.assertTrue(transported.succeeded)
                self.assertIsNone(admitted.value)
                self.assertEqual(admitted.diagnostic.reason, reason)
                self.assertIsNone(observed)
                read_call.assert_not_called()

    def test_06_profile_grammar_and_label_failures_never_call_leg(self) -> None:
        cases = (
            ("leg\x00 transcriptA", FIXED_TARGET_NAME,
             lexical.SOURCE_REJECTED),
            ("leg transcriptA extra", FIXED_TARGET_NAME,
             read.SYNTAX_REJECTED),
            ("leg transcriptA", "transcriptB", read.TARGET_REJECTED),
        )
        admitted = transcript.transcriptio(
            FIXED_REVIEWED_PAYLOAD, reviewed=True, accepted=True
        )
        for source, target_name, outcome in cases:
            with self.subTest(outcome=outcome):
                with patch.object(read.runtime, "leg",
                                  wraps=read.runtime.leg) as leg_call:
                    result = read.observe_read_unit(
                        source, target_name=target_name, target_value=admitted.value
                    )
                self.assertEqual(result.outcome, outcome)
                self.assertIsNone(result.observation)
                leg_call.assert_not_called()

    def test_07_wrong_target_values_keep_the_existing_i2_rejection(self) -> None:
        for target_value in (None, object(), FIXED_REVIEWED_PAYLOAD):
            with self.subTest(value_type=type(target_value).__name__):
                with patch.object(
                    transcript,
                    "transcriptio",
                    side_effect=AssertionError("no implicit admission"),
                ) as admission_call:
                    result = read.observe_read_unit(
                        "leg transcriptA",
                        target_name=FIXED_TARGET_NAME,
                        target_value=target_value,
                    )
                admission_call.assert_not_called()
                self.assertEqual(result.outcome, transcript.REJECTED)
                self.assertFalse(result.succeeded)
                self.assertIs(type(result.observation), transcript.ObservationResult)
                self.assertIsNone(result.observation.payload)
                self.assertEqual(result.observation.diagnostic.reason,
                                 transcript.EXPECTED_TEXTUS)
                self.assertEqual(tuple(reason.code for reason in result.reasons),
                                 (transcript.EXPECTED_TEXTUS,))

    def test_08_transport_preserves_case_scalars_and_approved_whitespace(self) -> None:
        source = "// caf\u00e9\r\n\tleg \tTranscriptA\r\n"
        transported = transport.inspect_source_bytes(
            source.encode("utf-8"), "core-0.1-i21-preservation"
        )
        admitted = transcript.transcriptio(
            FIXED_REVIEWED_PAYLOAD, reviewed=True, accepted=True
        )
        result = read.observe_read_unit(
            transported.decoded_text,
            target_name="TranscriptA",
            target_value=admitted.value,
        )

        self.assertEqual(transported.decoded_text, source)
        self.assertTrue(result.succeeded)
        self.assertEqual(result.parse_result.instruction.target_name, "TranscriptA")
        self.assertEqual(
            result.parse_result.instruction.syntax_input.source_map.source_text,
            source,
        )

    def test_09_observed_payload_is_never_reused_as_instruction_source(self) -> None:
        payload = "leg nestedTarget\n\x00 \u05e2\u05d1\u05e8\u05d9\u05ea \U0001f600 \u202e"
        with (
            patch.object(transport, "inspect_source_bytes",
                         wraps=transport.inspect_source_bytes) as transport_call,
            patch.object(read.lexical, "lex_source",
                         wraps=read.lexical.lex_source) as lexer_call,
            patch.object(read, "parse_read_unit",
                         wraps=read.parse_read_unit) as parser_call,
        ):
            _, _, result = self._demonstrate(payload=payload)

        transport_call.assert_called_once_with(FIXED_SOURCE_BYTES, FIXED_SOURCE_ID)
        lexer_call.assert_called_once_with("leg transcriptA")
        parser_call.assert_called_once()
        self.assertEqual(result.observation.payload, payload)

    def test_10_repeated_observation_is_exact_nonconsuming_and_uncached(self) -> None:
        transported = transport.inspect_source_bytes(FIXED_SOURCE_BYTES, FIXED_SOURCE_ID)
        admitted = transcript.transcriptio(
            FIXED_REVIEWED_PAYLOAD, reviewed=True, accepted=True
        )
        with patch.object(read.runtime, "leg", wraps=read.runtime.leg) as leg_call:
            results = tuple(
                read.observe_read_unit(
                    transported.decoded_text,
                    target_name=FIXED_TARGET_NAME,
                    target_value=admitted.value,
                )
                for _ in range(3)
            )

        self.assertEqual(leg_call.call_count, 3)
        self.assertEqual(tuple(item.observation.payload for item in results),
                         (FIXED_REVIEWED_PAYLOAD,) * 3)
        self.assertTrue(all(item.succeeded for item in results))
        self.assertEqual(transcript.leg(admitted.value).payload,
                         FIXED_REVIEWED_PAYLOAD)

    def test_11_path_is_silent_and_has_no_combined_serialized_result(self) -> None:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            transported, admitted, result = self._demonstrate()
            transport_json = transport.serialize_transport_result(transported)

        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(FIXED_REVIEWED_PAYLOAD, repr(admitted))
        self.assertNotIn(FIXED_REVIEWED_PAYLOAD, repr(result))
        envelope = json.loads(transport_json)
        self.assertNotIn("decoded_text", envelope)
        self.assertNotIn("payload", envelope)
        self.assertNotIn("admission", envelope)
        self.assertNotIn("read_result", envelope)
        self.assertNotIn(FIXED_REVIEWED_PAYLOAD, transport_json)

    def test_12_existing_public_surfaces_remain_separate_and_non_dispatching(self) -> None:
        self.assertEqual(
            tuple(item.name for item in fields(read.ReadObservationResult)),
            ("outcome", "parse_result", "reasons", "observation"),
        )
        self.assertEqual(
            tuple(item.name for item in fields(transcript.ObservationResult)),
            ("outcome", "payload", "diagnostic"),
        )
        public_names = set(transport.__all__) | set(transcript.__all__) | set(read.__all__)
        forbidden_public = {
            "dispatch", "dispatcher", "evaluate", "execute", "run", "main",
            "bind", "lookup", "serialize_read_result", "serialize_core_result",
            "recon", "fulfill", "authorize", "observe_glyph",
        }
        self.assertTrue(forbidden_public.isdisjoint(public_names))

        root = Path(__file__).resolve().parent
        read_tree = ast.parse(
            (root / "core_0_1_read_instruction.py").read_text(encoding="utf-8")
        )
        imported = {
            alias.name
            for node in ast.walk(read_tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module or ""
            for node in ast.walk(read_tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertFalse(any("glyph" in name for name in imported))
        self.assertFalse(any(name in imported for name in
                             ("subprocess", "socket", "pathlib", "urllib")))
        called_names = {
            node.func.id
            for node in ast.walk(read_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue({"eval", "exec", "compile", "open", "input", "print"}
                        .isdisjoint(called_names))


if __name__ == "__main__":
    unittest.main()
