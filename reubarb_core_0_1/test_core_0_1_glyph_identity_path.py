"""I-20 acceptance checks for the identity-only native-glyph endpoint."""
from __future__ import annotations

import ast
import contextlib
from dataclasses import fields
import inspect
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import core_0_1_glyph_encoding as glyph_encoding
import core_0_1_glyph_identity_value as i16
import core_0_1_glyph_recognizer as glyph_recognizer
import core_0_1_glyph_source_integration as i15
import core_0_1_lexical_frontend as lexical
import core_0_1_source_profile as source_profile


class GlyphIdentityPathTests(unittest.TestCase):
    def test_01_existing_i16_function_is_the_terminal_interface(self):
        signature = inspect.signature(i16.form_glyph_identity_value)
        parameters = tuple(signature.parameters.values())
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters[0].name, "source_text")
        self.assertIs(parameters[0].default, inspect.Parameter.empty)

    def test_02_exact_five_mapping_inventory_reaches_identity_endpoint(self):
        expected = (
            (2, "\uE100", "U+E100"),
            (3, "\uE101", "U+E101"),
            (4, "\uE102", "U+E102"),
            (5, "\uE103", "U+E103"),
            (6, "\uE104", "U+E104"),
        )
        actual = tuple(
            (mapping.design_id, mapping.scalar, mapping.code_point_label)
            for mapping in glyph_encoding.APPROVED_GLYPH_ENCODINGS
        )
        self.assertEqual(actual, expected)
        for design_id, scalar, label in expected:
            with self.subTest(design_id=design_id):
                result = i16.form_glyph_identity_value(scalar)
                self.assertEqual(result.outcome, i16.VALUE_AVAILABLE)
                self.assertEqual(result.reasons, ())
                self.assertIsNotNone(result.value)
                if result.value is not None:
                    self.assertEqual(result.value.design_id, design_id)
                    self.assertEqual(result.value.code_point_label, label)

    def test_03_success_retains_complete_i15_parse_and_recognition_provenance(self):
        for mapping in glyph_encoding.APPROVED_GLYPH_ENCODINGS:
            with self.subTest(design_id=mapping.design_id):
                result = i16.form_glyph_identity_value(mapping.scalar)
                observed = result.source_observation
                parsed = observed.parse_result
                instruction = parsed.instruction
                candidate = observed.observation
                self.assertEqual(parsed.outcome, i15.PARSED)
                self.assertEqual(
                    parsed.source_profile_outcome, source_profile.CONTEXT_REQUIRED
                )
                self.assertIsNotNone(instruction)
                self.assertIsNotNone(candidate)
                if instruction is None or candidate is None:
                    continue
                self.assertEqual(instruction.candidate, mapping.scalar)
                self.assertEqual(
                    (
                        instruction.candidate_span.start_offset,
                        instruction.candidate_span.end_offset,
                    ),
                    (0, 1),
                )
                self.assertEqual(
                    (
                        instruction.instruction_span.start_offset,
                        instruction.instruction_span.end_offset,
                    ),
                    (0, 1),
                )
                self.assertEqual(observed.outcome, i15.OBSERVED)
                self.assertEqual(
                    candidate.outcome,
                    glyph_recognizer.RecognitionOutcome.RECOGNIZED.value,
                )
                self.assertEqual(candidate.design_id, mapping.design_id)
                self.assertEqual(candidate.code_point_label, mapping.code_point_label)

    def test_04_general_lexer_stays_context_required_while_i15_resolves_glyph(self):
        scalar = glyph_encoding.APPROVED_SCALARS[0]
        lexed = lexical.lex_source(scalar)
        parsed = i15.parse_glyph_source_candidate(scalar)
        endpoint = i16.form_glyph_identity_value(scalar)
        self.assertEqual(lexed.outcome, lexical.CONTEXT_REQUIRED)
        self.assertIsNone(lexed.stream)
        self.assertEqual(
            tuple(reason.code for reason in lexed.reasons),
            (source_profile.LEXICAL_CONTEXT_REQUIRED,),
        )
        self.assertEqual(parsed.outcome, i15.PARSED)
        self.assertEqual(endpoint.outcome, i16.VALUE_AVAILABLE)

    def test_05_approved_trivia_preserves_candidate_and_instruction_spans(self):
        scalar = glyph_encoding.APPROVED_SCALARS[3]
        prefix = "\n\t//private note\r\n"
        source = prefix + scalar + " \t  "
        result = i16.form_glyph_identity_value(source)
        self.assertEqual(result.outcome, i16.VALUE_AVAILABLE)
        instruction = result.source_observation.parse_result.instruction
        candidate = result.source_observation.observation
        self.assertIsNotNone(instruction)
        self.assertIsNotNone(candidate)
        if instruction is None or candidate is None:
            return
        self.assertEqual(instruction.candidate, scalar)
        self.assertEqual(candidate.candidate, scalar)
        self.assertEqual(
            (
                instruction.candidate_span.start_offset,
                instruction.candidate_span.end_offset,
            ),
            (len(prefix), len(prefix) + 1),
        )
        self.assertEqual(
            (
                instruction.instruction_span.start_offset,
                instruction.instruction_span.end_offset,
            ),
            (0, len(source)),
        )

    def test_06_endpoint_value_is_identity_metadata_only_and_g3_is_not_fulfillment(self):
        value = i16.form_glyph_identity_value(
            glyph_encoding.APPROVED_SCALARS[1]
        ).value
        self.assertIsNotNone(value)
        if value is None:
            return
        self.assertEqual(value.design_id, 3)
        self.assertEqual(
            tuple(field.name for field in fields(value)),
            ("design_id", "code_point_label"),
        )
        self.assertFalse(hasattr(value, "__dict__"))
        for name in (
            "fulfilled", "fulfillment", "recon", "partner", "matrix",
            "identity_axis", "charge", "authorized", "source_certification",
            "transition", "execute", "state",
        ):
            self.assertFalse(hasattr(value, name))

    def test_07_repeated_calls_have_deterministic_metadata_without_target_equality(self):
        scalar = glyph_encoding.APPROVED_SCALARS[-1]
        first = i16.form_glyph_identity_value(scalar)
        second = i16.form_glyph_identity_value(scalar)
        self.assertEqual(first.outcome, second.outcome)
        self.assertIsNotNone(first.value)
        self.assertIsNotNone(second.value)
        if first.value is None or second.value is None:
            return
        self.assertEqual(first.value.design_id, second.value.design_id)
        self.assertEqual(
            first.value.code_point_label, second.value.code_point_label
        )
        self.assertIs(i16.GlyphIdentityValue.__eq__, object.__eq__)
        self.assertIs(i16.GlyphIdentityResult.__eq__, object.__eq__)

    def test_08_unmapped_single_scalars_return_exact_no_value_observation(self):
        for scalar in ("\uE0FF", "\uE105", "\U0001F604"):
            with self.subTest(code_point=f"U+{ord(scalar):04X}"):
                result = i16.form_glyph_identity_value(scalar)
                candidate = result.source_observation.observation
                self.assertEqual(result.outcome, i16.NO_VALUE)
                self.assertIsNone(result.value)
                self.assertEqual(
                    tuple(reason.code for reason in result.reasons),
                    (i15.UNRECOGNIZED_GLYPH,),
                )
                self.assertIsNotNone(candidate)
                if candidate is not None:
                    self.assertEqual(
                        candidate.outcome,
                        glyph_recognizer.RecognitionOutcome.UNRECOGNIZED.value,
                    )
                    self.assertIsNone(candidate.design_id)
                    self.assertEqual(
                        (
                            candidate.candidate_span.start_offset,
                            candidate.candidate_span.end_offset,
                        ),
                        (0, 1),
                    )

    def test_09_empty_and_trivia_only_sources_preserve_empty_glyph_reason(self):
        for source in ("", " \t\n", "//note\r\n\t"):
            with self.subTest(length=len(source)):
                result = i16.form_glyph_identity_value(source)
                self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
                self.assertIsNone(result.value)
                self.assertEqual(
                    tuple(reason.code for reason in result.reasons),
                    (i15.EMPTY_GLYPH_SOURCE,),
                )

    def test_10_multiple_tokens_preserve_incomplete_relationship_reason(self):
        source = " ".join(glyph_encoding.APPROVED_SCALARS[:2])
        result = i16.form_glyph_identity_value(source)
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (i15.INCOMPLETE_GLYPH_RELATIONSHIP,),
        )
        location = result.reasons[0].location
        self.assertIsNotNone(location)
        if location is not None:
            self.assertEqual((location.start_offset, location.end_offset), (2, 3))

    def test_11_contiguous_multi_scalar_form_preserves_unauthorized_reason(self):
        source = "".join(glyph_encoding.APPROVED_SCALARS[:2])
        result = i16.form_glyph_identity_value(source)
        self.assertEqual(result.outcome, i15.SYNTAX_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (i15.UNAUTHORIZED_SOURCE_FORM,),
        )

    def test_12_source_control_failures_preserve_i4_reasons_and_locations(self):
        scalar = glyph_encoding.APPROVED_SCALARS[0]
        cases = (scalar + "\x00", "\ufeff" + scalar, scalar + "\u202e")
        for source in cases:
            with self.subTest(code_points=tuple(ord(character) for character in source)):
                direct = source_profile.inspect_source_profile(source)
                result = i16.form_glyph_identity_value(source)
                self.assertEqual(direct.outcome, source_profile.PROFILE_REJECTED)
                self.assertEqual(result.outcome, i15.SOURCE_REJECTED)
                self.assertIsNone(result.value)
                self.assertEqual(
                    result.source_observation.parse_result.source_profile_outcome,
                    direct.outcome,
                )
                self.assertEqual(
                    tuple((reason.code, reason.location) for reason in result.reasons),
                    tuple((reason.code, reason.location) for reason in direct.reasons),
                )

    def test_13_surrogate_host_text_preserves_non_scalar_profile_stop(self):
        source = glyph_encoding.APPROVED_SCALARS[0] + "\ud800"
        direct = source_profile.inspect_source_profile(source)
        result = i16.form_glyph_identity_value(source)
        self.assertEqual(direct.outcome, source_profile.INPUT_REJECTED)
        self.assertEqual(result.outcome, i15.SOURCE_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(
            result.source_observation.parse_result.source_profile_outcome,
            source_profile.INPUT_REJECTED,
        )
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (source_profile.NON_SCALAR_INPUT,),
        )
        self.assertIsNone(result.reasons[0].location)

    def test_14_oversized_source_preserves_profile_limit_without_partial_value(self):
        source = "A" * (source_profile.MAX_SOURCE_CODE_POINTS + 1)
        result = i16.form_glyph_identity_value(source)
        self.assertEqual(result.outcome, i15.SOURCE_REJECTED)
        self.assertIsNone(result.value)
        self.assertEqual(
            result.source_observation.parse_result.source_profile_outcome,
            source_profile.LIMITED,
        )
        self.assertEqual(
            tuple(reason.code for reason in result.reasons),
            (source_profile.SOURCE_PROFILE_LIMIT,),
        )

    def test_15_non_strings_and_subclasses_are_rejected_without_hooks(self):
        calls: list[str] = []

        class Hostile:
            def __str__(self):
                calls.append("str")
                return glyph_encoding.APPROVED_SCALARS[0]

            def __repr__(self):
                calls.append("repr")
                return glyph_encoding.APPROVED_SCALARS[0]

            def __eq__(self, other):
                calls.append("eq")
                return True

        class TextSubclass(str):
            pass

        inputs = (
            None,
            b"\xee\x84\x80",
            0xE100,
            [glyph_encoding.APPROVED_SCALARS[0]],
            Hostile(),
            TextSubclass(glyph_encoding.APPROVED_SCALARS[0]),
        )
        for source in inputs:
            result = i16.form_glyph_identity_value(source)
            self.assertEqual(result.outcome, i15.INPUT_REJECTED)
            self.assertIsNone(result.value)
            self.assertEqual(
                tuple(reason.code for reason in result.reasons),
                ("GART.CORE_0_1.HOST.EXPECTED_STRING",),
            )
        self.assertEqual(calls, [])

    def test_16_source_profile_and_recognizer_resource_stops_produce_no_value(self):
        with patch.object(
            source_profile, "_make_source_map", side_effect=MemoryError
        ):
            profile_failure = i16.form_glyph_identity_value("A")
        self.assertEqual(profile_failure.outcome, i15.SOURCE_REJECTED)
        self.assertIsNone(profile_failure.value)
        self.assertEqual(
            profile_failure.source_observation.parse_result.source_profile_outcome,
            source_profile.HOST_FAILED,
        )
        self.assertEqual(
            tuple(reason.code for reason in profile_failure.reasons),
            (source_profile.RESOURCE_EXHAUSTED,),
        )

        scalar = glyph_encoding.APPROVED_SCALARS[0]
        with patch.object(
            i15.glyph_recognizer,
            "recognize_glyph_candidate",
            side_effect=MemoryError,
        ):
            recognizer_failure = i16.form_glyph_identity_value(scalar)
        self.assertEqual(recognizer_failure.outcome, i15.HOST_FAILED)
        self.assertIsNone(recognizer_failure.value)
        self.assertEqual(
            tuple(reason.code for reason in recognizer_failure.reasons),
            (i15.HOST_FAILED,),
        )

    def test_17_i16_invariant_and_allocation_failures_have_no_partial_value(self):
        scalar = glyph_encoding.APPROVED_SCALARS[0]
        with patch.object(
            i16.glyph_encoding, "get_encoding_by_design_id", return_value=None
        ):
            invariant_failure = i16.form_glyph_identity_value(scalar)
        self.assertEqual(invariant_failure.outcome, i16.HOST_FAILED)
        self.assertIsNone(invariant_failure.value)
        self.assertEqual(
            tuple(reason.code for reason in invariant_failure.reasons),
            (i16.GLYPH_IDENTITY_INVARIANT_FAILURE,),
        )

        with patch.object(i16, "_construct_glyph_identity", side_effect=MemoryError):
            allocation_failure = i16.form_glyph_identity_value(scalar)
        self.assertEqual(allocation_failure.outcome, i16.HOST_FAILED)
        self.assertIsNone(allocation_failure.value)
        self.assertEqual(
            tuple(reason.code for reason in allocation_failure.reasons),
            (i16.RESOURCE_EXHAUSTED,),
        )

    def test_18_i15_is_called_once_and_stops_or_interruptions_are_not_retried(self):
        scalar = glyph_encoding.APPROVED_SCALARS[0]
        for source in (scalar, " ".join(glyph_encoding.APPROVED_SCALARS[:2])):
            with self.subTest(source_length=len(source)):
                with patch.object(
                    i16.glyph_source,
                    "observe_glyph_source_candidate",
                    wraps=i15.observe_glyph_source_candidate,
                ) as observe:
                    i16.form_glyph_identity_value(source)
                observe.assert_called_once_with(source)

        for defect in (RuntimeError, KeyboardInterrupt):
            with self.subTest(defect=defect.__name__):
                with patch.object(
                    i16.glyph_source,
                    "observe_glyph_source_candidate",
                    side_effect=defect,
                ) as observe:
                    with self.assertRaises(defect):
                        i16.form_glyph_identity_value(scalar)
                self.assertEqual(observe.call_count, 1)

    def test_19_calls_are_silent_source_redacted_and_leave_mapping_unchanged(self):
        scalar = glyph_encoding.APPROVED_SCALARS[2]
        mapping_before = tuple(
            (
                mapping.design_id,
                mapping.scalar,
                mapping.code_point_label,
                mapping.shortcut_prefix,
            )
            for mapping in glyph_encoding.APPROVED_GLYPH_ENCODINGS
        )
        source = "//private-marker\r\n" + scalar
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = i16.form_glyph_identity_value(source)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        for value in (
            result,
            result.value,
            result.source_observation,
            result.source_observation.parse_result,
            result.source_observation.parse_result.instruction,
        ):
            self.assertNotIn("private-marker", repr(value))
        mapping_after = tuple(
            (
                mapping.design_id,
                mapping.scalar,
                mapping.code_point_label,
                mapping.shortcut_prefix,
            )
            for mapping in glyph_encoding.APPROVED_GLYPH_ENCODINGS
        )
        self.assertEqual(mapping_after, mapping_before)

    def test_20_endpoint_import_graph_has_no_new_language_or_operational_path(self):
        module_paths = (
            Path(i16.__file__).resolve(),
            Path(i15.__file__).resolve(),
        )
        imported_roots: set[str] = set()
        called_names: set[str] = set()
        attribute_calls: set[str] = set()
        defined_names: set[str] = set()
        for module_path in module_paths:
            source = module_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(
                        alias.name.split(".")[0] for alias in node.names
                    )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        called_names.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        attribute_calls.add(node.func.attr)
                elif isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    defined_names.add(node.name)

        allowed_imports = {
            "__future__",
            "bisect",
            "core_0_1_glyph_encoding",
            "core_0_1_glyph_recognizer",
            "core_0_1_glyph_source_integration",
            "core_0_1_source_profile",
            "dataclasses",
            "typing",
        }
        forbidden_imports = {
            "asyncio", "http", "logging", "multiprocessing", "os", "pathlib",
            "pickle", "requests", "shutil", "socket", "sqlite3", "subprocess",
            "sys", "tempfile", "threading", "urllib", "webbrowser",
        }
        forbidden_calls = {
            "__import__", "compile", "connect", "eval", "exec", "input", "open",
            "popen", "print", "remove", "run", "send", "sendall", "system",
            "unlink", "write_bytes", "write_text",
        }
        forbidden_action_fragments = (
            "authoriz", "certif", "charg", "clos", "congruen", "execut",
            "fulfil", "matrix", "new_occurrence", "occurrence", "pair",
            "persist", "recon", "record_attempt", "retry", "schedule",
            "state", "transition",
        )
        self.assertEqual(imported_roots, allowed_imports)
        self.assertTrue(imported_roots.isdisjoint(forbidden_imports))
        self.assertTrue(called_names.isdisjoint(forbidden_calls))
        self.assertTrue(attribute_calls.isdisjoint(forbidden_calls))
        audited_names = defined_names | set(i15.__all__) | set(i16.__all__)
        for name in audited_names:
            folded = name.casefold()
            for fragment in forbidden_action_fragments:
                self.assertNotIn(fragment, folded)


if __name__ == "__main__":
    unittest.main()
