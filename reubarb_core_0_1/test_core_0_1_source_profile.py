"""I-4 finite synthetic source-profile checks; no Reubarb programs execute."""
from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import core_0_1_source_profile as profile
import core_0_1_transcript_runtime as transcript
import core_0_1_transport_kernel as transport


class SourceProfileTests(unittest.TestCase):
    def checked(self, source: str) -> profile.SourceMap:
        result = profile.inspect_source_profile(source)
        self.assertEqual(result.outcome, profile.PROFILE_CHECKED)
        self.assertTrue(result.checks_complete)
        self.assertEqual(result.reasons, ())
        self.assertIsNotNone(result.source_map)
        return result.source_map

    def codes(self, source: str) -> tuple[str, ...]:
        return tuple(reason.code for reason in profile.inspect_source_profile(source).reasons)

    def test_01_empty_profile_and_zero_width_end_position(self) -> None:
        source_map = self.checked("")
        self.assertEqual(source_map.scalar_length, 0)
        self.assertEqual(source_map.end_of_input, profile.SourcePosition(0, 1, 1))
        self.assertEqual(source_map.comments, ())
        self.assertEqual(source_map.line_breaks, ())

    def test_02_ascii_content_is_not_tokenized_or_given_numeric_meaning(self) -> None:
        for source in ("Signal signal SIGNAL", "00", "0WITH", "2signal", "WITHIN",
                       "textus transcriptio leg", "FALSE WITH RECON"):
            with self.subTest(case=source):
                self.assertEqual(self.checked(source).source_text, source)
        # Profile success never classifies tokens, valid identifiers, or programs.
        self.assertFalse(hasattr(self.checked("0WITH"), "tokens"))

    def test_03_unicode_comment_is_exact_including_supplementary_characters(self) -> None:
        source = "Signal // עברית العربية Ελληνικά 😀 e\u0301"
        source_map = self.checked(source)
        self.assertEqual(source_map.source_text, source)
        comment = source_map.comments[0]
        self.assertEqual(source[comment.start_offset:comment.end_offset], source[7:])
        self.assertEqual(source_map.scalar_length, len(source))

    def test_04_lf_line_map_and_final_line_are_exact(self) -> None:
        source_map = self.checked("A\nBC\n")
        self.assertEqual(source_map.line_starts, (0, 2, 5))
        self.assertEqual(source_map.position(2), profile.SourcePosition(2, 2, 1))
        self.assertEqual(source_map.end_of_input, profile.SourcePosition(5, 3, 1))
        self.assertEqual(tuple(item.kind for item in source_map.line_breaks), ("LF", "LF"))

    def test_05_crlf_is_one_break_but_two_scalar_offsets(self) -> None:
        source_map = self.checked("A\r\nB")
        self.assertEqual(source_map.line_starts, (0, 3))
        self.assertEqual(source_map.position(1), profile.SourcePosition(1, 1, 2))
        self.assertEqual(source_map.position(2), profile.SourcePosition(2, 1, 3))
        self.assertEqual(source_map.position(3), profile.SourcePosition(3, 2, 1))
        self.assertEqual(source_map.line_breaks[0], profile.LineBreak(
            "CRLF", profile.ScalarSpan(1, 3, 1, 2, 2, 1)))
        self.assertEqual(source_map.source_text, "A\r\nB")

    def test_06_mixed_approved_line_endings_are_not_rewritten(self) -> None:
        source = "A\r\nB\nC\r\n"
        source_map = self.checked(source)
        self.assertEqual(source_map.line_starts, (0, 3, 5, 8))
        self.assertEqual(source_map.source_text, source)
        self.assertEqual(tuple(item.kind for item in source_map.line_breaks),
                         ("CRLF", "LF", "CRLF"))

    def test_07_only_space_and_tab_are_horizontal_spans(self) -> None:
        source_map = self.checked("A\t B  C")
        self.assertEqual(source_map.position(3), profile.SourcePosition(3, 1, 4))
        self.assertEqual(tuple((s.start_offset, s.end_offset)
                              for s in source_map.horizontal_whitespace), ((1, 3), (4, 6)))

    def test_08_comment_spans_exclude_lf_and_crlf(self) -> None:
        for line_end in ("\n", "\r\n"):
            with self.subTest(ending_length=len(line_end)):
                source = "// hi" + line_end + "B"
                source_map = self.checked(source)
                span = source_map.comments[0]
                self.assertEqual((span.start_offset, span.end_offset), (0, 5))
                self.assertEqual(source[span.start_offset:span.end_offset], "// hi")
                self.assertEqual(source_map.position(5 + len(line_end)).line, 2)

    def test_09_comment_at_eof_and_empty_comment_need_no_newline(self) -> None:
        for source in ("//", "// end", "A //"):
            with self.subTest(length=len(source)):
                source_map = self.checked(source)
                self.assertEqual(source_map.comments[-1].end_offset, len(source))
                self.assertEqual(source_map.line_breaks, ())
                self.assertEqual(source_map.source_text, source)

    def test_10_comment_only_mark_is_rejected_after_real_line_end(self) -> None:
        self.checked("A//\u200e\nB")
        result = profile.inspect_source_profile("A// note\n\u200eB")
        self.assertEqual(result.outcome, profile.PROFILE_REJECTED)
        self.assertEqual(result.reasons[0].code, profile.COMMENT_ONLY_CHARACTER)
        self.assertEqual(result.reasons[0].location.start_line, 2)

    def test_11_c0_exclusions_apply_outside_and_inside_comments(self) -> None:
        for point in range(0x20):
            if point in (0x09, 0x0A, 0x0D):
                continue
            expected = (profile.UNSUPPORTED_LINE_BREAK if point in (0x0B, 0x0C)
                        else profile.FORBIDDEN_CONTROL)
            for prefix in ("A", "//"):
                with self.subTest(point=point, comment=prefix == "//"):
                    result = profile.inspect_source_profile(prefix + chr(point))
                    self.assertEqual(result.outcome, profile.PROFILE_REJECTED)
                    self.assertEqual(result.reasons[0].code, expected)
                    self.assertIsNone(result.source_map)

    def test_12_c1_exclusions_apply_outside_and_inside_comments(self) -> None:
        for point in range(0x80, 0xA0):
            expected = (profile.UNSUPPORTED_LINE_BREAK if point == 0x85
                        else profile.FORBIDDEN_CONTROL)
            for prefix in ("A", "//"):
                with self.subTest(point=point, comment=prefix == "//"):
                    self.assertEqual(self.codes(prefix + chr(point)), (expected,))

    def test_13_unsupported_breaks_never_end_comments(self) -> None:
        for bad in ("\r", "\v", "\f", "\u0085", "\u2028", "\u2029"):
            with self.subTest(point=ord(bad)):
                self.assertEqual(self.codes("A" + bad), (profile.UNSUPPORTED_LINE_BREAK,))
                # LRM remains inside a comment despite the illegal visual line break.
                result = profile.inspect_source_profile("// a" + bad + "\u200e")
                self.assertEqual(tuple(r.code for r in result.reasons),
                                 (profile.UNSUPPORTED_LINE_BREAK,))
                self.assertIsNone(result.source_map)

    def test_14_all_stateful_bidi_controls_are_forbidden_in_both_contexts(self) -> None:
        for point in (*range(0x202A, 0x202F), *range(0x2066, 0x206A)):
            for prefix in ("A", "//"):
                with self.subTest(point=point, comment=prefix == "//"):
                    self.assertEqual(self.codes(prefix + chr(point)),
                                     (profile.BIDI_CONTROL_FORBIDDEN,))

    def test_15_feff_source_reason_is_separate_from_transport_bom(self) -> None:
        for source in ("\ufeffA", "A\ufeffB", "//\ufeff"):
            with self.subTest(length=len(source)):
                result = profile.inspect_source_profile(source)
                self.assertEqual(result.outcome, profile.PROFILE_REJECTED)
                self.assertEqual(result.reasons[0].code, profile.FEFF_FORBIDDEN)
                self.assertEqual(result.reasons[0].location.unit, "UNICODE_SCALAR")
        decoded = transport.inspect_source_bytes(b"\xef\xbb\xbfA", "i4-bom")
        self.assertEqual(decoded.reasons[0].code, transport.UTF8_BOM_FORBIDDEN)
        self.assertEqual(decoded.reasons[0].location.unit, "BYTE")

    def test_16_non_stateful_direction_marks_are_comment_only(self) -> None:
        for character in ("\u061c", "\u200e", "\u200f"):
            with self.subTest(point=ord(character)):
                self.assertEqual(self.checked("//" + character).source_text, "//" + character)
                self.assertEqual(self.codes("A" + character),
                                 (profile.COMMENT_ONLY_CHARACTER,))

    def test_17_pinned_default_ignorables_have_complete_range_membership(self) -> None:
        ranges = profile.DEFAULT_IGNORABLE_RANGES
        self.assertEqual(sum(end - start + 1 for start, end in ranges), 4174)
        self.assertTrue(all(end < nxt for (_, end), (nxt, _) in zip(ranges, ranges[1:])))
        allowed = []
        for start, end in ranges:
            for point in (start, end):
                forbidden = (point == 0xFEFF or 0x202A <= point <= 0x202E
                             or 0x2066 <= point <= 0x2069)
                if not forbidden:
                    with self.subTest(point=point):
                        self.assertEqual(self.codes(chr(point)),
                                         (profile.COMMENT_ONLY_CHARACTER,))
            allowed.extend(chr(point) for point in range(start, end + 1)
                           if point != 0xFEFF and not 0x202A <= point <= 0x202E
                           and not 0x2066 <= point <= 0x2069)
        source = "//" + "".join(allowed)
        self.assertEqual(self.checked(source).source_text, source)

    def test_18_unapproved_quotes_and_block_syntax_require_context(self) -> None:
        for source in ('"//\u200f"', "'//x'", "`//x`", "/* // x */", "A/B", "A = B"):
            with self.subTest(case_length=len(source)):
                result = profile.inspect_source_profile(source)
                self.assertEqual(result.outcome, profile.CONTEXT_REQUIRED)
                self.assertFalse(result.succeeded)
                self.assertFalse(result.checks_complete)
                self.assertIsNone(result.source_map)
                self.assertEqual(tuple(r.code for r in result.reasons),
                                 (profile.LEXICAL_CONTEXT_REQUIRED,))

    def test_19_unknown_context_does_not_resume_at_an_assumed_newline(self) -> None:
        source = '"unknown\n//\u200f'
        result = profile.inspect_source_profile(source)
        self.assertEqual(result.outcome, profile.CONTEXT_REQUIRED)
        self.assertEqual(len(result.reasons), 1)
        self.assertEqual(result.reasons[0].location.start_offset, 0)
        self.assertIsNone(result.source_map)

    def test_20_quotes_slashes_and_block_markers_inside_comments_are_payload(self) -> None:
        source = '// "quotes" /* fake */ /// \\ `x`\nA'
        source_map = self.checked(source)
        self.assertEqual(len(source_map.comments), 1)
        self.assertEqual(source_map.comments[0].end_offset, source.index("\n"))

    def test_21_unconditional_violations_are_reported_after_unresolved_context(self) -> None:
        result = profile.inspect_source_profile('"//\x00\u202e')
        self.assertEqual(result.outcome, profile.PROFILE_REJECTED)
        self.assertFalse(result.checks_complete)
        self.assertEqual(tuple(r.code for r in result.reasons), (
            profile.LEXICAL_CONTEXT_REQUIRED, profile.FORBIDDEN_CONTROL,
            profile.BIDI_CONTROL_FORBIDDEN))
        self.assertIsNone(result.source_map)

    def test_22_bytes_textus_and_lookalikes_are_not_coerced_to_source(self) -> None:
        calls = []

        class Lookalike:
            def __str__(self):
                calls.append("str")
                return "A"

            def __repr__(self):
                calls.append("repr")
                return "A"

        class TextSubclass(str):
            pass

        value = transcript.transcriptio("A", reviewed=True, accepted=True).value
        for item in (b"A", value, Lookalike(), TextSubclass("A"), None, 1):
            result = profile.inspect_source_profile(item)
            self.assertEqual(result.outcome, profile.INPUT_REJECTED)
            self.assertEqual(result.reasons[0].code, profile.EXPECTED_DECODED_TEXT)
            self.assertIsNone(result.reasons[0].location)
        self.assertEqual(calls, [])

    def test_23_surrogates_are_not_repaired_or_given_scalar_spans(self) -> None:
        for source in ("\ud800", "//\udfff", "\ud800\udc00"):
            result = profile.inspect_source_profile(source)
            self.assertEqual(result.outcome, profile.INPUT_REJECTED)
            self.assertEqual(result.reasons[0].code, profile.NON_SCALAR_INPUT)
            self.assertIsNone(result.reasons[0].location)
            self.assertIsNone(result.source_map)

    def test_24_size_limit_is_inclusive_and_precedes_scalar_scan(self) -> None:
        at_limit = "A" * profile.MAX_SOURCE_CODE_POINTS
        self.assertEqual(self.checked(at_limit).scalar_length, 65_536)
        for source in (at_limit + "A", at_limit + "\ud800"):
            result = profile.inspect_source_profile(source)
            self.assertEqual(result.outcome, profile.LIMITED)
            self.assertEqual(result.reasons[0].code, profile.SOURCE_PROFILE_LIMIT)
            self.assertFalse(result.checks_complete)
            self.assertIsNone(result.source_map)

    def test_25_diagnostic_limit_never_becomes_truncated_success(self) -> None:
        full = profile.inspect_source_profile("\x00" * profile.MAX_SOURCE_DIAGNOSTICS)
        self.assertEqual(full.outcome, profile.PROFILE_REJECTED)
        self.assertTrue(full.checks_complete)
        self.assertEqual(len(full.reasons), 128)
        limited = profile.inspect_source_profile("\x00" * 129)
        self.assertEqual(limited.outcome, profile.LIMITED)
        self.assertFalse(limited.checks_complete)
        self.assertEqual(len(limited.reasons), 129)
        self.assertEqual(limited.reasons[-1].code, profile.SOURCE_DIAGNOSTIC_LIMIT)
        self.assertIsNone(limited.reasons[-1].location)
        self.assertIsNone(limited.source_map)

    def test_26_reason_order_is_repeatable_and_locations_are_not_collapsed(self) -> None:
        source = "\u202eA\x00\u200f\x00\r"
        first = profile.inspect_source_profile(source)
        second = profile.inspect_source_profile(source)
        self.assertEqual(first.reasons, second.reasons)
        self.assertEqual(tuple(r.location.start_offset for r in first.reasons), (0, 2, 3, 4, 5))
        self.assertEqual(sum(r.code == profile.FORBIDDEN_CONTROL for r in first.reasons), 2)

    def test_27_offsets_and_columns_count_scalars_not_bytes_or_glyphs(self) -> None:
        source = "//😀e\u0301\nA\x00"
        result = profile.inspect_source_profile(source)
        location = result.reasons[0].location
        self.assertEqual(location, profile.ScalarSpan(7, 8, 2, 2, 2, 3))
        source_map = self.checked("//😀e\u0301\nA")
        self.assertEqual(source_map.position(5), profile.SourcePosition(5, 1, 6))
        self.assertEqual(source_map.position(6), profile.SourcePosition(6, 2, 1))

    def test_28_comment_sequences_are_not_normalized(self) -> None:
        precomposed, decomposed = "//é", "//e\u0301"
        self.assertEqual(self.checked(precomposed).source_text, precomposed)
        self.assertEqual(self.checked(decomposed).source_text, decomposed)
        self.assertNotEqual(tuple(map(ord, precomposed)), tuple(map(ord, decomposed)))

    def test_29_source_rejection_does_not_filter_a_reviewed_transcript(self) -> None:
        payload = "\x00\r\u202e\ufeff"
        decoded = transport.inspect_source_bytes(payload.encode("utf-8"), "i4-routing")
        self.assertEqual(decoded.decoded_text, payload)
        self.assertEqual(profile.inspect_source_profile(decoded.decoded_text).outcome,
                         profile.PROFILE_REJECTED)
        admitted = transcript.transcriptio(payload, reviewed=True, accepted=True)
        self.assertEqual(transcript.leg(admitted.value).payload, payload)
        self.assertIsNone(profile.inspect_source_profile(admitted.value).source_map)

    def test_30_inspection_is_silent_and_representations_are_source_free(self) -> None:
        secret = "I4_SYNTHETIC_SECRET_936ab"
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            good = profile.inspect_source_profile("//" + secret)
            bad = profile.inspect_source_profile(secret + "\x00")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        for record in (good, good.source_map, bad, *bad.reasons):
            self.assertNotIn(secret, repr(record))
        self.assertEqual(good.source_map.source_text, "//" + secret)

    def test_31_map_is_read_only_and_offset_misuse_is_explicit(self) -> None:
        source_map = self.checked("A")
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            source_map.source_text = "B"
        for offset in (-1, 2):
            with self.assertRaises(ValueError):
                source_map.position(offset)
        for offset in (True, 1.0, "1"):
            with self.assertRaises(TypeError):
                source_map.position(offset)
        self.assertEqual(source_map.source_text, "A")

    def test_32_unspecified_forms_are_not_silently_rejected_or_whitespace(self) -> None:
        for source in ("A\u00a0B", "A\u2003B", "A\x7fB", "עברית", "\ue100", "-", "("):
            result = profile.inspect_source_profile(source)
            self.assertEqual(result.outcome, profile.CONTEXT_REQUIRED)
            self.assertIsNone(result.source_map)
        # DEL is not in the explicit C0/C1 intervals; no new ban is invented.
        self.assertEqual(self.checked("//\x7f").source_text, "//\x7f")

    def test_33_profile_and_reason_identifiers_are_fixed(self) -> None:
        self.assertEqual(profile.PROFILE_ID, "gart-source-profile-inspector-i4-0.1")
        self.assertEqual(profile.UNICODE_DATA_VERSION, "17.0.0")
        codes = (profile.EXPECTED_DECODED_TEXT, profile.NON_SCALAR_INPUT,
                 profile.FORBIDDEN_CONTROL, profile.UNSUPPORTED_LINE_BREAK,
                 profile.FEFF_FORBIDDEN, profile.BIDI_CONTROL_FORBIDDEN,
                 profile.COMMENT_ONLY_CHARACTER, profile.LEXICAL_CONTEXT_REQUIRED,
                 profile.SOURCE_PROFILE_LIMIT, profile.SOURCE_DIAGNOSTIC_LIMIT,
                 profile.RESOURCE_EXHAUSTED)
        self.assertEqual(len(set(codes)), 11)
        for code in codes:
            self.assertIsNotNone(re.fullmatch(
                r"GART\.CORE_0_1\.[A-Z][A-Z0-9]*\.[A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)*", code))
        self.assertEqual(profile.RESOURCE_EXHAUSTED, transcript.RESOURCE_EXHAUSTED)

    def test_34_fixed_generated_source_preserves_exact_spans(self) -> None:
        alphabet = ("A", "a", "\t", " ", "_", "0")
        for length in range(33):
            source = "".join(alphabet[(i * 7 + length) % 6] for i in range(length))
            source += "//e\u0301😀\u200f\r\nB\n"
            source_map = self.checked(source)
            self.assertEqual(source_map.source_text, source)
            for comment in source_map.comments:
                self.assertTrue(source[comment.start_offset:comment.end_offset].startswith("//"))
            self.assertEqual(source_map.end_of_input.offset, len(source))
            self.assertEqual(source_map.end_of_input.column, 1)

    def test_35_source_inspection_has_no_io_normalization_or_execution_path(self) -> None:
        path = Path(profile.__file__).resolve()
        self.assertEqual(path.name, "core_0_1_source_profile.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertEqual(imports, {"__future__", "bisect", "dataclasses", "typing"})
        forbidden = {"eval", "exec", "compile", "open", "print", "input", "__import__",
                     "getattr", "setattr", "normalize", "strip", "lower", "upper", "casefold",
                     "isspace", "isidentifier", "splitlines", "system", "popen", "write_text",
                     "write_bytes", "connect", "transcriptio", "leg"}
        self.assertTrue(calls.isdisjoint(forbidden))

    def test_36_guarded_memory_failure_is_not_success_and_defects_propagate(self) -> None:
        with patch.object(profile, "_make_source_map", side_effect=MemoryError):
            result = profile.inspect_source_profile("A")
        self.assertEqual(result.outcome, profile.HOST_FAILED)
        self.assertEqual(result.reasons[0].code, profile.RESOURCE_EXHAUSTED)
        self.assertIsNone(result.source_map)
        for defect in (RuntimeError, KeyboardInterrupt):
            with patch.object(profile, "_make_source_map", side_effect=defect):
                with self.assertRaises(defect):
                    profile.inspect_source_profile("A")


if __name__ == "__main__":
    unittest.main()
