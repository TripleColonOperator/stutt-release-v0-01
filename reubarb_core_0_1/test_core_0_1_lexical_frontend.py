"""I-5: 42 finite synthetic checks; no new target grammar or semantic oracle."""
from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import core_0_1_lexical_frontend as lexical
import core_0_1_source_profile as profile
import core_0_1_transcript_runtime as transcript


class LexicalFrontendTests(unittest.TestCase):
    def lexed(self, text: str) -> lexical.LexicalStream:
        result = lexical.lex_source(text)
        self.assertEqual(result.outcome, lexical.LEXED)
        self.assertEqual(result.reasons, ())
        self.assertIsNotNone(result.stream)
        return result.stream

    def words(self, text: str) -> tuple[lexical.LexicalItem, ...]:
        return tuple(item for item in self.lexed(text).items if item.kind == "WORD")

    def projected(self, result: lexical.LexicalResult) -> tuple:
        items = () if result.stream is None else tuple(
            (item.kind, item.lexeme, item.span, item.approved_spelling)
            for item in result.stream.items)
        return result.outcome, result.source_profile_outcome, result.reasons, items

    def test_01_empty_input_has_one_zero_width_eof(self):
        stream = self.lexed("")
        self.assertEqual(len(stream.items), 1)
        end = stream.items[0]
        self.assertEqual((end.kind, end.lexeme, end.span.start_offset,
                          end.span.end_offset, end.span.start_line,
                          end.span.start_column), ("EOF", "", 0, 0, 1, 1))

    def test_02_original_eight_spellings_match_exactly(self):
        expected = ("0", "WITH", "OR", "FALSE", "RECON", "DPEND", "IDENTITY", "BOUNDARY")
        stream = self.lexed(" ".join(expected))
        matches = tuple(item.approved_spelling.spelling for item in stream.items
                        if item.approved_spelling is not None)
        self.assertEqual(matches, expected)
        self.assertTrue(all(item.approved_spelling.evidence_group == "original-eight"
                            for item in stream.items if item.approved_spelling is not None))

    def test_03_i2_bindings_match_only_the_three_later_approvals(self):
        words = self.words("textus transcriptio leg")
        self.assertEqual(tuple((item.lexeme, item.approved_spelling.role) for item in words),
                         tuple((binding.spelling, binding.role) for binding in transcript.BINDINGS))
        self.assertTrue(all(item.approved_spelling.decision_ref == "I-2" for item in words))

    def test_04_matched_words_do_not_decide_keyword_reservation(self):
        words = self.words("WITH ordinary textus leg IDENTITY")
        self.assertEqual(tuple(item.kind for item in words), ("WORD",) * 5)
        for item in words:
            self.assertFalse(hasattr(item, "reserved"))
            self.assertFalse(hasattr(item, "callable"))
        self.assertIsNone(words[1].approved_spelling)

    def test_05_ascii_identifier_start_and_continuation(self):
        names = ("_", "_abc", "_1", "A", "z", "Signal", "signal", "a123_Z")
        self.assertEqual(tuple(item.lexeme for item in self.words(" ".join(names))), names)

    def test_06_case_variants_do_not_become_aliases(self):
        names = ("With", "with", "Or", "or", "False", "false", "Textus",
                 "TEXTUS", "TranscripTio", "LEG", "identity", "Boundary")
        words = self.words(" ".join(names))
        self.assertEqual(tuple(item.lexeme for item in words), names)
        self.assertTrue(all(item.approved_spelling is None for item in words))

    def test_07_complete_identifier_run_precedes_exact_match(self):
        names = ("WITHIN", "ORACLE", "FALSEhood", "RECONnect", "DPENDent",
                 "IDENTITY2", "BOUNDARY_name", "textusExtra", "transcriptio2", "legible")
        words = self.words(" ".join(names))
        self.assertEqual(tuple(item.lexeme for item in words), names)
        self.assertTrue(all(item.approved_spelling is None for item in words))

    def test_08_identifier_digits_are_not_separate_zero_atoms(self):
        names = ("a0", "WITH0", "_0", "textus0", "a00", "leg0")
        words = self.words(" ".join(names))
        self.assertEqual(tuple(item.lexeme for item in words), names)
        self.assertTrue(all(item.approved_spelling is None for item in words))

    def test_09_isolated_zero_has_no_number_value(self):
        for text in ("0", " 0 ", "\t0\r\n", "// comment\n0"):
            with self.subTest(case_length=len(text)):
                items = tuple(item for item in self.lexed(text).items
                              if item.kind == "EXACT_ATOM")
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0].lexeme, "0")
                self.assertEqual(items[0].approved_spelling.role, "boundary-local zero")
                self.assertFalse(hasattr(items[0], "value"))

    def test_10_zero_leading_runs_require_a_boundary_decision(self):
        for text in ("00", "0foo", "0_", "01", "0WITH"):
            with self.subTest(case_length=len(text)):
                result = lexical.lex_source(text)
                self.assertEqual(result.outcome, lexical.CONTEXT_REQUIRED)
                self.assertIsNone(result.stream)
                self.assertEqual(result.reasons[0].code, lexical.ZERO_BOUNDARY_REQUIRED)
                self.assertEqual(result.reasons[0].location.end_offset, len(text))

    def test_11_zero_touching_comment_is_not_silently_split(self):
        result = lexical.lex_source("0// payload")
        self.assertEqual(result.outcome, lexical.CONTEXT_REQUIRED)
        self.assertEqual(result.reasons[0].code, lexical.ZERO_BOUNDARY_REQUIRED)
        self.assertIsNone(result.stream)
        self.assertTrue(lexical.lex_source("0 // payload").succeeded)

    def test_12_other_digit_leading_forms_do_not_invent_numbers(self):
        for text in ("1", "123", "2name", "10", "9_thing"):
            with self.subTest(case_length=len(text)):
                result = lexical.lex_source(text)
                self.assertEqual(result.outcome, lexical.CONTEXT_REQUIRED)
                self.assertEqual(result.reasons[0].code, lexical.DIGIT_FORM_REQUIRED)
                self.assertIsNone(result.stream)
        # A profile pass alone is not sufficient for a lexical-subset pass.
        self.assertTrue(profile.inspect_source_profile("123").succeeded)

    def test_13_horizontal_trivia_preserves_exact_space_tab_order(self):
        items = self.lexed(" \t A\t  B ").items
        self.assertEqual(tuple(item.lexeme for item in items if item.kind == "SPACE_TAB"),
                         (" \t ", "\t  ", " "))
        self.assertEqual("".join(item.lexeme for item in items), " \t A\t  B ")

    def test_14_line_break_records_keep_lf_and_crlf_distinct(self):
        items = self.lexed("A\r\nB\nC\r\n").items
        lines = tuple(item for item in items if item.kind in ("LF", "CRLF"))
        self.assertEqual(tuple((item.kind, item.lexeme) for item in lines),
                         (("CRLF", "\r\n"), ("LF", "\n"), ("CRLF", "\r\n")))
        self.assertEqual(items[-1].span.start_line, 4)
        self.assertEqual(items[-1].span.start_column, 1)

    def test_15_comment_payload_is_not_scanned_for_words_or_commands(self):
        text = '// textus WITH 0 LEG " /* + עברית 😀\u200e'
        items = self.lexed(text).items
        self.assertEqual(tuple(item.kind for item in items), ("COMMENT", "EOF"))
        self.assertEqual(items[0].lexeme, text)
        self.assertIsNone(items[0].approved_spelling)

    def test_16_word_adjacent_to_approved_comment_is_preserved(self):
        items = self.lexed("WITH// leg\ntextus").items
        self.assertEqual(tuple((item.kind, item.lexeme) for item in items),
                         (("WORD", "WITH"), ("COMMENT", "// leg"), ("LF", "\n"),
                          ("WORD", "textus"), ("EOF", "")))

    def test_17_every_success_accounts_for_source_once(self):
        text = " \tSignal0// עברית\r\n0 \tleg\n"
        stream = self.lexed(text)
        self.assertEqual("".join(item.lexeme for item in stream.items), text)
        offset = 0
        for item in stream.items[:-1]:
            self.assertEqual(item.span.start_offset, offset)
            self.assertGreater(item.span.end_offset, offset)
            self.assertEqual(item.lexeme, text[offset:item.span.end_offset])
            offset = item.span.end_offset
        self.assertEqual(offset, len(text))
        self.assertEqual(stream.items[-1].span.start_offset, len(text))

    def test_18_positions_count_scalars_not_utf8_or_display_cells(self):
        comment = "// 😀e\u0301"
        stream = self.lexed(comment + "\r\nSignal0")
        comment_item, crlf, word, eof = stream.items
        self.assertEqual(comment_item.span.end_offset, len(comment))
        self.assertEqual(comment_item.span.end_column, len(comment) + 1)
        self.assertEqual(crlf.span.end_offset - crlf.span.start_offset, 2)
        self.assertEqual((word.span.start_line, word.span.start_column), (2, 1))
        self.assertEqual((eof.span.start_line, eof.span.start_column), (2, 8))

    def test_19_eof_never_synthesizes_newline_or_statement(self):
        for text in ("name", "// comment", "name\n"):
            with self.subTest(case_length=len(text)):
                items = self.lexed(text).items
                self.assertEqual(sum(item.kind == "EOF" for item in items), 1)
                self.assertEqual(items[-1].lexeme, "")
                self.assertEqual(items[-1].span.start_offset, len(text))
                self.assertEqual(items[-1].span.end_offset, len(text))
                self.assertEqual("".join(item.lexeme for item in items), text)

    def test_20_profile_rejections_keep_reasons_and_release_no_stream(self):
        for text in ("WITH\x00", "// bad\r", "leg\u202e", "textus\ufeff"):
            with self.subTest(case_length=len(text)):
                expected = profile.inspect_source_profile(text)
                actual = lexical.lex_source(text)
                self.assertEqual(actual.outcome, lexical.SOURCE_REJECTED)
                self.assertEqual(actual.source_profile_outcome, expected.outcome)
                self.assertEqual(tuple((r.code, r.location) for r in actual.reasons),
                                 tuple((r.code, r.location) for r in expected.reasons))
                self.assertIsNone(actual.stream)

    def test_21_unknown_syntax_withholds_even_a_known_prefix(self):
        for text in ('WITH "unknown"', "leg(name)", "x = textus", "x;", "/* anything */"):
            with self.subTest(case_length=len(text)):
                result = lexical.lex_source(text)
                self.assertEqual(result.outcome, lexical.CONTEXT_REQUIRED)
                self.assertEqual(result.source_profile_outcome, profile.CONTEXT_REQUIRED)
                self.assertIsNone(result.stream)
                self.assertEqual(result.reasons[0].code, profile.LEXICAL_CONTEXT_REQUIRED)

    def test_22_non_text_inputs_are_not_decoded_observed_or_coerced(self):
        calls = []
        class Hostile:
            def __str__(self):
                calls.append("str")
                return "WITH"
            def __repr__(self):
                calls.append("repr")
                return "WITH"
        class TextSubclass(str):
            pass
        value = transcript.transcriptio("WITH", reviewed=True, accepted=True).value
        for supplied in (b"WITH", value, Hostile(), TextSubclass("WITH"), None, 0):
            result = lexical.lex_source(supplied)
            self.assertEqual(result.outcome, lexical.INPUT_REJECTED)
            self.assertIsNone(result.stream)
            self.assertEqual(result.reasons[0].code, profile.EXPECTED_DECODED_TEXT)
        self.assertEqual(calls, [])

    def test_23_non_scalars_have_no_invented_scalar_span(self):
        for text in ("\ud800", "\udfff", "\ud800\udc00"):
            result = lexical.lex_source(text)
            self.assertEqual(result.outcome, lexical.INPUT_REJECTED)
            self.assertEqual(result.reasons[0].code, profile.NON_SCALAR_INPUT)
            self.assertIsNone(result.reasons[0].location)
            self.assertIsNone(result.stream)

    def test_24_source_size_ceiling_precedes_scanning(self):
        text = "a" * profile.MAX_SOURCE_CODE_POINTS
        self.assertEqual(self.lexed(text).items[0].lexeme, text)
        result = lexical.lex_source(text + "\ud800")
        self.assertEqual(result.outcome, lexical.LIMITED)
        self.assertEqual(result.reasons[0].code, profile.SOURCE_PROFILE_LIMIT)
        self.assertIsNone(result.stream)

    def test_25_item_ceiling_includes_trivia_but_excludes_eof(self):
        text = "a " * (lexical.MAX_LEXICAL_ITEMS // 2)
        items = self.lexed(text).items
        self.assertEqual(len(items), lexical.MAX_LEXICAL_ITEMS + 1)
        self.assertEqual(items[-1].kind, "EOF")

    def test_26_item_limit_never_releases_partial_success(self):
        text = "a " * (lexical.MAX_LEXICAL_ITEMS // 2) + "b"
        result = lexical.lex_source(text)
        self.assertEqual(result.outcome, lexical.LIMITED)
        self.assertEqual(result.source_profile_outcome, profile.PROFILE_CHECKED)
        self.assertEqual(result.reasons[0].code, lexical.LEXICAL_ITEM_LIMIT)
        self.assertIsNone(result.stream)

    def test_27_default_representations_and_output_omit_source(self):
        secret = "SYNTHETIC_I5_SECRET_7fa021"
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = lexical.lex_source(secret)
            rejected = lexical.lex_source(secret + "\x00")
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", ""))
        for obj in (result, result.stream, result.stream.items, rejected, rejected.reasons):
            self.assertNotIn(secret, repr(obj))
        self.assertEqual(result.stream.items[0].lexeme, secret)

    def test_28_spelling_match_never_calls_runtime_operations(self):
        with (patch.object(transcript, "transcriptio", side_effect=AssertionError("no admission")),
              patch.object(transcript, "leg", side_effect=AssertionError("no observation"))):
            words = self.words("textus transcriptio leg WITH RECON")
        self.assertEqual(len(words), 5)
        self.assertTrue(all(item.approved_spelling is not None for item in words))

    def test_29_source_failure_cannot_mutate_or_reclassify_transcript(self):
        payload = "\ufeff\x00WITH\r"
        admitted = transcript.transcriptio(payload, reviewed=True, accepted=True)
        self.assertEqual(lexical.lex_source(payload).outcome, lexical.SOURCE_REJECTED)
        self.assertEqual(lexical.lex_source(admitted.value).outcome, lexical.INPUT_REJECTED)
        self.assertEqual(transcript.leg(admitted.value).payload, payload)

    def test_30_bhs_heads_and_translations_never_self_promote(self):
        # Source-derived contrast fixtures; not a target keyword catalogue.
        names = ("txt", "aut", "et", "c", "false", "non", "an", "vel",
                 "falsum", "mandatum", "imp", "TEXT", "TRUTH", "Wahrheit")
        words = self.words(" ".join(names))
        self.assertTrue(all(item.approved_spelling is None for item in words))
        self.assertEqual(tuple(item.lexeme for item in words), names)

    def test_31_shared_bhs_heads_do_not_select_a_source_sense(self):
        names = ("acc", "add", "dupl", "hic", "in", "libera", "marg", "orig", "regens")
        words = self.words(" ".join(names))
        self.assertTrue(all(item.approved_spelling is None for item in words))
        self.assertFalse(any(hasattr(item, "resolved_sense") for item in words))

    def test_32_inflections_are_not_operation_aliases(self):
        names = ("legere", "legit", "legunt", "legisse", "transl", "txt")
        self.assertTrue(all(item.approved_spelling is None
                            for item in self.words(" ".join(names))))

    def test_33_bhs_phrase_evidence_does_not_create_phrase_tokens(self):
        for text in ("et cetera", "confisus est", "lapsus calami", "stella crinita"):
            words = self.words(text)
            self.assertEqual(len(words), 2)
            self.assertTrue(all(item.approved_spelling is None for item in words))
            self.assertEqual(" ".join(item.lexeme for item in words), text)

    def test_34_witness_spellings_do_not_inherit_siglum_semantics(self):
        words = self.words("OR Or C Ed Edd K L Ms Mss Occ Q")
        self.assertEqual(words[0].approved_spelling.spelling, "OR")
        self.assertTrue(all(item.approved_spelling is None for item in words[1:]))
        # Identifier-form recognition is not word-to-witness namespace promotion.
        self.assertTrue(all(item.kind == "WORD" for item in words))

    def test_35_signs_and_ellipsis_do_not_become_operators_or_glyphs(self):
        for text in ("+", ">", "*", "...", "aut ... aut", "Atbaš"):
            result = lexical.lex_source(text)
            self.assertEqual(result.outcome, lexical.CONTEXT_REQUIRED)
            self.assertIsNone(result.stream)

    def test_36_repeated_calls_preserve_exact_observations(self):
        for text in ("WITH a0 // e\u0301\nleg", "0WITH", "x\x00", '"//x"'):
            self.assertEqual(self.projected(lexical.lex_source(text)),
                             self.projected(lexical.lex_source(text)))

    def test_37_fixed_generated_sources_are_lossless(self):
        names = ("a", "WITHIN", "textus", "leg", "0", "_0", "txt")
        separators = (" ", "\t", "\n", "\r\n", " // e\u0301😀\n")
        for length in range(33):
            text = "".join(names[(i * 3 + length) % len(names)] +
                           separators[(i + length) % len(separators)]
                           for i in range(length))
            stream = self.lexed(text)
            self.assertEqual("".join(item.lexeme for item in stream.items), text)
            self.assertEqual(stream.items[-1].span.end_offset, len(text))

    def test_38_carriers_are_read_only_host_records(self):
        stream = self.lexed("name")
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            stream.items[0].lexeme = "different"
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            stream.items = ()
        self.assertIs(type(stream.items), tuple)
        self.assertNotIn("evaluate", lexical.__all__)
        self.assertNotIn("execute", lexical.__all__)

    def test_39_profile_and_reason_identities_are_fixed(self):
        self.assertEqual(lexical.PROFILE_ID, "gart-lexical-frontend-i5-0.1")
        self.assertEqual(lexical.MAX_LEXICAL_ITEMS, 16_384)
        expected = (
            (lexical.ZERO_BOUNDARY_REQUIRED, "GART.CORE_0_1.LEXICAL.ZERO_BOUNDARY_REQUIRED"),
            (lexical.DIGIT_FORM_REQUIRED, "GART.CORE_0_1.LEXICAL.DIGIT_FORM_REQUIRED"),
            (lexical.LEXICAL_ITEM_LIMIT, "GART.CORE_0_1.RESOURCE.LEXICAL_ITEM_LIMIT"),
        )
        for actual, code in expected:
            self.assertEqual(actual, code)
            self.assertIsNotNone(re.fullmatch(
                r"GART\.CORE_0_1\.[A-Z][A-Z0-9]*\.[A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)*", actual))
        self.assertEqual(lexical.RESOURCE_EXHAUSTED, transcript.RESOURCE_EXHAUSTED)

    def test_40_guarded_memory_failure_and_unknown_defects_stay_distinct(self):
        with patch.object(lexical, "_make_stream", side_effect=MemoryError):
            result = lexical.lex_source("WITH")
        self.assertEqual(result.outcome, lexical.HOST_FAILED)
        self.assertEqual(result.reasons[0].code, lexical.RESOURCE_EXHAUSTED)
        self.assertIsNone(result.stream)
        for failure in (RuntimeError("synthetic defect"), KeyboardInterrupt()):
            with patch.object(lexical, "_scan", side_effect=failure):
                with self.assertRaises(type(failure)):
                    lexical.lex_source("WITH")

    def test_41_source_inspection_finds_no_unapproved_operational_path(self):
        path = Path(lexical.__file__).resolve()
        self.assertEqual(path.name, "core_0_1_lexical_frontend.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports, calls = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertEqual(imports, {"__future__", "dataclasses", "typing", "core_0_1_source_profile"})
        forbidden = {"eval", "exec", "compile", "open", "print", "input", "getattr",
                     "__import__", "globals", "locals", "normalize", "casefold", "strip",
                     "split", "isidentifier", "isalpha", "isdigit", "transcriptio", "leg",
                     "write_text", "write_bytes", "system", "Popen", "run", "send"}
        self.assertTrue(calls.isdisjoint(forbidden))

    def test_42_metadata_is_fixed_evidence_not_a_dispatch_registry(self):
        expected = ("0", "WITH", "OR", "FALSE", "RECON", "DPEND", "IDENTITY",
                    "BOUNDARY", "textus", "transcriptio", "leg")
        self.assertIs(type(lexical.APPROVED_SPELLINGS), tuple)
        self.assertEqual(tuple(record.spelling for record in lexical.APPROVED_SPELLINGS), expected)
        self.assertEqual(len(set(expected)), 11)
        for record in lexical.APPROVED_SPELLINGS:
            self.assertFalse(callable(record))
            self.assertIs(type(record.role), str)
            self.assertIs(type(record.decision_ref), str)
            with self.assertRaises((FrozenInstanceError, AttributeError)):
                record.spelling = "replacement"


if __name__ == "__main__":
    unittest.main()
