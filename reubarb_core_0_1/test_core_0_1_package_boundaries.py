"""Package I-3: fixed synthetic checks of accepted I-1/I-2 boundaries.

These tests add no runtime API or source grammar. Host comparisons establish
payload preservation, not Reubarb IDENTITY, equality, copying, or authority.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import re
import unittest

import core_0_1_transport_kernel as transport
import core_0_1_transcript_runtime as transcript


class PackageBoundaryTests(unittest.TestCase):
    def _admit(self, payload: str) -> transcript.textus:
        result = transcript.transcriptio(payload, reviewed=True, accepted=True)
        self.assertEqual(result.outcome, transcript.ADMITTED)
        self.assertIsNone(result.diagnostic)
        self.assertIsNotNone(result.value)
        return result.value

    def test_01_decoding_does_not_supply_review_or_acceptance(self) -> None:
        decoded = transport.inspect_source_bytes(b"I approve these words", "i3-01")
        self.assertTrue(decoded.succeeded)
        unreviewed = transcript.transcriptio(decoded.decoded_text)
        self.assertEqual(unreviewed.diagnostic.reason, transcript.REVIEW_REQUIRED)
        reviewed_only = transcript.transcriptio(decoded.decoded_text, reviewed=True)
        self.assertEqual(reviewed_only.diagnostic.reason, transcript.ACCEPTANCE_REQUIRED)
        self.assertIsNone(unreviewed.value)
        self.assertIsNone(reviewed_only.value)

    def test_02_decoded_host_text_is_not_already_textus(self) -> None:
        decoded = transport.inspect_source_bytes(b"leg WITH FALSE", "i3-02")
        result = transcript.leg(decoded.decoded_text)
        self.assertEqual(result.outcome, transcript.REJECTED)
        self.assertEqual(result.diagnostic.reason, transcript.EXPECTED_TEXTUS)
        self.assertIsNone(result.payload)

    def test_03_source_bom_rule_does_not_strip_reviewed_data(self) -> None:
        payload = "\ufeffreviewed data"
        source_result = transport.inspect_source_bytes(payload.encode("utf-8"), "i3-03")
        self.assertFalse(source_result.succeeded)
        self.assertEqual(source_result.reasons[0].code, transport.UTF8_BOM_FORBIDDEN)
        self.assertEqual(transcript.leg(self._admit(payload)).payload, payload)

    def test_04_source_control_rules_do_not_filter_transcript_data(self) -> None:
        payload = "\x00\r\x0b\x0c\u0085\u2028\u2029\u202e\u2066\x1b[31m"
        decoded = transport.inspect_source_bytes(payload.encode("utf-8"), "i3-04")
        self.assertEqual(decoded.decoded_text, payload)
        self.assertEqual(transcript.leg(self._admit(payload)).payload, payload)

    def test_05_bytes_are_not_implicitly_admitted_as_text(self) -> None:
        invalid_bytes = b"\xff"
        decoded = transport.inspect_source_bytes(invalid_bytes, "i3-05")
        self.assertIsNone(decoded.decoded_text)
        result = transcript.transcriptio(invalid_bytes, reviewed=True, accepted=True)
        self.assertEqual(result.diagnostic.reason, transcript.EXPECTED_TEXT)
        self.assertIsNone(result.value)

    def test_06_failure_policies_remain_boundary_specific(self) -> None:
        decoded = transport.inspect_source_bytes(b"\xef\xbb\xbf\xff", "i3-06")
        self.assertEqual(tuple(r.code for r in decoded.reasons),
                         (transport.UTF8_BOM_FORBIDDEN, transport.INVALID_UTF8))
        malformed = "a" * transcript.MAX_TRANSCRIPT_SCALARS + "\ud800"
        unreviewed = transcript.transcriptio(malformed)
        limited = transcript.transcriptio(malformed, reviewed=True, accepted=True)
        self.assertEqual(unreviewed.diagnostic.reason, transcript.REVIEW_REQUIRED)
        self.assertEqual(limited.diagnostic.reason, transcript.TRANSCRIPT_LIMIT)
        self.assertEqual(limited.outcome, transcript.LIMITED)
        self.assertIsNone(limited.value)

    def test_07_correction_does_not_replace_earlier_payload(self) -> None:
        original = self._admit("north valve")
        corrected = self._admit("south valve")
        for _ in range(3):
            self.assertEqual(transcript.leg(original).payload, "north valve")
            self.assertEqual(transcript.leg(corrected).payload, "south valve")

    def test_08_literal_replacement_character_is_not_decoder_repair(self) -> None:
        payload = "A\ufffdB"
        decoded = transport.inspect_source_bytes(payload.encode("utf-8"), "i3-08")
        self.assertEqual(decoded.decoded_text, payload)
        self.assertEqual(transcript.leg(self._admit(payload)).payload, payload)
        invalid = transport.inspect_source_bytes(b"A\xffB", "i3-08-bad")
        self.assertIsNone(invalid.decoded_text)

    def test_09_utf8_width_boundaries_preserve_scalars(self) -> None:
        scalars = (0, 0x7f, 0x80, 0x7ff, 0x800, 0xd7ff, 0xe000, 0xfeff,
                   0xffff, 0x10000, 0x10ffff)
        payload = "x" + "".join(chr(cp) for cp in scalars)
        decoded = transport.inspect_source_bytes(payload.encode("utf-8"), "i3-09")
        self.assertEqual(decoded.decoded_text, payload)
        observed = transcript.leg(self._admit(payload))
        self.assertEqual(observed.payload, payload)
        metadata = json.loads(transport.serialize_transport_result(decoded))
        self.assertEqual(metadata["decoded_scalar_count"], len(scalars) + 1)

    def test_10_fixed_malformed_utf8_corpus_is_rejected(self) -> None:
        vectors = (b"\xc0\x80", b"\xe0\x80\x80", b"\xf0\x80\x80\x80",
                   b"\xed\xa0\x80", b"\xed\xbf\xbf", b"\xf4\x90\x80\x80",
                   b"\xf5\x80\x80\x80", b"\xe2(\xa1", b"\xf0\x9f\x92")
        for index, vector in enumerate(vectors):
            with self.subTest(vector_index=index):
                result = transport.inspect_source_bytes(vector, "i3-10")
                self.assertIsNone(result.decoded_text)
                self.assertEqual(tuple(r.code for r in result.reasons),
                                 (transport.INVALID_UTF8,))

    def test_11_transcript_ceiling_counts_scalars_not_utf8_bytes(self) -> None:
        payload = "\U0001f600" * transcript.MAX_TRANSCRIPT_SCALARS
        self.assertGreater(len(payload.encode("utf-8")), len(payload))
        self.assertEqual(transcript.leg(self._admit(payload)).payload, payload)
        result = transcript.transcriptio(payload + "x", reviewed=True, accepted=True)
        self.assertEqual(result.outcome, transcript.LIMITED)
        self.assertIsNone(result.value)

    def test_12_reason_catalogue_keeps_exact_codes_and_domains(self) -> None:
        codes = (transport.INVALID_UTF8, transport.UTF8_BOM_FORBIDDEN,
                 transcript.INVALID_REVIEW_STATE, transcript.REVIEW_REQUIRED,
                 transcript.ACCEPTANCE_REQUIRED, transcript.EXPECTED_TEXT,
                 transcript.NON_SCALAR_CONTENT, transcript.TRANSCRIPT_LIMIT,
                 transcript.EXPECTED_TEXTUS, transcript.RESOURCE_EXHAUSTED,
                 transcript.TRANSCRIPT_INVARIANT_FAILURE)
        pattern = r"GART\.CORE_0_1\.[A-Z][A-Z0-9]*\.[A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)*"
        self.assertEqual(len(codes), 11)
        self.assertEqual(len(set(codes)), 11)
        for code in codes:
            self.assertIsNotNone(re.fullmatch(pattern, code, flags=re.ASCII))
        self.assertTrue(transcript.TRANSCRIPT_LIMIT.startswith("GART.CORE_0_1.RESOURCE."))

    def test_13_operations_do_not_automatically_display_payloads(self) -> None:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            payload = "\x1b[31mSYNTHETIC_ONLY<script>not code</script>"
            value = self._admit(payload)
            observed = transcript.leg(value)
            metadata = transport.serialize_transport_result(
                transport.inspect_source_bytes(b"plain", "i3-13"))
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(observed.payload, payload)
        self.assertTrue(metadata)

    def test_14_observation_and_diagnostic_privacy_are_separate(self) -> None:
        secret = "I3_SYNTHETIC_PAYLOAD_NOT_FOR_DIAGNOSTICS"
        admitted = transcript.transcriptio(secret, reviewed=True, accepted=True)
        observed = transcript.leg(admitted.value)
        rejected = transcript.transcriptio(secret)
        self.assertEqual(observed.payload, secret)
        for record in (admitted, admitted.value, observed, rejected, rejected.diagnostic):
            self.assertNotIn(secret, repr(record))
        decoded = transport.inspect_source_bytes(secret.encode("utf-8"), "i3-14")
        metadata = json.loads(transport.serialize_transport_result(decoded))
        self.assertNotIn("decoded_text", metadata)
        self.assertNotIn(secret, json.dumps(metadata))

    def test_15_runtime_binding_metadata_does_not_add_aliases(self) -> None:
        self.assertEqual(tuple((b.spelling, b.role) for b in transcript.BINDINGS), (
            ("textus", "reviewed-transcript runtime type"),
            ("transcriptio", "reviewed-transcript admission operation"),
            ("leg", "whole-transcript exact observation operation"),
        ))
        spellings = {binding.spelling for binding in transcript.BINDINGS}
        self.assertTrue({"txt", "TEXTUS", "LEG", "TRANSCRIPTIO"}.isdisjoint(spellings))

    def test_16_fixed_generated_payloads_preserve_each_exact_sequence(self) -> None:
        # Fixed generator v1: 33 cases, no random seed, framework, or shrinker.
        alphabet = ("A", "a", " ", "\t", "\n", "\r", "\u0301", "\u00e9",
                    "\u05d0", "\u2066", "\ufeff", "\x00", "\U0001f600")
        for length in range(33):
            with self.subTest(case_length=length):
                payload = "".join(alphabet[(i * 7 + length) % len(alphabet)]
                                  for i in range(length))
                value = self._admit(payload)
                self.assertEqual(transcript.leg(value).payload, payload)
                self.assertEqual(transcript.leg(value).payload, payload)


if __name__ == "__main__":
    unittest.main()
