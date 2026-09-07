"""Bounded Package I-1 checks for the Core 0.1 transport kernel."""

from __future__ import annotations

import json
import unittest
from unittest import mock

import core_0_1_transport_kernel as kernel


class TransportKernelTests(unittest.TestCase):
    def test_01_valid_ascii_utf8_returns_exact_text(self) -> None:
        result = kernel.inspect_source_bytes(b"WITH", "fixture-ascii")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.decoded_text, "WITH")
        self.assertEqual(result.reasons, ())

    def test_02_valid_non_ascii_utf8_returns_exact_text(self) -> None:
        text = "\u05e9\u05dc\u05d5\u05dd"
        result = kernel.inspect_source_bytes(
            text.encode("utf-8"),
            "fixture-unicode",
        )
        self.assertTrue(result.succeeded)
        self.assertEqual(result.decoded_text, text)

    def test_03_canonical_equivalents_remain_scalar_distinct(self) -> None:
        precomposed = kernel.inspect_source_bytes(
            "\u00e9".encode("utf-8"),
            "fixture-precomposed",
        )
        decomposed = kernel.inspect_source_bytes(
            "e\u0301".encode("utf-8"),
            "fixture-decomposed",
        )
        self.assertNotEqual(precomposed.decoded_text, decomposed.decoded_text)
        self.assertEqual(len(precomposed.decoded_text or ""), 1)
        self.assertEqual(len(decomposed.decoded_text or ""), 2)

    def test_04_empty_bytes_decode_to_empty_scalar_sequence(self) -> None:
        result = kernel.inspect_source_bytes(b"", "fixture-empty")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.decoded_text, "")
        self.assertEqual(result.reasons, ())

    def test_05_lone_continuation_byte_returns_invalid_utf8(self) -> None:
        result = kernel.inspect_source_bytes(b"\x80", "fixture-continuation")
        self.assertFalse(result.succeeded)
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (kernel.INVALID_UTF8,),
        )
        self.assertIsNone(result.reasons[0].location)

    def test_06_truncated_multibyte_sequence_returns_invalid_utf8(self) -> None:
        result = kernel.inspect_source_bytes(b"\xe2\x82", "fixture-truncated")
        self.assertFalse(result.succeeded)
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (kernel.INVALID_UTF8,),
        )

    def test_07_invalid_utf8_returns_no_decoded_text(self) -> None:
        result = kernel.inspect_source_bytes(b"\xff", "fixture-invalid")
        self.assertIsNone(result.decoded_text)
        self.assertTrue(result.reasons)

    def test_08_invalid_utf8_never_inserts_replacement_character(self) -> None:
        result = kernel.inspect_source_bytes(b"A\xffB", "fixture-no-repair")
        self.assertIsNone(result.decoded_text)
        serialized = kernel.serialize_transport_result(result)
        self.assertNotIn("\ufffd", serialized)
        self.assertNotIn("\\ufffd", serialized.lower())

    def test_09_leading_bom_returns_bom_forbidden(self) -> None:
        result = kernel.inspect_source_bytes(
            b"\xef\xbb\xbfWITH",
            "fixture-bom",
        )
        self.assertFalse(result.succeeded)
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (kernel.UTF8_BOM_FORBIDDEN,),
        )

    def test_10_bom_reason_uses_byte_span_zero_to_three(self) -> None:
        result = kernel.inspect_source_bytes(
            b"\xef\xbb\xbf",
            "fixture-bom-span",
        )
        location = result.reasons[0].location
        self.assertIsNotNone(location)
        self.assertEqual(location.unit, "BYTE")
        self.assertEqual(location.start_offset, 0)
        self.assertEqual(location.end_offset, 3)

    def test_11_valid_leading_bom_releases_no_decoded_text(self) -> None:
        result = kernel.inspect_source_bytes(
            b"\xef\xbb\xbfA",
            "fixture-bom-no-text",
        )
        self.assertIsNone(result.decoded_text)

    def test_12_truncated_bom_prefix_is_invalid_not_bom_reason(self) -> None:
        result = kernel.inspect_source_bytes(b"\xef\xbb", "fixture-bom-prefix")
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (kernel.INVALID_UTF8,),
        )
        self.assertNotIn(
            kernel.UTF8_BOM_FORBIDDEN,
            tuple(reason.code for reason in result.reasons),
        )

    def test_13_non_leading_ufeff_passes_transport_unchanged(self) -> None:
        text = "A\ufeffB"
        result = kernel.inspect_source_bytes(
            text.encode("utf-8"),
            "fixture-inner-feff",
        )
        self.assertTrue(result.succeeded)
        self.assertEqual(result.decoded_text, text)

    def test_14_bom_plus_later_invalid_bytes_returns_both_reasons(self) -> None:
        result = kernel.inspect_source_bytes(
            b"\xef\xbb\xbfA\x80",
            "fixture-bom-invalid",
        )
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (
                kernel.UTF8_BOM_FORBIDDEN,
                kernel.INVALID_UTF8,
            ),
        )
        self.assertIsNone(result.decoded_text)

    def test_15_reasons_are_deduplicated_and_ordered(self) -> None:
        bom = kernel.ReasonRecord(
            code=kernel.UTF8_BOM_FORBIDDEN,
            message="first wording",
            location=kernel.ByteSpan(start_offset=0, end_offset=3),
        )
        duplicate_bom = kernel.ReasonRecord(
            code=kernel.UTF8_BOM_FORBIDDEN,
            message="different non-normative wording",
            location=kernel.ByteSpan(start_offset=0, end_offset=3),
        )
        invalid = kernel.ReasonRecord(
            code=kernel.INVALID_UTF8,
            location=None,
        )
        ordered = kernel._deduplicate_and_order_reasons(
            (invalid, duplicate_bom, bom, invalid)
        )
        self.assertEqual(len(ordered), 2)
        self.assertEqual(
            tuple(reason.code for reason in ordered),
            (
                kernel.UTF8_BOM_FORBIDDEN,
                kernel.INVALID_UTF8,
            ),
        )

    def test_16_success_json_omits_source_and_counts_scalars(self) -> None:
        text = "e\u0301"
        result = kernel.inspect_source_bytes(
            text.encode("utf-8"),
            "fixture-success-json",
        )
        serialized = kernel.serialize_transport_result(result)
        payload = json.loads(serialized)
        self.assertEqual(payload["decoded_scalar_count"], 2)
        self.assertNotIn("decoded_text", payload)
        self.assertNotIn(text, serialized)
        self.assertEqual(payload["reasons"], [])

    def test_17_failure_json_contains_code_and_byte_span(self) -> None:
        result = kernel.inspect_source_bytes(
            b"\xef\xbb\xbf",
            "fixture-failure-json",
        )
        payload = json.loads(kernel.serialize_transport_result(result))
        self.assertEqual(payload["transport_result"], "failed")
        self.assertEqual(
            payload["reasons"],
            [
                {
                    "code": kernel.UTF8_BOM_FORBIDDEN,
                    "location": {
                        "unit": "BYTE",
                        "start_offset": 0,
                        "end_offset": 3,
                    },
                }
            ],
        )

    def test_18_json_uses_exact_protocol_identifiers(self) -> None:
        result = kernel.inspect_source_bytes(
            b"A",
            "\u00e9",
        )
        serialized = kernel.serialize_transport_result(result)
        payload = json.loads(serialized)
        self.assertEqual(payload["schema"], "gart-transport-observation-0.1")
        self.assertEqual(payload["profile"], "core-0.1")
        self.assertEqual(payload["observation_kind"], "source-transport")
        self.assertEqual(payload["transport_result"], "decoded")
        self.assertIn("\\u00e9", serialized)

    def test_19_reference_json_field_order_is_stable(self) -> None:
        result = kernel.inspect_source_bytes(b"A", "fixture-order")
        serialized = kernel.serialize_transport_result(result)
        expected_keys = (
            '"schema"',
            '"profile"',
            '"observation_kind"',
            '"source_id"',
            '"transport_result"',
            '"decoded_scalar_count"',
            '"reasons"',
        )
        positions = tuple(serialized.index(key) for key in expected_keys)
        self.assertEqual(positions, tuple(sorted(positions)))

    def test_20_json_has_no_final_newline(self) -> None:
        result = kernel.inspect_source_bytes(b"A", "fixture-no-newline")
        serialized = kernel.serialize_transport_result(result)
        self.assertFalse(serialized.endswith("\n"))
        self.assertFalse(serialized.endswith("\r"))

    def test_21_json_omits_private_and_unapproved_data(self) -> None:
        secret = "TOP_SECRET_PAYLOAD_\u03a9"
        result = kernel.inspect_source_bytes(
            secret.encode("utf-8"),
            "fixture-private",
        )
        serialized = kernel.serialize_transport_result(result)
        payload = json.loads(serialized)

        self.assertNotIn(secret, serialized)
        self.assertNotIn("decoded_text", payload)
        self.assertNotIn("raw_bytes", payload)
        self.assertNotIn("timestamp", payload)
        self.assertNotIn("stack_trace", payload)
        self.assertNotIn("process_id", payload)
        self.assertNotIn("C:\\\\", serialized)
        self.assertNotIn("/home/", serialized)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("NaN", serialized)
        self.assertNotIn("Infinity", serialized)

    def test_22_repeated_calls_are_equal_and_json_is_identical(self) -> None:
        first = kernel.inspect_source_bytes(
            b"\xef\xbb\xbfA\x80",
            "fixture-repeat",
        )
        second = kernel.inspect_source_bytes(
            b"\xef\xbb\xbfA\x80",
            "fixture-repeat",
        )
        self.assertEqual(first, second)
        self.assertEqual(
            kernel.serialize_transport_result(first),
            kernel.serialize_transport_result(second),
        )

    def test_23_kernel_has_no_forbidden_operational_path(self) -> None:
        forbidden_names = {
            "open",
            "eval",
            "exec",
            "compile",
            "__import__",
            "system",
            "popen",
            "Popen",
            "run",
            "socket",
            "create_connection",
            "urlopen",
            "requests",
            "logging",
            "subprocess",
            "pathlib",
            "threading",
            "multiprocessing",
            "asyncio",
            "ctypes",
            "evaluate",
            "execute",
        }

        code_objects = []

        def add_code_object(value: object) -> None:
            code = getattr(value, "__code__", None)
            if code is not None:
                code_objects.append(code)
            if isinstance(value, property):
                for accessor in (value.fget, value.fset, value.fdel):
                    if accessor is not None:
                        add_code_object(accessor)

        for value in vars(kernel).values():
            if isinstance(value, type) and value.__module__ == kernel.__name__:
                for member in vars(value).values():
                    add_code_object(member)
            elif getattr(value, "__module__", None) == kernel.__name__:
                add_code_object(value)

        all_names = set()
        pending = list(code_objects)
        while pending:
            code = pending.pop()
            all_names.update(code.co_names)
            for constant in code.co_consts:
                if hasattr(constant, "co_names") and hasattr(constant, "co_consts"):
                    pending.append(constant)

        self.assertTrue(forbidden_names.isdisjoint(all_names))

        blocked = AssertionError("A forbidden operational function was called.")
        with (
            mock.patch("builtins.open", side_effect=blocked),
            mock.patch("socket.socket", side_effect=blocked),
            mock.patch("socket.create_connection", side_effect=blocked),
            mock.patch("subprocess.Popen", side_effect=blocked),
            mock.patch("subprocess.run", side_effect=blocked),
            mock.patch("os.system", side_effect=blocked),
            mock.patch("logging.Logger._log", side_effect=blocked),
        ):
            result = kernel.inspect_source_bytes(b"A", "fixture-isolated")
            serialized = kernel.serialize_transport_result(result)

        self.assertTrue(result.succeeded)
        self.assertEqual(json.loads(serialized)["transport_result"], "decoded")


if __name__ == "__main__":
    unittest.main()
