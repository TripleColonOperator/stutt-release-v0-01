"""I-6: finite synthetic checks for parser support, not a language grammar."""
from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError, replace
from io import StringIO
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import core_0_1_lexical_frontend as lex
import core_0_1_source_profile as profile
import core_0_1_syntax_skeleton as syntax
import core_0_1_transcript_runtime as transcript


class SyntaxSkeletonTests(unittest.TestCase):
    def prepared(self, text):
        result = syntax.prepare_syntax_input(lex.lex_source(text))
        self.assertEqual(result.outcome, syntax.PREPARED)
        self.assertEqual(result.reasons, ())
        self.assertIsNotNone(result.syntax_input)
        return result.syntax_input

    def failed(self, result, code=syntax.LEXICAL_STREAM_INVARIANT_FAILURE):
        checked = syntax.prepare_syntax_input(result)
        self.assertIsNone(checked.syntax_input)
        self.assertEqual(tuple(r.code for r in checked.reasons), (code,))
        return checked

    def with_items(self, result, items):
        return replace(result, stream=replace(result.stream, items=items))

    def test_01_empty_input_is_prepared_but_never_an_empty_program(self):
        view = self.prepared("")
        self.assertEqual(len(view.items), 1)
        self.assertEqual(view.items[0].kind, "EOF")
        self.assertEqual(syntax.ParserCursor(view).finish().outcome, syntax.INCOMPLETE)
        for name in ("parse", "evaluate", "execute", "valid_program", "ast"):
            self.assertFalse(hasattr(syntax, name))
            self.assertFalse(hasattr(view, name))

    def test_02_all_approved_metadata_is_preserved_not_dispatched(self):
        words = " ".join(record.spelling for record in lex.APPROVED_SPELLINGS)
        view = self.prepared(words)
        matched = tuple(i.approved_spelling for i in view.items if i.approved_spelling)
        self.assertEqual(matched, lex.APPROVED_SPELLINGS)
        self.assertTrue(all(i.kind == "WORD" for i in view.items
                            if i.approved_spelling and i.lexeme != "0"))

    def test_03_raw_inputs_lookalikes_and_subclasses_are_not_coerced(self):
        calls = []
        class Hostile:
            def __str__(self):
                calls.append("str")
                raise AssertionError("conversion forbidden")
            def __repr__(self):
                calls.append("repr")
                raise AssertionError("representation forbidden")
        class ResultSubclass(lex.LexicalResult):
            pass
        admitted = transcript.transcriptio("leg", reviewed=True, accepted=True).value
        for value in ("leg", b"leg", (), [], None, Hostile(), admitted,
                      lex.lex_source("x").stream,
                      ResultSubclass("lexed", None, (), "profile-checked")):
            checked = syntax.prepare_syntax_input(value)
            self.assertEqual(checked.outcome, syntax.INPUT_REJECTED)
            self.assertEqual(checked.reasons[0].code, syntax.EXPECTED_LEXICAL_RESULT)
            self.assertIsNone(checked.syntax_input)
        self.assertEqual(calls, [])

    def test_04_source_rejection_preserves_upstream_reasons_and_locations(self):
        upstream = lex.lex_source("a\x00\n\u202e")
        result = syntax.prepare_syntax_input(upstream)
        self.assertEqual(result.outcome, syntax.UPSTREAM_STOPPED)
        self.assertEqual(result.upstream_outcome, lex.SOURCE_REJECTED)
        self.assertEqual(tuple((r.code, r.location) for r in result.reasons),
                         tuple((r.code, r.location) for r in upstream.reasons))
        self.assertIsNone(result.syntax_input)

    def test_05_unknown_grammar_and_zero_forms_do_not_supply_input(self):
        for text in ('leg "words"', "WITH 0foo", "0//comment", "00", "2name", "WITH + OR"):
            upstream = lex.lex_source(text)
            result = syntax.prepare_syntax_input(upstream)
            self.assertEqual(result.outcome, syntax.UPSTREAM_STOPPED)
            self.assertEqual(result.upstream_outcome, lex.CONTEXT_REQUIRED)
            self.assertEqual(result.reasons[0].code, upstream.reasons[0].code)
            self.assertIsNone(result.syntax_input)

    def test_06_upstream_resource_limits_are_not_success_or_relabelled(self):
        for text in ("a" * (profile.MAX_SOURCE_CODE_POINTS + 1), "a " * 8193):
            upstream = lex.lex_source(text)
            result = syntax.prepare_syntax_input(upstream)
            self.assertEqual(result.outcome, syntax.UPSTREAM_STOPPED)
            self.assertEqual(result.upstream_outcome, lex.LIMITED)
            self.assertEqual(result.reasons[0].code, upstream.reasons[0].code)

    def test_07_upstream_input_rejections_keep_no_invented_scalar_span(self):
        for text in (b"x", "\ud800"):
            upstream = lex.lex_source(text)
            result = syntax.prepare_syntax_input(upstream)
            self.assertEqual(result.upstream_outcome, lex.INPUT_REJECTED)
            self.assertEqual(result.reasons[0].code, upstream.reasons[0].code)
            self.assertIsNone(result.reasons[0].location)
            self.assertIsNone(result.syntax_input)

    def test_08_upstream_host_failure_is_retained_without_retry(self):
        upstream = lex.LexicalResult(lex.HOST_FAILED, None,
            (lex.LexicalReason(lex.RESOURCE_EXHAUSTED),), None)
        result = syntax.prepare_syntax_input(upstream)
        self.assertEqual(result.outcome, syntax.UPSTREAM_STOPPED)
        self.assertEqual(result.upstream_outcome, lex.HOST_FAILED)
        self.assertEqual(result.reasons[0].code, lex.RESOURCE_EXHAUSTED)

    def test_09_malformed_outcomes_and_reasons_are_host_record_failures(self):
        base = lex.lex_source("x")
        mutations = (
            replace(base, outcome="SYNTHETIC_SECRET"),
            replace(base, outcome=object()),
            replace(base, reasons=[]),
            replace(base, source_profile_outcome="unknown"),
            replace(base, outcome=lex.SOURCE_REJECTED, stream=None),
            replace(base, outcome=lex.SOURCE_REJECTED, stream=None,
                    reasons=(lex.LexicalReason("SYNTHETIC_SECRET"),)),
            replace(base, outcome=lex.SOURCE_REJECTED, stream=None,
                    reasons=(lex.LexicalReason(profile.FORBIDDEN_CONTROL, object()),)),
            replace(base, outcome=lex.SOURCE_REJECTED, stream=None,
                    reasons=(object(),)),
        )
        for value in mutations:
            result = self.failed(value, syntax.LEXICAL_RESULT_INVARIANT_FAILURE)
            self.assertEqual(result.outcome, syntax.HOST_FAILED)
            self.assertNotIn("SYNTHETIC_SECRET", repr(result))

    def test_10_success_envelope_cannot_hold_failure_or_missing_stream(self):
        base = lex.lex_source("x")
        for value in (replace(base, stream=None), replace(base, source_profile_outcome=None),
                      replace(base, reasons=(lex.LexicalReason(lex.RESOURCE_EXHAUSTED),)),
                      replace(base, outcome=lex.CONTEXT_REQUIRED,
                              reasons=(lex.LexicalReason(lex.ZERO_BOUNDARY_REQUIRED),))):
            self.failed(value, syntax.LEXICAL_RESULT_INVARIANT_FAILURE)

    def test_11_unknown_profile_and_non_tuple_items_are_rejected(self):
        base = lex.lex_source("x")
        damaged = replace(base.stream)
        object.__setattr__(damaged, "profile_id", "different-host-profile")
        self.failed(replace(base, stream=damaged))
        self.failed(self.with_items(base, list(base.stream.items)))
        self.failed(self.with_items(base, ()))

    def test_12_missing_duplicated_or_early_eof_is_rejected(self):
        base = lex.lex_source("a b")
        items = base.stream.items
        for changed in (items[:-1], items + (items[-1],), (items[-1],) + items,
                        items[:1] + (items[-1],) + items[1:]):
            self.failed(self.with_items(base, changed))

    def test_13_eof_has_exact_empty_lexeme_span_and_no_metadata(self):
        base = lex.lex_source("a")
        eof = base.stream.items[-1]
        for changed in (replace(eof, lexeme="x"),
                        replace(eof, span=replace(eof.span, start_offset=0)),
                        replace(eof, span=replace(eof.span, end_column=99)),
                        replace(eof, approved_spelling=lex.APPROVED_SPELLINGS[0])):
            self.failed(self.with_items(base, base.stream.items[:-1] + (changed,)))

    def test_14_gaps_overlaps_zero_width_and_reversed_spans_are_rejected(self):
        base = lex.lex_source("abc def")
        first, gap, second, eof = base.stream.items
        for damaged in (replace(first, span=replace(first.span, start_offset=1)),
                        replace(first, span=replace(first.span, end_offset=0)),
                        replace(first, span=replace(first.span, end_offset=999)),
                        replace(first, span=replace(first.span, start_offset=4, end_offset=3))):
            self.failed(self.with_items(base, (damaged, gap, second, eof)))
        self.failed(self.with_items(base, (second, gap, first, eof)))

    def test_15_lexeme_source_mismatch_is_not_repaired(self):
        base = lex.lex_source("Signal")
        changed = replace(base.stream.items[0], lexeme="signal")
        self.failed(self.with_items(base, (changed, base.stream.items[-1])))
        self.assertEqual(base.stream.source_map.source_text, "Signal")

    def test_16_coordinates_cannot_be_bytes_bools_or_false_line_columns(self):
        base = lex.lex_source("// 😀\nWITH")
        first = base.stream.items[0]
        for span in (replace(first.span, end_offset=8),
                     replace(first.span, start_offset=False),
                     replace(first.span, start_line=0),
                     replace(first.span, end_column=99)):
            self.failed(self.with_items(base, (replace(first, span=span),) + base.stream.items[1:]))
        damaged = replace(first.span)
        object.__setattr__(damaged, "unit", "BYTE")
        self.failed(self.with_items(base, (replace(first, span=damaged),) + base.stream.items[1:]))

    def test_17_line_map_must_match_exact_source_line_breaks(self):
        base = lex.lex_source("a\r\nb\nc")
        for starts in ((), (1,), (0, 2, 5), (0, 3, 3, 5), (False, 3, 5), [0, 3, 5]):
            mapping = replace(base.stream.source_map, line_starts=starts)
            self.failed(replace(base, stream=replace(base.stream, source_map=mapping)))

    def test_18_bad_source_map_fields_and_non_scalars_do_not_get_views(self):
        base = lex.lex_source("x")
        for mapping in (object(), replace(base.stream.source_map, source_text=b"x"),
                        replace(base.stream.source_map, source_text="\ud800"),
                        replace(base.stream.source_map, source_text="\r"),
                        replace(base.stream.source_map, comments=[]),
                        replace(base.stream.source_map, comments=(object(),)),
                        replace(base.stream.source_map, line_breaks=(object(),))):
            self.failed(replace(base, stream=replace(base.stream, source_map=mapping)))

    def test_19_trivia_and_line_tables_must_agree_with_lexical_items(self):
        base = lex.lex_source("a //note\r\nb")
        mapping = base.stream.source_map
        for altered in (replace(mapping, comments=()),
                        replace(mapping, horizontal_whitespace=()),
                        replace(mapping, line_breaks=())):
            self.failed(replace(base, stream=replace(base.stream, source_map=altered)))
        for index, item in enumerate(base.stream.items):
            if item.kind in ("COMMENT", "CRLF", "SPACE_TAB"):
                changed = base.stream.items[:index] + (replace(item, kind="WORD"),) + base.stream.items[index + 1:]
                self.failed(self.with_items(base, changed))

    def test_20_unknown_or_subclassed_items_are_not_new_syntax(self):
        base = lex.lex_source("a")
        class ItemSubclass(lex.LexicalItem):
            pass
        item = base.stream.items[0]
        for changed in (replace(item, kind="CALL"), replace(item, kind=object()),
                        ItemSubclass(item.kind, item.lexeme, item.span), object()):
            self.failed(self.with_items(base, (changed, base.stream.items[-1])))

    def test_21_metadata_cannot_change_spelling_roles_or_aliases(self):
        base = lex.lex_source("WITH txt")
        first = base.stream.items[0]
        for changed in (replace(first, approved_spelling=None),
                        replace(first, approved_spelling=lex.APPROVED_SPELLINGS[0]),
                        replace(first, approved_spelling=replace(first.approved_spelling, role="execute")),
                        replace(first, approved_spelling=object())):
            self.failed(self.with_items(base, (changed,) + base.stream.items[1:]))
        txt = base.stream.items[2]
        self.failed(self.with_items(base, base.stream.items[:2] + (
            replace(txt, approved_spelling=lex.APPROVED_SPELLINGS[8]), base.stream.items[-1])))

    def test_22_split_identifier_runs_and_non_ascii_words_are_not_accepted(self):
        base = lex.lex_source("WITHIN")
        mapping = base.stream.source_map
        left = lex.LexicalItem("WORD", "WITH", profile.ScalarSpan(0, 4, 1, 1, 1, 5), lex.APPROVED_SPELLINGS[1])
        right = lex.LexicalItem("WORD", "IN", profile.ScalarSpan(4, 6, 1, 5, 1, 7))
        self.failed(self.with_items(base, (left, right, base.stream.items[-1])))
        small = lex.lex_source("a")
        altered_map = replace(small.stream.source_map, source_text="é")
        altered_item = replace(small.stream.items[0], lexeme="é")
        self.failed(replace(small, stream=replace(small.stream, source_map=altered_map,
            items=(altered_item, small.stream.items[-1]))))

    def test_23_zero_and_case_variants_remain_unchanged_neutral_records(self):
        view = self.prepared("0\nWITH With with a0 txt textus")
        records = tuple((i.kind, i.lexeme) for i in view.items)
        self.assertEqual(records[0], ("EXACT_ATOM", "0"))
        self.assertIn(("WORD", "With"), records)
        self.assertIn(("WORD", "with"), records)
        self.assertIn(("WORD", "a0"), records)
        self.assertFalse(hasattr(view.items[0], "numeric_value"))

    def test_24_limits_are_bounded_before_inspecting_oversized_item_tuples(self):
        view = self.prepared("a " * 8192)
        self.assertEqual(len(view.items), syntax.MAX_INPUT_ITEMS + 1)
        base = lex.lex_source("x")
        huge = self.with_items(base, (object(),) * (syntax.MAX_INPUT_ITEMS + 2))
        self.assertEqual(self.failed(huge, syntax.SYNTAX_INPUT_LIMIT).outcome, syntax.LIMITED)
        mapping = replace(base.stream.source_map, source_text="a" * (profile.MAX_SOURCE_CODE_POINTS + 1))
        self.failed(replace(base, stream=replace(base.stream, source_map=mapping)))

    def test_25_preparation_keeps_original_source_items_and_metadata(self):
        upstream = lex.lex_source("Signal // e\u0301 😀\r\nleg")
        view = syntax.prepare_syntax_input(upstream).syntax_input
        self.assertIs(view.items, upstream.stream.items)  # Host sharing, not target identity.
        self.assertIs(view.source_map, upstream.stream.source_map)
        self.assertEqual("".join(i.lexeme for i in view.items), view.source_map.source_text)

    def test_26_peek_is_non_consuming_and_lookahead_is_explicit(self):
        view = self.prepared("a b")
        cursor = syntax.ParserCursor(view)
        self.assertIs(cursor.peek(), view.items[0])
        self.assertIs(cursor.peek(2), view.items[2])
        self.assertIsNone(cursor.peek(10**50))
        self.assertEqual(cursor.position, 0)

    def test_27_advance_visits_every_item_and_eof_exactly_once(self):
        view = self.prepared("WITH //note\r\n0")
        cursor = syntax.ParserCursor(view)
        observed = tuple(cursor.advance() for _ in range(len(view.items)))
        self.assertEqual(observed, view.items)
        self.assertEqual(sum(i.kind == "EOF" for i in observed), 1)
        self.assertEqual(cursor.position, len(view.items))

    def test_28_exhaustion_does_not_create_phantom_items_or_new_eof(self):
        cursor = syntax.ParserCursor(self.prepared(""))
        self.assertEqual(cursor.advance().kind, "EOF")
        for _ in range(5):
            self.assertIsNone(cursor.peek())
            self.assertIsNone(cursor.advance())
            self.assertEqual(cursor.skip_trivia(), 0)
            self.assertEqual(cursor.position, 1)
        self.assertTrue(cursor.exhausted)

    def test_29_independent_cursors_do_not_consume_each_other(self):
        view = self.prepared("a b")
        first, second = syntax.ParserCursor(view), syntax.ParserCursor(view)
        first.advance()
        self.assertEqual((first.position, second.position), (1, 0))
        self.assertEqual(second.peek().lexeme, "a")
        self.assertEqual(view.source_map.source_text, "a b")

    def test_30_explicit_trivia_skip_never_discards_line_breaks(self):
        view = self.prepared(" \t//comment\r\n\nleg")
        cursor = syntax.ParserCursor(view)
        self.assertEqual(cursor.skip_trivia(), 2)
        self.assertEqual(cursor.peek().kind, "CRLF")
        self.assertEqual(cursor.skip_trivia(), 0)
        cursor.advance()
        self.assertEqual(cursor.peek().kind, "LF")
        cursor.advance()
        self.assertEqual(cursor.peek().lexeme, "leg")
        self.assertEqual(len(view.source_map.comments), 1)

    def test_31_trailing_trivia_and_newlines_need_explicit_traversal(self):
        cursor = syntax.ParserCursor(self.prepared("a //end\n"))
        cursor.advance()
        self.assertFalse(cursor.finish().complete)
        cursor.skip_trivia()
        self.assertEqual(cursor.peek().kind, "LF")
        self.assertFalse(cursor.finish().complete)
        cursor.advance()
        self.assertEqual(cursor.peek().kind, "EOF")
        self.assertFalse(cursor.finish().complete)
        cursor.advance()
        self.assertTrue(cursor.finish().complete)

    def test_32_incomplete_finish_reports_first_remaining_span_without_moving(self):
        view = self.prepared("SYNTHETIC_SECRET next")
        cursor = syntax.ParserCursor(view)
        result = cursor.finish()
        self.assertEqual(result.outcome, syntax.INCOMPLETE)
        self.assertEqual(result.reasons[0].code, syntax.UNCONSUMED_ITEMS)
        self.assertEqual(result.reasons[0].location, view.items[0].span)
        self.assertEqual(cursor.position, 0)
        self.assertNotIn("SYNTHETIC_SECRET", repr(result))

    def test_33_seeing_eof_does_not_count_as_consuming_it(self):
        cursor = syntax.ParserCursor(self.prepared(""))
        self.assertEqual(cursor.peek().kind, "EOF")
        result = cursor.finish()
        self.assertEqual(result.reasons[0].code, syntax.EOF_NOT_CONSUMED)
        self.assertFalse(result.complete)
        self.assertFalse(cursor.exhausted)

    def test_34_full_consumption_is_not_a_parse_result_or_authorization(self):
        view = self.prepared("WITH OR FALSE RECON DPEND IDENTITY BOUNDARY textus transcriptio leg")
        cursor = syntax.ParserCursor(view)
        for _ in view.items:
            cursor.advance()
        result = cursor.finish()
        self.assertEqual(result.outcome, syntax.FULLY_CONSUMED)
        self.assertTrue(result.complete)
        self.assertEqual(result.reasons, ())
        for name in ("ast", "value", "parsed", "valid_program", "authorization", "executable"):
            self.assertFalse(hasattr(result, name))

    def test_35_ranges_preserve_trivia_lines_and_supplementary_scalar_positions(self):
        view = self.prepared("a //😀\r\nleg")
        full = view.source_range(0, len(view.items) - 1)
        self.assertEqual((full.span.start_offset, full.span.end_offset), (0, 10))
        self.assertEqual((full.span.end_line, full.span.end_column), (2, 4))
        comment = view.source_range(2, 3)
        self.assertEqual((comment.span.start_offset, comment.span.end_offset), (2, 5))
        self.assertEqual(view.source_map.source_text[2:5], "//😀")

    def test_36_empty_ranges_are_positions_not_empty_productions(self):
        view = self.prepared("a\r\nb")
        start = view.source_range(0, 0)
        after_break = view.source_range(2, 2)
        end = view.source_range(len(view.items) - 1, len(view.items) - 1)
        self.assertEqual((start.span.start_offset, start.span.end_offset), (0, 0))
        self.assertEqual((after_break.span.start_offset, after_break.span.start_line,
                          after_break.span.start_column), (3, 2, 1))
        self.assertEqual((end.span.start_offset, end.span.end_offset), (4, 4))
        self.assertFalse(hasattr(start, "production"))

    def test_37_cursor_and_range_api_misuse_is_explicit_and_source_free(self):
        view = self.prepared("a")
        cursor = syntax.ParserCursor(view)
        for ahead in (True, "1", 1.0, None):
            with self.assertRaises(TypeError):
                cursor.peek(ahead)
        with self.assertRaises(ValueError):
            cursor.peek(-1)
        for pair in ((True, 1), (0, False), ("0", 1)):
            with self.assertRaises(TypeError):
                view.source_range(*pair)
        for pair in ((-1, 0), (1, 0), (0, 2), (3, 3)):
            with self.assertRaises(ValueError):
                view.source_range(*pair)
        for value in ("a", lex.lex_source("a"), None, replace(view, _seal=object())):
            with self.assertRaises(TypeError):
                syntax.ParserCursor(value)
        self.assertEqual(cursor.position, 0)

    def test_38_prepared_records_and_ranges_are_read_only(self):
        view = self.prepared("a")
        span = view.source_range(0, 1)
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            view.items = ()
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            span.start_item = 9
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            del view.source_map

    def test_39_repeated_preparation_and_cursor_scripts_are_deterministic(self):
        def observe():
            cursor = syntax.ParserCursor(self.prepared("WITH\n//note\r\nleg"))
            visited = []
            while not cursor.exhausted:
                item = cursor.advance()
                visited.append((item.kind, item.lexeme, item.span))
            return visited, cursor.finish()
        first, second = observe(), observe()
        self.assertEqual(first, second)

    def test_40_ordinary_output_and_representations_omit_source(self):
        secret = "SYNTHETIC_I6_SECRET"
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = syntax.prepare_syntax_input(lex.lex_source(secret))
            view = result.syntax_input
            cursor = syntax.ParserCursor(view)
            location = view.source_range(0, 1)
            representations = tuple(repr(value) for value in
                (result, view, cursor, cursor.peek(), location, cursor.finish()))
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")
        self.assertTrue(all(secret not in value for value in representations))

    def test_41_preparation_and_traversal_never_lex_again_or_call_runtime(self):
        upstream = lex.lex_source("transcriptio textus leg RECON")
        with (patch.object(lex, "lex_source", side_effect=AssertionError("no re-lex")),
              patch.object(profile, "inspect_source_profile", side_effect=AssertionError("no re-scan")),
              patch.object(transcript, "transcriptio", side_effect=AssertionError("no admission")),
              patch.object(transcript, "leg", side_effect=AssertionError("no observation"))):
            view = syntax.prepare_syntax_input(upstream).syntax_input
            cursor = syntax.ParserCursor(view)
            for _ in view.items:
                cursor.advance()
            self.assertTrue(cursor.finish().complete)

    def test_42_module_has_no_grammar_dispatch_io_or_unapproved_dependency(self):
        path = Path(syntax.__file__).resolve()
        self.assertEqual(path.name, "core_0_1_syntax_skeleton.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots, calls = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertEqual(roots, {"__future__", "dataclasses", "typing",
                               "core_0_1_lexical_frontend", "core_0_1_source_profile"})
        self.assertTrue(calls.isdisjoint({"eval", "exec", "compile", "open", "print", "input",
            "__import__", "lex_source", "inspect_source_profile", "transcriptio", "leg",
            "parse", "evaluate", "execute", "normalize", "write_text", "write_bytes"}))
        self.assertEqual(syntax.PROFILE_ID, "gart-syntax-skeleton-i6-0.1")
        self.assertEqual(syntax.MAX_INPUT_ITEMS, lex.MAX_LEXICAL_ITEMS)
        for code in (syntax.EXPECTED_LEXICAL_RESULT, syntax.LEXICAL_RESULT_INVARIANT_FAILURE,
                     syntax.LEXICAL_STREAM_INVARIANT_FAILURE, syntax.SYNTAX_INPUT_LIMIT,
                     syntax.UNCONSUMED_ITEMS, syntax.EOF_NOT_CONSUMED):
            self.assertIsNotNone(re.fullmatch(
                r"GART\.CORE_0_1\.[A-Z][A-Z0-9]*\.[A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)*", code))

    def test_43_guarded_allocation_failures_stop_and_unknown_defects_escape(self):
        upstream = lex.lex_source("leg")
        with patch.object(syntax, "_make_input", side_effect=MemoryError):
            result = syntax.prepare_syntax_input(upstream)
            self.assertEqual(result.outcome, syntax.HOST_FAILED)
            self.assertEqual(result.reasons[0].code, syntax.RESOURCE_EXHAUSTED)
            self.assertIsNone(result.syntax_input)
        for error in (RuntimeError("synthetic defect"), KeyboardInterrupt()):
            with patch.object(syntax, "_stream_valid", side_effect=error):
                with self.assertRaises(type(error)):
                    syntax.prepare_syntax_input(upstream)

    def test_44_fixed_generated_streams_preserve_all_items_ranges_and_boundaries(self):
        atoms = ("WITH", "With", "WITHIN", "txt", "textus", "a00", "_x", "0")
        separators = (" ", "\t", "\n", "\r\n", " // e\u0301 😀\n")
        for count in range(25):
            text = "".join(atoms[(i + count) % len(atoms)] + separators[i % len(separators)]
                           for i in range(count))
            view = self.prepared(text)
            cursor = syntax.ParserCursor(view)
            pieces = []
            for index, item in enumerate(view.items):
                self.assertIs(cursor.advance(), item)
                if item.kind != "EOF":
                    span = view.source_range(index, index + 1).span
                    pieces.append(text[span.start_offset:span.end_offset])
            self.assertEqual("".join(pieces), text)
            self.assertTrue(cursor.finish().complete)
            self.assertIsNone(cursor.advance())


if __name__ == "__main__":
    unittest.main()
