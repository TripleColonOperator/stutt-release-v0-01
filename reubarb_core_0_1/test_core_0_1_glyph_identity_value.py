"""I-16 checks for inert immutable standalone glyph-identity values."""
from __future__ import annotations

import ast
import contextlib
from dataclasses import FrozenInstanceError, fields
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import core_0_1_glyph_encoding as glyph_encoding
import core_0_1_glyph_identity_value as i16
import core_0_1_glyph_recognizer as glyph_recognizer
import core_0_1_glyph_source_integration as i15
import core_0_1_source_profile as source_profile


class GlyphIdentityValueTests(unittest.TestCase):
    def test_01_each_approved_standalone_glyph_forms_exact_identity(self):
        for mapping in glyph_encoding.APPROVED_GLYPH_ENCODINGS:
            with self.subTest(design_id=mapping.design_id):
                result = i16.form_glyph_identity_value(mapping.scalar)
                self.assertEqual(result.outcome, i16.VALUE_AVAILABLE)
                self.assertTrue(result.succeeded)
                self.assertIsNotNone(result.value)
                if result.value is None:
                    continue
                self.assertEqual(result.value.design_id, mapping.design_id)
                self.assertEqual(
                    result.value.code_point_label, mapping.code_point_label
                )
                self.assertEqual(result.reasons, ())

    def test_02_i15_trivia_boundary_is_preserved(self):
        scalar = glyph_encoding.APPROVED_SCALARS[2]
        result = i16.form_glyph_identity_value(f"\n//note\r\n\t{scalar}  ")
        self.assertEqual(result.outcome, i16.VALUE_AVAILABLE)
        self.assertEqual(result.value.design_id, 4)
        self.assertEqual(
            result.source_observation.parse_result.source_profile_outcome,
            source_profile.CONTEXT_REQUIRED,
        )

    def test_03_value_surface_contains_identity_metadata_only(self):
        value = i16.form_glyph_identity_value(
            glyph_encoding.APPROVED_SCALARS[0]
        ).value
        self.assertIsNotNone(value)
        self.assertEqual(
            tuple(field.name for field in fields(value)),
            ("design_id", "code_point_label"),
        )
        self.assertFalse(hasattr(value, "__dict__"))

    def test_04_g3_value_makes_no_fulfillment_or_execution_claim(self):
        value = i16.form_glyph_identity_value(
            glyph_encoding.APPROVED_SCALARS[1]
        ).value
        self.assertIsNotNone(value)
        self.assertEqual(value.design_id, 3)
        for name in (
            "fulfilled", "fulfillment", "recon", "authorized", "state",
            "execute", "transition", "partner",
        ):
            self.assertFalse(hasattr(value, name))

    def test_05_value_is_frozen_without_target_equality_semantics(self):
        value = i16.form_glyph_identity_value(
            glyph_encoding.APPROVED_SCALARS[0]
        ).value
        self.assertIsNotNone(value)
        with self.assertRaises(FrozenInstanceError):
            value.design_id = 6  # type: ignore[misc]
        self.assertIs(i16.GlyphIdentityValue.__eq__, object.__eq__)

    def test_06_unsupported_direct_construction_is_rejected(self):
        with self.assertRaises(ValueError):
            i16.GlyphIdentityValue(2, "U+E100", object())
        with self.assertRaises(ValueError):
            i16.GlyphIdentityValue(1, "U+E0FF", object())
        with self.assertRaises(ValueError):
            i16.GlyphIdentityValue(99, "U+E163", object())

        class HostileDesignId:
            def __eq__(self, other):
                raise AssertionError("unsupported equality hook was invoked")

        with patch.object(
            i16.glyph_encoding,
            "get_encoding_by_design_id",
            side_effect=AssertionError("lookup occurred before host type validation"),
        ) as lookup:
            with self.assertRaises(ValueError):
                i16.GlyphIdentityValue(
                    HostileDesignId(), "U+E100", i16._SEAL
                )
        lookup.assert_not_called()

    def test_07_unrecognized_scalar_forms_no_value(self):
        result = i16.form_glyph_identity_value("\U0001F604")
        self.assertEqual(result.outcome, i16.NO_VALUE)
        self.assertFalse(result.succeeded)
        self.assertIsNone(result.value)
        self.assertEqual(
            result.source_observation.observation.outcome,
            glyph_recognizer.RecognitionOutcome.UNRECOGNIZED.value,
        )
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (i15.UNRECOGNIZED_GLYPH,),
        )

    def test_08_two_glyph_tokens_form_no_value(self):
        source = " ".join(glyph_encoding.APPROVED_SCALARS[:2])
        result = i16.form_glyph_identity_value(source)
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(
            result.source_observation.outcome, i15.SYNTAX_REJECTED
        )
        self.assertEqual(
            result.reasons[0].code, i15.INCOMPLETE_GLYPH_RELATIONSHIP
        )

    def test_09_multi_scalar_source_form_forms_no_value(self):
        result = i16.form_glyph_identity_value("leg")
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(result.reasons[0].code, i15.UNAUTHORIZED_SOURCE_FORM)

    def test_10_empty_source_forms_no_value(self):
        result = i16.form_glyph_identity_value("  //comment\r\n\t")
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(result.reasons[0].code, i15.EMPTY_GLYPH_SOURCE)

    def test_11_source_profile_rejection_is_retained(self):
        result = i16.form_glyph_identity_value("x\x00")
        self.assertEqual(result.outcome, i15.SOURCE_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(result.source_observation.outcome, i15.SOURCE_REJECTED)
        self.assertEqual(
            result.source_observation.parse_result.source_profile_outcome,
            source_profile.PROFILE_REJECTED,
        )
        self.assertEqual(result.reasons, result.source_observation.reasons)

    def test_12_non_string_input_is_not_coerced(self):
        for source in (None, b"\xee\x84\x80", 0xE100, ["\uE100"]):
            with self.subTest(host_type=type(source).__name__):
                result = i16.form_glyph_identity_value(source)
                self.assertEqual(result.outcome, i15.INPUT_REJECTED)
                self.assertIsNone(result.value)
                self.assertEqual(
                    result.source_observation.outcome, i15.INPUT_REJECTED
                )

    def test_13_repeated_reads_have_repeatable_identity_metadata(self):
        scalar = glyph_encoding.APPROVED_SCALARS[-1]
        first = i16.form_glyph_identity_value(scalar)
        second = i16.form_glyph_identity_value(scalar)
        self.assertEqual(first.value.design_id, second.value.design_id)
        self.assertEqual(
            first.value.code_point_label, second.value.code_point_label
        )
        self.assertIs(i16.GlyphIdentityValue.__eq__, object.__eq__)

    def test_14_representations_and_calls_are_silent_and_source_free(self):
        scalar = glyph_encoding.APPROVED_SCALARS[-1]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            success = i16.form_glyph_identity_value(scalar)
            failure = i16.form_glyph_identity_value("private-unrecognized")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        for value in (success, success.value, failure):
            self.assertNotIn(scalar, repr(value))
            self.assertNotIn("private-unrecognized", repr(value))

    def test_15_controlled_host_failures_return_no_partial_value(self):
        scalar = glyph_encoding.APPROVED_SCALARS[0]
        with patch.object(i16, "_construct_glyph_identity", side_effect=MemoryError):
            result = i16.form_glyph_identity_value(scalar)
        self.assertEqual(result.outcome, i16.HOST_FAILED)
        self.assertIsNone(result.value)
        self.assertEqual(result.reasons[0].code, i16.RESOURCE_EXHAUSTED)

        with patch.object(
            i16.glyph_encoding, "get_encoding_by_design_id", return_value=None
        ):
            result = i16.form_glyph_identity_value(scalar)
        self.assertEqual(result.outcome, i16.HOST_FAILED)
        self.assertIsNone(result.value)
        self.assertEqual(
            result.reasons[0].code, i16.GLYPH_IDENTITY_INVARIANT_FAILURE
        )

        inconsistent_mapping = SimpleNamespace(
            design_id=99,
            scalar=scalar,
            code_point_label="U+E100",
        )
        with patch.object(
            i16.glyph_encoding,
            "get_encoding_by_design_id",
            return_value=inconsistent_mapping,
        ):
            result = i16.form_glyph_identity_value(scalar)
        self.assertEqual(result.outcome, i16.HOST_FAILED)
        self.assertIsNone(result.value)
        self.assertEqual(
            result.reasons[0].code, i16.GLYPH_IDENTITY_INVARIANT_FAILURE
        )

        valid_observation = i15.observe_glyph_source_candidate(scalar)
        recognized = valid_observation.observation
        self.assertIsNotNone(recognized)
        malformed_candidate = i15.GlyphCandidateObservation(
            recognized.candidate,
            recognized.candidate_span,
            glyph_recognizer.RecognitionOutcome.INVALID_INPUT.value,
            None,
            None,
        )
        malformed_observation = i15.GlyphSourceObservationResult(
            i15.OBSERVED,
            valid_observation.parse_result,
            (),
            malformed_candidate,
        )
        with patch.object(
            i16.glyph_source,
            "observe_glyph_source_candidate",
            return_value=malformed_observation,
        ):
            result = i16.form_glyph_identity_value(scalar)
        self.assertEqual(result.outcome, i16.HOST_FAILED)
        self.assertIsNone(result.value)
        self.assertEqual(
            result.reasons[0].code, i16.GLYPH_IDENTITY_INVARIANT_FAILURE
        )

        stopped_parse = i15.GlyphSourceParseResult(
            i15.HOST_FAILED,
            None,
            (i15.GlyphSourceReason(i15.HOST_FAILED),),
            None,
        )
        stopped_observation = i15.GlyphSourceObservationResult(
            i15.HOST_FAILED,
            stopped_parse,
            stopped_parse.reasons,
            None,
        )
        with patch.object(
            i16.glyph_source,
            "observe_glyph_source_candidate",
            return_value=stopped_observation,
        ):
            result = i16.form_glyph_identity_value(scalar)
        self.assertEqual(result.outcome, i15.HOST_FAILED)
        self.assertEqual(result.reasons, stopped_observation.reasons)
        self.assertIsNone(result.value)

        with self.assertRaises(ValueError):
            i16.GlyphIdentityResult(
                i16.VALUE_AVAILABLE, None, valid_observation, ()
            )

    def test_16_module_has_no_operational_or_persistence_path(self):
        source_path = Path(i16.__file__).resolve()
        self.assertEqual(source_path.name, "core_0_1_glyph_identity_value.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        called_names: set[str] = set()
        attribute_calls: set[str] = set()
        defined_names: set[str] = set()
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
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)

        forbidden_imports = {
            "asyncio", "http", "logging", "multiprocessing", "os", "pathlib",
            "pickle", "requests", "shutil", "socket", "sqlite3", "subprocess",
            "sys", "tempfile", "threading", "urllib", "webbrowser",
        }
        forbidden_calls = {
            "eval", "exec", "compile", "open", "print", "input", "__import__",
            "system", "popen", "run", "call", "Popen", "send", "sendall",
            "connect", "write_text", "write_bytes", "unlink", "remove",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden_imports))
        self.assertTrue(called_names.isdisjoint(forbidden_calls))
        self.assertTrue(attribute_calls.isdisjoint(forbidden_calls))
        semantic_fragments = (
            "fulfill", "recon", "authoriz", "execute", "transition", "evaluate",
            "pair", "mutat", "persist", "save", "load", "copy",
        )
        audited_names = defined_names | set(i16.__all__)
        for name in audited_names:
            folded = name.casefold()
            for fragment in semantic_fragments:
                self.assertNotIn(fragment, folded)


if __name__ == "__main__":
    unittest.main()
