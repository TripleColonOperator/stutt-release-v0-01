"""Finite I-7 conformance checks for the approved single reading unit.

Synthetic fixtures only. Observation executes the bounded reading operation;
the observed transcript is never interpreted or executed as instructions.
"""
from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError, replace
from io import StringIO
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import core_0_1_lexical_frontend as lexical
import core_0_1_read_instruction as read
import core_0_1_source_profile as profile
import core_0_1_syntax_skeleton as syntax
import core_0_1_transcript_runtime as runtime


class ReadInstructionTests(unittest.TestCase):
    def admitted(self, payload="Synthetic reviewed transcript."):
        result = runtime.transcriptio(payload, reviewed=True, accepted=True)
        self.assertEqual(result.outcome, runtime.ADMITTED)
        return result.value

    def parsed(self, source):
        result = read.parse_read_unit(lexical.lex_source(source))
        self.assertEqual(result.outcome, read.PARSED)
        self.assertTrue(result.succeeded)
        self.assertIsNotNone(result.instruction)
        self.assertEqual(result.reasons, ())
        return result

    def syntax_failure(self, source, expected_code):
        result = read.parse_read_unit(lexical.lex_source(source))
        self.assertEqual(result.outcome, read.SYNTAX_REJECTED)
        self.assertFalse(result.succeeded)
        self.assertIsNone(result.instruction)
        self.assertEqual(tuple(reason.code for reason in result.reasons),
                         (expected_code,))
        return result

    def test_01_minimal_instruction_has_one_exact_target(self):
        result = self.parsed("leg transcriptA")
        self.assertEqual(result.instruction.target_name, "transcriptA")
        self.assertEqual(result.preparation.outcome, syntax.PREPARED)
        self.assertEqual(result.source_profile_outcome, profile.PROFILE_CHECKED)

    def test_02_one_nonempty_space_tab_run_is_the_horizontal_gap(self):
        for gap in (" ", "\t", "    ", " \t\t "):
            with self.subTest(gap=repr(gap)):
                self.assertEqual(self.parsed("leg" + gap + "name").instruction.target_name,
                                 "name")

    def test_03_surrounding_padding_preserves_comments_and_line_breaks(self):
        for prefix, suffix in (("", "\n"), ("\r\n\t", " \r\n"),
                               ("//\U0001f600\n\n ", " // e\u0301\r\n//end")):
            with self.subTest(prefix=repr(prefix)):
                source = prefix + "leg name" + suffix
                record = self.parsed(source).instruction
                self.assertEqual(record.syntax_input.source_map.source_text, source)
                self.assertEqual(record.target_name, "name")

    def test_04_target_adjacent_to_existing_comment_marker_is_allowed(self):
        record = self.parsed("leg name// trailing comment").instruction
        self.assertEqual(record.target_name, "name")

    def test_05_approved_word_spellings_have_contextual_target_roles(self):
        names = tuple(item.spelling for item in lexical.APPROVED_SPELLINGS
                      if item.spelling != "0")
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(self.parsed("leg " + name).instruction.target_name,
                                 name)

    def test_06_ordinary_ascii_identifier_forms_are_targets(self):
        for name in ("_", "_name2", "a0", "WITHIN", "txt", "TranscriptA", "a00"):
            with self.subTest(name=name):
                self.assertEqual(self.parsed("leg " + name).instruction.target_name,
                                 name)

    def test_07_only_exact_lowercase_leg_selects_the_head(self):
        for source in ("LEG name", "Leg name", "textus name", "WITH name", "0 name"):
            with self.subTest(source=source):
                self.syntax_failure(source, read.EXPECTED_READ_HEAD)

    def test_08_empty_or_padding_only_units_have_no_instruction(self):
        for source in ("", " \t", "\r\n", "//only", " \n//only\r\n\t"):
            with self.subTest(source=repr(source)):
                self.syntax_failure(source, read.EXPECTED_READ_HEAD)

    def test_09_bare_head_requires_a_horizontal_gap(self):
        result = self.syntax_failure("leg", read.EXPECTED_HORIZONTAL_GAP)
        self.assertEqual(result.reasons[0].location.start_offset, 3)
        self.assertEqual(result.reasons[0].location.end_offset, 3)

    def test_10_newlines_and_comments_cannot_replace_the_gap(self):
        for source in ("leg\nname", "leg\r\nname", "leg//note\nname"):
            with self.subTest(source=repr(source)):
                self.syntax_failure(source, read.EXPECTED_HORIZONTAL_GAP)

    def test_11_horizontal_gap_must_be_followed_immediately_by_a_word(self):
        for source in ("leg ", "leg\t", "leg \nname", "leg //note\nname"):
            with self.subTest(source=repr(source)):
                self.syntax_failure(source, read.EXPECTED_TARGET_NAME)

    def test_12_exact_zero_atom_is_not_a_target_name(self):
        result = self.syntax_failure("leg 0", read.EXPECTED_TARGET_NAME)
        self.assertEqual((result.reasons[0].location.start_offset,
                          result.reasons[0].location.end_offset), (4, 5))

    def test_13_extra_material_rejects_the_entire_unit(self):
        for source in ("leg name extra", "leg name 0", "leg name\nWITH"):
            with self.subTest(source=repr(source)):
                self.syntax_failure(source, read.EXPECTED_READ_EOF)

    def test_14_a_second_instruction_is_not_statement_composition(self):
        for gap in (" ", "\n", "\r\n//comment\n"):
            with self.subTest(gap=repr(gap)):
                self.syntax_failure("leg first" + gap + "leg second",
                                    read.EXPECTED_READ_EOF)

    def test_15_target_case_is_retained_without_normalization(self):
        first = self.parsed("leg transcriptA").instruction
        second = self.parsed("leg TranscriptA").instruction
        self.assertEqual(first.target_name, "transcriptA")
        self.assertEqual(second.target_name, "TranscriptA")
        self.assertNotEqual(first.target_name, second.target_name)

    def test_16_head_prefixes_do_not_split_or_become_aliases(self):
        for source in ("legal name", "legname", "leg_ name", "lege name"):
            with self.subTest(source=source):
                self.syntax_failure(source, read.EXPECTED_READ_HEAD)

    def test_17_unresolved_literal_context_preserves_upstream_stop(self):
        for source in ('leg "name"', "leg name;", "leg 123"):
            with self.subTest(source=source):
                upstream = lexical.lex_source(source)
                result = read.parse_read_unit(upstream)
                self.assertEqual(upstream.outcome, lexical.CONTEXT_REQUIRED)
                self.assertEqual(result.outcome, upstream.outcome)
                self.assertEqual(tuple((r.code, r.location) for r in result.reasons),
                                 tuple((r.code, r.location) for r in upstream.reasons))
                self.assertEqual(result.source_profile_outcome,
                                 upstream.source_profile_outcome)
                self.assertIsNone(result.instruction)

    def test_18_source_rejections_preserve_reason_codes_and_locations(self):
        for source in ("\ufeffleg name", "leg name\x00", "leg \u202ename"):
            with self.subTest(source=repr(source)):
                upstream = lexical.lex_source(source)
                result = read.parse_read_unit(upstream)
                self.assertEqual(result.outcome, upstream.outcome)
                self.assertEqual(result.outcome, lexical.SOURCE_REJECTED)
                self.assertEqual(tuple((r.code, r.location) for r in result.reasons),
                                 tuple((r.code, r.location) for r in upstream.reasons))
                self.assertIsNone(result.instruction)

    def test_19_upstream_non_text_and_non_scalar_failures_are_not_syntax_errors(self):
        for source in (None, b"leg name", "\ud800"):
            with self.subTest(source_type=type(source).__name__):
                upstream = lexical.lex_source(source)
                result = read.parse_read_unit(upstream)
                self.assertEqual(result.outcome, upstream.outcome)
                self.assertEqual(tuple(r.code for r in result.reasons),
                                 tuple(r.code for r in upstream.reasons))
                self.assertFalse(result.succeeded)
                self.assertIsNone(result.instruction)

    def test_20_source_and_item_limits_preserve_no_partial_instruction(self):
        for source in ("a" * (profile.MAX_SOURCE_CODE_POINTS + 1),
                       "a " * (lexical.MAX_LEXICAL_ITEMS // 2 + 1)):
            upstream = lexical.lex_source(source)
            self.assertEqual(upstream.outcome, lexical.LIMITED)
            result = read.parse_read_unit(upstream)
            self.assertEqual(result.outcome, upstream.outcome)
            self.assertEqual(tuple(r.code for r in result.reasons),
                             tuple(r.code for r in upstream.reasons))
            self.assertIsNone(result.instruction)

    def test_21_inconsistent_lexical_stream_remains_an_i6_host_failure(self):
        upstream = lexical.lex_source("leg name")
        first = replace(upstream.stream.items[0], approved_spelling=None)
        damaged = replace(upstream, stream=replace(upstream.stream,
                          items=(first,) + upstream.stream.items[1:]))
        result = read.parse_read_unit(damaged)
        self.assertEqual(result.outcome, syntax.HOST_FAILED)
        self.assertEqual(result.reasons[0].code, syntax.LEXICAL_STREAM_INVARIANT_FAILURE)
        self.assertIsNone(result.instruction)

    def test_22_inconsistent_stopped_result_is_not_trusted_as_source_failure(self):
        stopped = lexical.lex_source("leg \"name\"")
        result = read.parse_read_unit(replace(stopped, reasons=()))
        self.assertEqual(result.outcome, syntax.HOST_FAILED)
        self.assertEqual(result.reasons[0].code, syntax.LEXICAL_RESULT_INVARIANT_FAILURE)
        self.assertIsNone(result.instruction)

    def test_23_ranges_count_scalars_and_preserve_crlf_positions(self):
        prefix, middle, suffix = "// \U0001f600\r\n  ", "leg _2", " //end\n"
        source = prefix + middle + suffix
        record = self.parsed(source).instruction
        head = record.head_range.span
        target = record.target_range.span
        self.assertEqual((head.start_offset, head.end_offset),
                         (len(prefix), len(prefix) + 3))
        self.assertEqual((head.start_line, head.start_column,
                          head.end_line, head.end_column), (2, 3, 2, 6))
        self.assertEqual((target.start_offset, target.end_offset),
                         (len(prefix) + 4, len(prefix) + 6))
        self.assertEqual((target.start_line, target.start_column,
                          target.end_line, target.end_column), (2, 7, 2, 9))
        self.assertEqual((record.unit_range.span.start_offset,
                          record.unit_range.span.end_offset), (0, len(source)))
        self.assertEqual((record.unit_range.span.end_line,
                          record.unit_range.span.end_column), (3, 1))

    def test_24_instruction_range_excludes_padding_but_includes_exact_gap(self):
        source = "//before\n \tleg \tname //after\r\n"
        record = self.parsed(source).instruction
        expected = ((record.head_range, "leg"), (record.target_range, "name"),
                    (record.instruction_range, "leg \tname"), (record.unit_range, source))
        for location, exact in expected:
            with self.subTest(exact=repr(exact)):
                self.assertIs(type(location), syntax.SyntaxRange)
                self.assertEqual(source[location.span.start_offset:location.span.end_offset],
                                 exact)
                self.assertEqual(location,
                    record.syntax_input.source_range(location.start_item, location.end_item))
        self.assertEqual(record.unit_range.end_item, len(record.syntax_input.items) - 1)

    def test_25_parser_explicitly_consumes_eof_and_checks_completion(self):
        advanced, completed = [], []
        original_advance = syntax.ParserCursor.advance
        original_finish = syntax.ParserCursor.finish

        def advance(cursor):
            item = original_advance(cursor)
            if item is not None:
                advanced.append(item.kind)
            return item

        def finish(cursor):
            result = original_finish(cursor)
            completed.append(result.complete)
            return result

        with (patch.object(syntax.ParserCursor, "advance", new=advance),
              patch.object(syntax.ParserCursor, "finish", new=finish)):
            self.parsed("//before\nleg name //after\r\n")
        self.assertEqual(advanced.count("EOF"), 1)
        self.assertEqual(advanced[-1], "EOF")
        self.assertEqual(completed, [True])

    def test_26_parser_retains_the_original_checked_source_and_items(self):
        upstream = lexical.lex_source("leg name //source")
        before = tuple((i.kind, i.lexeme, i.span, i.approved_spelling)
                       for i in upstream.stream.items)
        result = read.parse_read_unit(upstream)
        record = result.instruction
        self.assertIs(record.syntax_input, result.preparation.syntax_input)
        self.assertIs(record.syntax_input.items, upstream.stream.items)
        self.assertIs(record.syntax_input.source_map, upstream.stream.source_map)
        self.assertEqual(before, tuple((i.kind, i.lexeme, i.span, i.approved_spelling)
                                       for i in upstream.stream.items))
        for attribute in ("payload", "target_value", "authorization"):
            self.assertFalse(hasattr(record, attribute))

    def test_27_parse_only_never_relexes_admits_or_observes(self):
        upstream = lexical.lex_source("leg transcriptio")
        with (patch.object(lexical, "lex_source", side_effect=AssertionError("no re-lex")),
              patch.object(profile, "inspect_source_profile", side_effect=AssertionError("no scan")),
              patch.object(runtime, "transcriptio", side_effect=AssertionError("no admission")),
              patch.object(runtime, "leg", side_effect=AssertionError("no observation"))):
            result = read.parse_read_unit(upstream)
        self.assertEqual(result.outcome, read.PARSED)

    def test_28_parser_requires_an_exact_i5_result_not_other_carriers(self):
        upstream = lexical.lex_source("leg name")
        view = syntax.prepare_syntax_input(upstream).syntax_input
        for value in ("leg name", b"leg name", upstream.stream, view, (), None,
                      self.admitted("leg name")):
            with self.subTest(value_type=type(value).__name__):
                result = read.parse_read_unit(value)
                self.assertEqual(result.outcome, syntax.INPUT_REJECTED)
                self.assertEqual(result.reasons[0].code, syntax.EXPECTED_LEXICAL_RESULT)
                self.assertIsNone(result.instruction)

    def test_29_parse_representations_and_diagnostics_omit_source(self):
        secret = "SYNTHETIC_I7_SOURCE_NAME_6721"
        success = self.parsed("leg " + secret + " //" + secret)
        failure = self.syntax_failure("leg name " + secret, read.EXPECTED_READ_EOF)
        values = (success, success.instruction, success.preparation, success.reasons,
                  success.instruction.syntax_input, failure, failure.reasons)
        self.assertTrue(all(secret not in repr(value) for value in values))

    def test_30_instruction_and_parse_records_are_read_only(self):
        result = self.parsed("leg name")
        for value, field, replacement in ((result.instruction, "target_name", "other"),
                                           (result, "outcome", "other"),
                                           (result.instruction.target_range, "start_item", 99)):
            with self.subTest(field=field):
                with self.assertRaises((FrozenInstanceError, AttributeError)):
                    setattr(value, field, replacement)

    def test_31_repeated_parsing_has_the_same_exact_observations(self):
        source = "// before\r\nleg \tSignal // after\n"
        observations = []
        for _ in range(3):
            result = self.parsed(source)
            record = result.instruction
            observations.append((result.outcome, result.source_profile_outcome,
                record.target_name, record.head_range, record.target_range,
                record.instruction_range, record.unit_range, result.reasons))
        self.assertEqual(observations[0], observations[1])
        self.assertEqual(observations[1], observations[2])

    def test_32_guarded_parser_memory_failure_stops_without_instruction(self):
        upstream = lexical.lex_source("leg name")
        with patch.object(read, "_parse_prepared", side_effect=MemoryError):
            result = read.parse_read_unit(upstream)
        self.assertEqual(result.outcome, read.HOST_FAILED)
        self.assertEqual(result.reasons[0].code, runtime.RESOURCE_EXHAUSTED)
        self.assertIsNone(result.instruction)
        self.assertFalse(result.succeeded)

    def test_33_parser_unknown_defects_and_cancellation_escape(self):
        upstream = lexical.lex_source("leg name")
        for error in (RuntimeError("synthetic programming defect"), KeyboardInterrupt()):
            with self.subTest(error_type=type(error).__name__):
                with patch.object(read, "_parse_prepared", side_effect=error):
                    with self.assertRaises(type(error)):
                        read.parse_read_unit(upstream)

    def test_34_explicit_adapter_returns_the_original_single_runtime_observation(self):
        value = self.admitted("Open the north valve.")
        original_leg, returned = runtime.leg, []

        def observe(argument):
            observation = original_leg(argument)
            returned.append(observation)
            return observation

        with patch.object(runtime, "leg", side_effect=observe) as called:
            result = read.observe_read_unit("leg transcriptA", target_name="transcriptA",
                                            target_value=value)
        called.assert_called_once_with(value)
        self.assertEqual(result.outcome, runtime.OBSERVED)
        self.assertTrue(result.succeeded)
        self.assertIs(result.observation, returned[0])
        self.assertEqual(result.observation.payload, "Open the north valve.")
        self.assertEqual(result.parse_result.outcome, read.PARSED)
        self.assertEqual(result.reasons, ())

    def test_35_repeated_invocations_are_non_consuming_and_not_cached_dispatch(self):
        value = self.admitted("same payload")
        with patch.object(runtime, "leg", wraps=runtime.leg) as called:
            results = [read.observe_read_unit("leg name", target_name="name", target_value=value)
                       for _ in range(3)]
        self.assertEqual(called.call_count, 3)
        self.assertEqual([result.observation.payload for result in results],
                         ["same payload"] * 3)
        self.assertEqual(runtime.leg(value).payload, "same payload")

    def test_36_empty_observed_payload_is_success(self):
        result = read.observe_read_unit("leg empty", target_name="empty",
                                        target_value=self.admitted(""))
        self.assertEqual(result.outcome, runtime.OBSERVED)
        self.assertTrue(result.succeeded)
        self.assertEqual(result.observation.payload, "")
        self.assertIsNotNone(result.observation.payload)

    def test_37_multilingual_and_supplementary_payload_is_exact(self):
        payload = " AbC \u05e2\u05d1\u05e8\u05d9\u05ea \u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac \U0001f600 \U00010348 "
        result = read.observe_read_unit("leg name", target_name="name",
                                        target_value=self.admitted(payload))
        self.assertEqual(result.observation.payload, payload)
        self.assertEqual(tuple(map(ord, result.observation.payload)), tuple(map(ord, payload)))

    def test_38_source_control_rules_do_not_filter_observed_payload(self):
        payload = "\x00\x1f\ufeff\u202e\u0009\U0010ffff\r\n\r\n \n"
        self.assertNotEqual(lexical.lex_source(payload).outcome, lexical.LEXED)
        result = read.observe_read_unit("leg name", target_name="name",
                                        target_value=self.admitted(payload))
        self.assertEqual(result.outcome, runtime.OBSERVED)
        self.assertEqual(result.observation.payload, payload)

    def test_39_distinct_normalization_forms_remain_distinct_payloads(self):
        payloads = ("\u00e9", "e\u0301")
        results = [read.observe_read_unit("leg name", target_name="name",
                                         target_value=self.admitted(payload))
                   for payload in payloads]
        self.assertEqual(tuple(result.observation.payload for result in results), payloads)
        self.assertNotEqual(results[0].observation.payload, results[1].observation.payload)

    def test_40_adapter_does_not_implicitly_observe_textus_as_source(self):
        source = self.admitted("leg name")
        with patch.object(runtime, "leg", side_effect=AssertionError("no source observation")):
            result = read.observe_read_unit(source, target_name="name", target_value=source)
        self.assertEqual(result.outcome, lexical.INPUT_REJECTED)
        self.assertIsNone(result.observation)

    def test_41_exact_label_mismatch_prevents_all_runtime_calls(self):
        for label in ("Name", "NAME", "other"):
            with self.subTest(label=label):
                with patch.object(runtime, "leg", side_effect=AssertionError("no lookup fallback")):
                    result = read.observe_read_unit("leg name", target_name=label,
                                                    target_value=object())
                self.assertEqual(result.outcome, read.TARGET_REJECTED)
                self.assertEqual(result.reasons[0].code, read.TARGET_NAME_MISMATCH)
                self.assertIsNone(result.observation)
                self.assertEqual(result.parse_result.outcome, read.PARSED)

    def test_42_missing_or_invalid_supplied_labels_diagnose_without_observation(self):
        with patch.object(runtime, "leg", side_effect=AssertionError("no implicit target")):
            omitted = read.observe_read_unit("leg name")
            self.assertEqual(omitted.outcome, read.TARGET_REJECTED)
            self.assertEqual(omitted.reasons[0].code, read.INVALID_TARGET_LABEL)
            for label in (None, "", "9name", "two words", "name\n", "\u00e9", "a-b",
                          "a.b", "0", b"name", 1, [], object()):
                with self.subTest(label_type=type(label).__name__):
                    result = read.observe_read_unit("leg name", target_name=label)
                    self.assertEqual(result.outcome, read.TARGET_REJECTED)
                    self.assertEqual(result.reasons[0].code, read.INVALID_TARGET_LABEL)
                    self.assertIsNone(result.observation)

    def test_43_label_type_checks_do_not_invoke_conversion_or_equality_hooks(self):
        calls = []

        class Hostile:
            def __str__(self):
                calls.append("str")
                return "name"

            def __repr__(self):
                calls.append("repr")
                return "name"

            def __eq__(self, other):
                calls.append("eq")
                return True

        class LabelSubclass(str):
            def __eq__(self, other):
                calls.append("subclass-eq")
                return True

        for label in (Hostile(), LabelSubclass("name")):
            result = read.observe_read_unit("leg name", target_name=label)
            self.assertEqual(result.outcome, read.TARGET_REJECTED)
            self.assertEqual(result.reasons[0].code, read.INVALID_TARGET_LABEL)
        self.assertEqual(calls, [])

    def test_44_matching_label_with_missing_value_uses_existing_i2_failure(self):
        with patch.object(runtime, "leg", wraps=runtime.leg) as called:
            result = read.observe_read_unit("leg name", target_name="name")
        called.assert_called_once_with(None)
        self.assertEqual(result.outcome, runtime.REJECTED)
        self.assertEqual(result.observation.diagnostic.reason, runtime.EXPECTED_TEXTUS)
        self.assertEqual(result.reasons[0].code, runtime.EXPECTED_TEXTUS)
        self.assertIsNone(result.reasons[0].location)
        self.assertIsNone(result.observation.payload)
        self.assertFalse(result.succeeded)

    def test_45_wrong_values_are_not_converted_or_admitted(self):
        calls = []

        class Lookalike:
            _payload = "payload"
            _seal = object()

        class Hostile:
            def __str__(self):
                calls.append("str")
                return "payload"

            def __repr__(self):
                calls.append("repr")
                return "payload"

        for value in ("raw text", b"bytes", object(), Lookalike(), Hostile(), None):
            with self.subTest(value_type=type(value).__name__):
                with (patch.object(runtime, "transcriptio", side_effect=AssertionError("no admission")),
                      patch.object(runtime, "leg", wraps=runtime.leg) as called):
                    result = read.observe_read_unit("leg name", target_name="name",
                                                    target_value=value)
                called.assert_called_once_with(value)
                self.assertEqual(result.outcome, runtime.REJECTED)
                self.assertEqual(result.reasons[0].code, runtime.EXPECTED_TEXTUS)
                self.assertIsNone(result.observation.payload)
        self.assertEqual(calls, [])

    def test_46_i2_invariant_failure_is_retained_without_partial_payload(self):
        forged = runtime.textus(_payload="SYNTHETIC_PRIVATE_PAYLOAD", _seal=object())
        result = read.observe_read_unit("leg name", target_name="name", target_value=forged)
        self.assertEqual(result.outcome, runtime.HOST_FAILED)
        self.assertEqual(result.observation.diagnostic.reason, runtime.TRANSCRIPT_INVARIANT_FAILURE)
        self.assertEqual(result.reasons[0].code, runtime.TRANSCRIPT_INVARIANT_FAILURE)
        self.assertIsNone(result.reasons[0].location)
        self.assertIsNone(result.observation.payload)

    def test_47_i2_resource_failure_preserves_the_original_observation(self):
        value = self.admitted("whole payload")
        with patch.object(runtime, "_make_observation", side_effect=MemoryError):
            failure = runtime.leg(value)
        with patch.object(runtime, "leg", return_value=failure) as called:
            result = read.observe_read_unit("leg name", target_name="name", target_value=value)
        called.assert_called_once_with(value)
        self.assertIs(result.observation, failure)
        self.assertEqual(result.outcome, runtime.HOST_FAILED)
        self.assertEqual(result.reasons[0].code, runtime.RESOURCE_EXHAUSTED)
        self.assertIsNone(result.observation.payload)
        self.assertFalse(result.succeeded)

    def test_48_runtime_unknown_defects_and_cancellation_are_not_language_results(self):
        value = self.admitted("payload")
        for error in (RuntimeError("synthetic defect"), KeyboardInterrupt()):
            with self.subTest(error_type=type(error).__name__):
                with patch.object(runtime, "leg", side_effect=error):
                    with self.assertRaises(type(error)):
                        read.observe_read_unit("leg name", target_name="name", target_value=value)

    def test_49_source_and_grammar_failures_prevent_runtime_calls(self):
        for source in ("", "leg", "leg \nname", "LEG name", "leg 0", 'leg "name"',
                       "\ufeffleg name"):
            with self.subTest(source=repr(source)):
                with patch.object(runtime, "leg", side_effect=AssertionError("no partial observation")):
                    result = read.observe_read_unit(source, target_name="name",
                                                    target_value=object())
                self.assertFalse(result.succeeded)
                self.assertIsNone(result.observation)
                self.assertIsNone(result.parse_result.instruction)

    def test_50_valid_prefix_before_extra_content_never_executes(self):
        value = self.admitted("payload")
        for tail in (" extra", "\nleg second", " //padding\r\nleg name"):
            with self.subTest(tail=repr(tail)):
                with patch.object(runtime, "leg", side_effect=AssertionError("no prefix execution")):
                    result = read.observe_read_unit("leg name" + tail,
                                                    target_name="name", target_value=value)
                self.assertEqual(result.outcome, read.SYNTAX_REJECTED)
                self.assertEqual(result.reasons[0].code, read.EXPECTED_READ_EOF)
                self.assertIsNone(result.observation)

    def test_51_instruction_like_payload_is_never_relexed_or_recursively_dispatched(self):
        payload = "leg second\nWITH RECON BOUNDARY"
        value = self.admitted(payload)
        with (patch.object(lexical, "lex_source", wraps=lexical.lex_source) as lexed,
              patch.object(read, "parse_read_unit", wraps=read.parse_read_unit) as parsed,
              patch.object(runtime, "leg", wraps=runtime.leg) as observed):
            result = read.observe_read_unit("leg name", target_name="name", target_value=value)
        lexed.assert_called_once_with("leg name")
        self.assertEqual(parsed.call_count, 1)
        observed.assert_called_once_with(value)
        self.assertEqual(result.observation.payload, payload)

    def test_52_shell_and_imperative_payloads_remain_complete_in_memory(self):
        for payload in ("Open the north valve.", "$(touch SHOULD_NOT_EXIST)",
                        "<script>alert('synthetic')</script>",
                        "__import__('os').system('SYNTHETIC_NO_EXECUTION')"):
            with self.subTest(payload_kind=payload[:12]):
                result = read.observe_read_unit("leg name", target_name="name",
                                                target_value=self.admitted(payload))
                self.assertEqual(result.outcome, runtime.OBSERVED)
                self.assertEqual(result.observation.payload, payload)

    def test_53_observation_representations_omit_source_and_payload(self):
        name = "SYNTHETIC_I7_PRIVATE_NAME"
        payload = "SYNTHETIC_I7_PRIVATE_PAYLOAD"
        result = read.observe_read_unit("leg " + name + " //PRIVATE_COMMENT",
                                        target_name=name, target_value=self.admitted(payload))
        mismatch = read.observe_read_unit("leg " + name, target_name="different")
        for value in (result, result.parse_result, result.parse_result.instruction,
                      result.observation, mismatch, mismatch.reasons):
            representation = repr(value)
            for secret in (name, payload, "PRIVATE_COMMENT"):
                self.assertNotIn(secret, representation)

    def test_54_adapter_and_parser_have_no_automatic_stdout_or_stderr(self):
        value = self.admitted("SYNTHETIC_NO_PRINT")
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.parsed("leg name //SYNTHETIC_NO_PRINT")
            read.observe_read_unit("leg name", target_name="name", target_value=value)
            read.observe_read_unit("leg name", target_name="other", target_value=value)
            read.observe_read_unit("leg name extra", target_name="name", target_value=value)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_55_contextual_name_observations_do_not_call_named_operations(self):
        value = self.admitted("payload")
        for name in ("leg", "WITH", "OR", "FALSE", "RECON", "DPEND", "IDENTITY",
                     "BOUNDARY", "textus", "transcriptio", "txt"):
            with self.subTest(name=name):
                with (patch.object(runtime, "leg", wraps=runtime.leg) as observed,
                      patch.object(runtime, "transcriptio", side_effect=AssertionError("no admission"))):
                    result = read.observe_read_unit("leg " + name,
                                                    target_name=name, target_value=value)
                observed.assert_called_once_with(value)
                self.assertEqual(result.observation.payload, "payload")

    def test_56_earliest_boundary_precedes_invalid_label_or_wrong_value(self):
        for source, outcome, code in (("LEG name", read.SYNTAX_REJECTED, read.EXPECTED_READ_HEAD),
                                     ('leg "name"', lexical.CONTEXT_REQUIRED,
                                      profile.LEXICAL_CONTEXT_REQUIRED)):
            with self.subTest(source=source):
                with patch.object(runtime, "leg", side_effect=AssertionError("earlier stop")):
                    result = read.observe_read_unit(source, target_name=object(),
                                                    target_value=object())
                self.assertEqual(result.outcome, outcome)
                self.assertEqual(result.reasons[0].code, code)
                self.assertIsNone(result.observation)

    def test_57_module_has_no_ambient_io_interpretation_or_dynamic_dispatch(self):
        path = Path(read.__file__).resolve()
        self.assertEqual(path.name, "core_0_1_read_instruction.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots, calls = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertTrue(roots.isdisjoint({"os", "subprocess", "socket", "pathlib", "urllib",
                                         "requests", "importlib", "builtins"}))
        self.assertTrue(calls.isdisjoint({"eval", "exec", "compile", "open", "print", "input",
            "__import__", "normalize", "casefold", "lower", "upper", "strip", "lstrip", "rstrip",
            "read_text", "read_bytes", "write_text", "write_bytes", "transcriptio", "system",
            "Popen", "connect", "send", "recv"}))

    def test_58_fixed_generated_units_preserve_target_and_reject_extra_words(self):
        names = ("a", "_", "a0", "WITH", "leg", "txt")
        prefixes = ("", " \t", "//before\r\n", "\n//\U0001f600\n")
        gaps = (" ", "\t", " \t ")
        for index in range(36):
            name = names[index % len(names)]
            source = prefixes[index % len(prefixes)] + "leg" + gaps[index % len(gaps)] + name
            with self.subTest(index=index):
                self.assertEqual(self.parsed(source + " //after\n").instruction.target_name, name)
                self.syntax_failure(source + " extra", read.EXPECTED_READ_EOF)

    def test_59_profile_and_new_reason_identities_use_the_published_contract(self):
        self.assertEqual(read.PROFILE_ID, "gart-read-instruction-i7-0.1")
        self.assertEqual(read.PARSED, "parsed")
        self.assertEqual(read.SYNTAX_REJECTED, "syntax-rejected")
        self.assertEqual(read.TARGET_REJECTED, "target-rejected")
        for name in ("EXPECTED_READ_HEAD", "EXPECTED_HORIZONTAL_GAP",
                     "EXPECTED_TARGET_NAME", "EXPECTED_READ_EOF"):
            self.assertEqual(getattr(read, name), "GART.CORE_0_1.SYNTAX." + name)
        for name in ("INVALID_TARGET_LABEL", "TARGET_NAME_MISMATCH"):
            self.assertEqual(getattr(read, name), "GART.CORE_0_1.READ." + name)
        for code in (read.EXPECTED_READ_HEAD, read.EXPECTED_HORIZONTAL_GAP,
                     read.EXPECTED_TARGET_NAME, read.EXPECTED_READ_EOF,
                     read.INVALID_TARGET_LABEL, read.TARGET_NAME_MISMATCH):
            self.assertIsNotNone(re.fullmatch(
                r"GART\.CORE_0_1\.[A-Z][A-Z0-9]*\.[A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)*", code))

    def test_60_adapter_resource_stop_never_selects_or_observes_a_target(self):
        source = "a" * (profile.MAX_SOURCE_CODE_POINTS + 1)
        upstream = lexical.lex_source(source)
        with patch.object(runtime, "leg", side_effect=AssertionError("no limited-prefix read")):
            result = read.observe_read_unit(source, target_name="a", target_value=object())
        self.assertEqual(result.outcome, lexical.LIMITED)
        self.assertEqual(tuple(r.code for r in result.reasons),
                         tuple(r.code for r in upstream.reasons))
        self.assertIsNone(result.observation)
        self.assertIsNone(result.parse_result.instruction)


if __name__ == "__main__":
    unittest.main()
