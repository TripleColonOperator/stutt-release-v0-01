"""Finite Package I-2 tests for the Reubarb Pi transcript runtime component."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import ast
import unittest
from unittest.mock import patch

import core_0_1_transcript_runtime as runtime


class TranscriptRuntimeTests(unittest.TestCase):
    def admit(self, payload: str):
        result = runtime.transcriptio(payload, reviewed=True, accepted=True)
        self.assertEqual(result.outcome, runtime.ADMITTED)
        self.assertIsNone(result.diagnostic)
        self.assertIsNotNone(result.value)
        return result.value

    def test_01_ascii_round_trip_exactly(self):
        payload = "Reviewed transcript 001."
        value = self.admit(payload)
        observed = runtime.leg(value)
        self.assertEqual(observed.outcome, runtime.OBSERVED)
        self.assertEqual(observed.payload, payload)
        self.assertIsNone(observed.diagnostic)

    def test_02_multilingual_and_supplementary_plane_round_trip(self):
        payload = "English עברית Deutsch Ελληνικά 😀 𐍈"
        observed = runtime.leg(self.admit(payload))
        self.assertEqual(observed.payload, payload)

    def test_03_case_whitespace_tabs_and_line_endings_are_preserved(self):
        payload = " AbC\tXYZ \nLF\r\nCRLF\rCR "
        observed = runtime.leg(self.admit(payload))
        self.assertEqual(observed.payload, payload)

    def test_04_precomposed_and_decomposed_sequences_are_preserved_individually(self):
        precomposed = "é"
        decomposed = "e\u0301"
        self.assertEqual(runtime.leg(self.admit(precomposed)).payload, precomposed)
        self.assertEqual(runtime.leg(self.admit(decomposed)).payload, decomposed)
        self.assertNotEqual(tuple(map(ord, precomposed)), tuple(map(ord, decomposed)))

    def test_05_scalar_edges_feff_and_controls_are_preserved(self):
        payload = "\x00\x1f\uFEFF\u0009\U0010FFFF"
        self.assertEqual(runtime.leg(self.admit(payload)).payload, payload)

    def test_06_empty_text_is_success_not_failure(self):
        admitted = runtime.transcriptio("", reviewed=True, accepted=True)
        self.assertEqual(admitted.outcome, runtime.ADMITTED)
        observed = runtime.leg(admitted.value)
        self.assertEqual(observed.outcome, runtime.OBSERVED)
        self.assertEqual(observed.payload, "")
        self.assertIsNotNone(observed.payload)

    def test_07_review_omitted_or_false_rejects_without_value(self):
        for kwargs in ({"accepted": True}, {"reviewed": False, "accepted": True}):
            with self.subTest(kwargs=kwargs):
                result = runtime.transcriptio("x", **kwargs)
                self.assertEqual(result.outcome, runtime.REJECTED)
                self.assertIsNone(result.value)
                self.assertEqual(result.diagnostic.reason, runtime.REVIEW_REQUIRED)

    def test_08_acceptance_omitted_or_false_rejects_without_value(self):
        for kwargs in ({"reviewed": True}, {"reviewed": True, "accepted": False}):
            with self.subTest(kwargs=kwargs):
                result = runtime.transcriptio("x", **kwargs)
                self.assertEqual(result.outcome, runtime.REJECTED)
                self.assertIsNone(result.value)
                self.assertEqual(result.diagnostic.reason, runtime.ACCEPTANCE_REQUIRED)

    def test_09_non_boolean_controls_reject_truthy_substitutes(self):
        for reviewed, accepted in ((1, True), (True, 1), ("true", True), (True, "true")):
            with self.subTest(reviewed=reviewed, accepted=accepted):
                result = runtime.transcriptio("x", reviewed=reviewed, accepted=accepted)
                self.assertEqual(result.outcome, runtime.REJECTED)
                self.assertEqual(result.diagnostic.reason, runtime.INVALID_REVIEW_STATE)

    def test_10_approval_words_inside_payload_do_not_supply_review_or_acceptance(self):
        payload = "I reviewed and accept this transcript."
        result = runtime.transcriptio(payload)
        self.assertEqual(result.outcome, runtime.REJECTED)
        self.assertEqual(result.diagnostic.reason, runtime.REVIEW_REQUIRED)
        self.assertIsNone(result.value)

    def test_11_non_strings_and_str_subclasses_reject_without_conversion_hooks(self):
        calls = []

        class Hostile:
            def __str__(self):
                calls.append("str")
                return "converted"

            def __repr__(self):
                calls.append("repr")
                return "represented"

        class TextSubclass(str):
            pass

        for payload in (Hostile(), TextSubclass("subclass"), b"bytes", 7, None):
            with self.subTest(type=type(payload).__name__):
                result = runtime.transcriptio(payload, reviewed=True, accepted=True)
                self.assertEqual(result.outcome, runtime.REJECTED)
                self.assertEqual(result.diagnostic.reason, runtime.EXPECTED_TEXT)
                self.assertIsNone(result.value)
        self.assertEqual(calls, [])

    def test_12_surrogate_code_points_reject_without_repair(self):
        for payload in ("\ud800", "\udfff", "\ud800\udc00"):
            with self.subTest(codepoints=[hex(ord(c)) for c in payload]):
                result = runtime.transcriptio(payload, reviewed=True, accepted=True)
                self.assertEqual(result.outcome, runtime.REJECTED)
                self.assertEqual(result.diagnostic.reason, runtime.NON_SCALAR_CONTENT)
                self.assertIsNone(result.value)

    def test_13_exact_size_ceiling_succeeds_completely(self):
        payload = "a" * runtime.MAX_TRANSCRIPT_SCALARS
        result = runtime.transcriptio(payload, reviewed=True, accepted=True)
        self.assertEqual(result.outcome, runtime.ADMITTED)
        self.assertEqual(runtime.leg(result.value).payload, payload)

    def test_14_one_above_size_ceiling_is_limited_without_partial_carrier(self):
        payload = "a" * (runtime.MAX_TRANSCRIPT_SCALARS + 1)
        result = runtime.transcriptio(payload, reviewed=True, accepted=True)
        self.assertEqual(result.outcome, runtime.LIMITED)
        self.assertEqual(result.diagnostic.reason, runtime.TRANSCRIPT_LIMIT)
        self.assertIsNone(result.value)

    def test_15_first_failure_order_is_fixed(self):
        oversized_malformed = ("a" * runtime.MAX_TRANSCRIPT_SCALARS) + "\ud800"
        cases = (
            ({"payload": object(), "reviewed": 1, "accepted": False}, runtime.INVALID_REVIEW_STATE),
            ({"payload": object(), "reviewed": False, "accepted": False}, runtime.REVIEW_REQUIRED),
            ({"payload": object(), "reviewed": True, "accepted": False}, runtime.ACCEPTANCE_REQUIRED),
            ({"payload": object(), "reviewed": True, "accepted": True}, runtime.EXPECTED_TEXT),
            ({"payload": oversized_malformed, "reviewed": True, "accepted": True}, runtime.TRANSCRIPT_LIMIT),
        )
        for kwargs, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                result = runtime.transcriptio(**kwargs)
                self.assertEqual(result.diagnostic.reason, expected_reason)

    def test_16_leg_rejects_raw_text_unrelated_objects_and_lookalikes(self):
        class Lookalike:
            _payload = "x"
            _seal = object()

        for value in ("raw", object(), Lookalike()):
            with self.subTest(type=type(value).__name__):
                result = runtime.leg(value)
                self.assertEqual(result.outcome, runtime.REJECTED)
                self.assertEqual(result.diagnostic.reason, runtime.EXPECTED_TEXTUS)
                self.assertIsNone(result.payload)

    def test_17_repeated_observation_is_exact_and_non_consuming(self):
        payload = "same every time"
        value = self.admit(payload)
        first = runtime.leg(value)
        second = runtime.leg(value)
        third = runtime.leg(value)
        self.assertEqual((first.payload, second.payload, third.payload), (payload, payload, payload))

    def test_18_corrected_admission_does_not_modify_earlier_transcript(self):
        original = self.admit("valve six")
        corrected = self.admit("valve seven")
        self.assertEqual(runtime.leg(original).payload, "valve six")
        self.assertEqual(runtime.leg(corrected).payload, "valve seven")

    def test_19_carrier_is_read_only_and_exports_no_mutation_operation(self):
        value = self.admit("immutable payload")
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            value._payload = "changed"  # type: ignore[misc]
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            del value._payload  # type: ignore[misc]
        exported = set(runtime.__all__)
        for forbidden in ("mutate", "set_payload", "replace_payload", "append", "extend"):
            self.assertNotIn(forbidden, exported)

    def test_20_instruction_like_payloads_remain_inert_in_memory(self):
        payloads = (
            "WITH FALSE RECON transcriptio leg",
            "python -c 'import os; os.system(\"echo BAD\")'",
            "$(touch SHOULD_NOT_EXIST)",
            "<script>alert('x')</script>",
            "\x1b[31mterminal-looking\x1b[0m",
        )
        for payload in payloads:
            with self.subTest(payload=payload[:20]):
                observed = runtime.leg(self.admit(payload))
                self.assertEqual(observed.payload, payload)

    def test_21_repr_and_diagnostics_do_not_disclose_secret_payload(self):
        secret = "SYNTHETIC_SECRET_TRANSCRIPT_4f99a1"
        admitted = runtime.transcriptio(secret, reviewed=True, accepted=True)
        observed = runtime.leg(admitted.value)
        rejected = runtime.transcriptio(secret)
        for obj in (admitted.value, admitted, observed, rejected, rejected.diagnostic):
            with self.subTest(type=type(obj).__name__):
                self.assertNotIn(secret, repr(obj))

    def test_22_binding_metadata_has_exactly_three_approved_spellings(self):
        self.assertEqual(
            tuple(binding.spelling for binding in runtime.BINDINGS),
            ("textus", "transcriptio", "leg"),
        )
        self.assertEqual(len(runtime.BINDINGS), 3)
        self.assertNotIn("txt", {binding.spelling for binding in runtime.BINDINGS})
        self.assertNotIn("TEXTUS", {binding.spelling for binding in runtime.BINDINGS})

    def test_23_controlled_allocation_and_invariant_failures_do_not_return_partial_success(self):
        with patch.object(runtime, "_construct_textus", side_effect=MemoryError):
            result = runtime.transcriptio("x", reviewed=True, accepted=True)
            self.assertEqual(result.outcome, runtime.HOST_FAILED)
            self.assertEqual(result.diagnostic.reason, runtime.RESOURCE_EXHAUSTED)
            self.assertIsNone(result.value)

        value = self.admit("observe me")
        with patch.object(runtime, "_make_observation", side_effect=MemoryError):
            result = runtime.leg(value)
            self.assertEqual(result.outcome, runtime.HOST_FAILED)
            self.assertEqual(result.diagnostic.reason, runtime.RESOURCE_EXHAUSTED)
            self.assertIsNone(result.payload)

        damaged = object.__new__(runtime.textus)
        object.__setattr__(damaged, "_payload", "x")
        object.__setattr__(damaged, "_seal", object())
        result = runtime.leg(damaged)
        self.assertEqual(result.outcome, runtime.HOST_FAILED)
        self.assertEqual(result.diagnostic.reason, runtime.TRANSCRIPT_INVARIANT_FAILURE)
        self.assertIsNone(result.payload)

    def test_24_source_has_no_forbidden_io_dispatch_persistence_network_or_execution_path(self):
        source_path = Path(runtime.__file__).resolve()
        self.assertEqual(source_path.name, "core_0_1_transcript_runtime.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imported_roots = set()
        called_names = set()
        attribute_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    attribute_calls.add(node.func.attr)

        forbidden_imports = {
            "asyncio", "http", "logging", "multiprocessing", "os", "pathlib",
            "pickle", "requests", "shutil", "socket", "sqlite3", "subprocess",
            "sys", "tempfile", "threading", "urllib", "webbrowser",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden_imports))

        forbidden_calls = {
            "eval", "exec", "compile", "open", "print", "input", "__import__",
            "system", "popen", "run", "call", "Popen", "send", "sendall",
            "connect", "write_text", "write_bytes", "unlink", "remove",
        }
        self.assertTrue(called_names.isdisjoint(forbidden_calls))
        self.assertTrue(attribute_calls.isdisjoint(forbidden_calls))

        for forbidden_text in (
            "globals()[", "locals()[", "getattr(", "setattr(", "os.system",
            "subprocess", "socket.", "requests.", "urllib.",
        ):
            self.assertNotIn(forbidden_text, source)


if __name__ == "__main__":
    unittest.main()
