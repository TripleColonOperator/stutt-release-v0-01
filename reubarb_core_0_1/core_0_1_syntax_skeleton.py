"""I-6: grammar-free input/cursor/range support for a future parser.

Prepared input and fully consumed input do NOT mean a parsed or valid program.
There are no grammar productions, syntax-tree node kinds, parser entry point,
name bindings, recovery edits, target values, authorization, or execution here.
I-5 remains responsible for lexical classification. This component checks its
host records, not arbitrary source, and neither re-lexes nor interprets payloads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import core_0_1_lexical_frontend as lexical
import core_0_1_source_profile as source_profile

PROFILE_ID: Final[str] = "gart-syntax-skeleton-i6-0.1"
MAX_INPUT_ITEMS: Final[int] = 16_384  # Inclusive, non-EOF items; same as I-5.
PREPARED: Final[str] = "prepared"
UPSTREAM_STOPPED: Final[str] = "upstream-stopped"
INPUT_REJECTED: Final[str] = "input-rejected"
LIMITED: Final[str] = "limited"
HOST_FAILED: Final[str] = "host-failed"
FULLY_CONSUMED: Final[str] = "fully-consumed"
INCOMPLETE: Final[str] = "incomplete"

EXPECTED_LEXICAL_RESULT: Final[str] = "GART.CORE_0_1.SYNTAX.EXPECTED_LEXICAL_RESULT"
LEXICAL_RESULT_INVARIANT_FAILURE: Final[str] = (
    "GART.CORE_0_1.HOST.LEXICAL_RESULT_INVARIANT_FAILURE"
)
LEXICAL_STREAM_INVARIANT_FAILURE: Final[str] = (
    "GART.CORE_0_1.HOST.LEXICAL_STREAM_INVARIANT_FAILURE"
)
SYNTAX_INPUT_LIMIT: Final[str] = "GART.CORE_0_1.RESOURCE.SYNTAX_INPUT_LIMIT"
UNCONSUMED_ITEMS: Final[str] = "GART.CORE_0_1.SYNTAX.UNCONSUMED_ITEMS"
EOF_NOT_CONSUMED: Final[str] = "GART.CORE_0_1.SYNTAX.EOF_NOT_CONSUMED"
RESOURCE_EXHAUSTED: Final[str] = "GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED"

_KINDS: Final[tuple[str, ...]] = (
    "WORD", "EXACT_ATOM", "SPACE_TAB", "COMMENT", "LF", "CRLF", "EOF",
)
_STOP_OUTCOMES: Final[tuple[str, ...]] = (
    lexical.SOURCE_REJECTED, lexical.CONTEXT_REQUIRED, lexical.INPUT_REJECTED,
    lexical.LIMITED, lexical.HOST_FAILED,
)
_PROFILE_OUTCOMES: Final[tuple[str, ...]] = (
    source_profile.PROFILE_CHECKED, source_profile.PROFILE_REJECTED,
    source_profile.CONTEXT_REQUIRED, source_profile.INPUT_REJECTED,
    source_profile.LIMITED, source_profile.HOST_FAILED,
)
_UPSTREAM_CODES: Final[tuple[str, ...]] = (
    source_profile.EXPECTED_DECODED_TEXT, source_profile.NON_SCALAR_INPUT,
    source_profile.FORBIDDEN_CONTROL, source_profile.UNSUPPORTED_LINE_BREAK,
    source_profile.FEFF_FORBIDDEN, source_profile.BIDI_CONTROL_FORBIDDEN,
    source_profile.COMMENT_ONLY_CHARACTER, source_profile.LEXICAL_CONTEXT_REQUIRED,
    source_profile.SOURCE_PROFILE_LIMIT, source_profile.SOURCE_DIAGNOSTIC_LIMIT,
    source_profile.RESOURCE_EXHAUSTED, lexical.ZERO_BOUNDARY_REQUIRED,
    lexical.DIGIT_FORM_REQUIRED, lexical.LEXICAL_ITEM_LIMIT,
)
_SEAL = object()  # Supported-host construction marker, NOT Source authority.


@dataclass(frozen=True, slots=True)
class SyntaxReason:
    code: str
    location: source_profile.ScalarSpan | None = None


@dataclass(frozen=True, slots=True)
class SyntaxRange:
    """Half-open lexical-item interval and source span; not an AST node."""
    start_item: int
    end_item: int
    span: source_profile.ScalarSpan


def _span_key(span: source_profile.ScalarSpan) -> tuple[int, ...]:
    return (span.start_offset, span.end_offset, span.start_line,
            span.start_column, span.end_line, span.end_column)


def _span_shape(span: object) -> bool:
    if type(span) is not source_profile.ScalarSpan:
        return False
    if type(span.unit) is not str or span.unit != "UNICODE_SCALAR":
        return False
    fields = _span_key(span)
    return (all(type(value) is int for value in fields)
            and 0 <= fields[0] <= fields[1]
            and all(value >= 1 for value in fields[2:]))


def _span_from_map(mapping: source_profile.SourceMap, start: int,
                   end: int) -> source_profile.ScalarSpan:
    first, last = mapping.position(start), mapping.position(end)
    return source_profile.ScalarSpan(start, end, first.line, first.column,
                                     last.line, last.column)


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class SyntaxInput:
    """Read-only view of a checked complete I-5 stream; no parse result."""
    source_map: source_profile.SourceMap
    items: tuple[lexical.LexicalItem, ...]
    _seal: object
    profile_id: str = field(default=PROFILE_ID, init=False)

    def __repr__(self) -> str:
        return "SyntaxInput(<source omitted; grammar not evaluated>)"

    def source_range(self, start_item: int, end_item: int) -> SyntaxRange:
        """Describe [start_item, end_item), excluding EOF from nonempty ranges.

        An empty interval is a position marker only, not an empty production.
        The full lossless item sequence, including trivia/line breaks, is used.
        """
        if self._seal is not _SEAL:
            raise ValueError("Use prepared syntax input for range inspection.")
        if type(start_item) is not int or type(end_item) is not int:
            raise TypeError("Item indexes must be exact host integers.")
        non_eof_count = len(self.items) - 1
        if not 0 <= start_item <= end_item <= non_eof_count:
            raise ValueError("Item range is outside the prepared input.")
        start = self.items[start_item].span.start_offset
        end = start if start_item == end_item else self.items[end_item - 1].span.end_offset
        return SyntaxRange(start_item, end_item, _span_from_map(self.source_map, start, end))


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class PreparationResult:
    outcome: str
    syntax_input: SyntaxInput | None
    reasons: tuple[SyntaxReason, ...]
    upstream_outcome: str | None

    def __repr__(self) -> str:
        return "PreparationResult(<source omitted; no program-validity claim>)"


@dataclass(frozen=True, slots=True)
class ConsumptionResult:
    """Cursor bookkeeping only; complete does not mean parsed or authorized."""
    outcome: str
    reasons: tuple[SyntaxReason, ...]

    @property
    def complete(self) -> bool:
        return self.outcome == FULLY_CONSUMED


def _stopped(outcome: str, code: str, upstream: str | None) -> PreparationResult:
    return PreparationResult(outcome, None, (SyntaxReason(code),), upstream)


def _mapping_valid(mapping: source_profile.SourceMap) -> bool:
    source = mapping.source_text
    if (type(source) is not str or len(source) > source_profile.MAX_SOURCE_CODE_POINTS
            or type(mapping.line_starts) is not tuple
            or not 1 <= len(mapping.line_starts) <= len(source) + 1):
        return False
    starts = [0]
    for index, character in enumerate(source):
        if 0xD800 <= ord(character) <= 0xDFFF:
            return False
        if character == "\r" and not source.startswith("\r\n", index):
            return False
        if character == "\n":
            starts.append(index + 1)
    if (any(type(value) is not int for value in mapping.line_starts)
            or mapping.line_starts != tuple(starts)):
        return False
    for spans in (mapping.comments, mapping.horizontal_whitespace, mapping.line_breaks):
        if type(spans) is not tuple or len(spans) > MAX_INPUT_ITEMS:
            return False
    for span in mapping.comments + mapping.horizontal_whitespace:
        if not _span_shape(span):
            return False
    for entry in mapping.line_breaks:
        if (type(entry) is not source_profile.LineBreak or type(entry.kind) is not str
                or entry.kind not in ("LF", "CRLF") or not _span_shape(entry.span)):
            return False
    return True


def _metadata_valid(item: lexical.LexicalItem) -> bool:
    expected = None
    if item.kind in ("WORD", "EXACT_ATOM"):
        for record in lexical.APPROVED_SPELLINGS:
            if item.lexeme == record.spelling:
                expected = record
                break
    actual = item.approved_spelling
    if expected is None:
        return actual is None
    if type(actual) is not lexical.ApprovedSpelling:
        return False
    fields = (actual.spelling, actual.role, actual.decision_ref, actual.evidence_group)
    if any(type(value) is not str for value in fields):
        return False
    return fields == (expected.spelling, expected.role,
                      expected.decision_ref, expected.evidence_group)


def _stream_valid(stream: lexical.LexicalStream) -> bool:
    mapping = stream.source_map
    if type(mapping) is not source_profile.SourceMap or not _mapping_valid(mapping):
        return False
    source = mapping.source_text
    offset = 0
    comments, whitespace, breaks = [], [], []
    for index, item in enumerate(stream.items):
        if (type(item) is not lexical.LexicalItem or type(item.kind) is not str
                or item.kind not in _KINDS or type(item.lexeme) is not str
                or not _span_shape(item.span)):
            return False
        span = item.span
        if not offset == span.start_offset <= span.end_offset <= len(source):
            return False
        if _span_key(span) != _span_key(_span_from_map(mapping, offset, span.end_offset)):
            return False
        if item.lexeme != source[offset:span.end_offset] or not _metadata_valid(item):
            return False
        if index == len(stream.items) - 1:
            return item.kind == "EOF" and offset == span.end_offset == len(source) and (
                tuple(comments) == tuple(_span_key(s) for s in mapping.comments)
                and tuple(whitespace) == tuple(_span_key(s) for s in mapping.horizontal_whitespace)
                and tuple(breaks) == tuple((r.kind, _span_key(r.span)) for r in mapping.line_breaks)
            )
        if item.kind == "EOF" or span.end_offset <= offset:
            return False
        # Check carrier shape without retokenizing source or resolving grammar.
        if item.kind == "WORD":
            first = item.lexeme[0]
            if not ("A" <= first <= "Z" or "a" <= first <= "z" or first == "_"):
                return False
            if any(not ("A" <= c <= "Z" or "a" <= c <= "z"
                        or "0" <= c <= "9" or c == "_") for c in item.lexeme):
                return False
            # I-5 never divides one contiguous word-shaped run into two items.
            if span.end_offset < len(source):
                c = source[span.end_offset]
                if "A" <= c <= "Z" or "a" <= c <= "z" or "0" <= c <= "9" or c == "_":
                    return False
        elif item.kind == "EXACT_ATOM":
            if (item.lexeme != "0"
                    or (offset and source[offset - 1] not in " \t\r\n")
                    or (span.end_offset < len(source) and source[span.end_offset] not in " \t\r\n")):
                return False
        elif item.kind == "SPACE_TAB":
            if any(c not in " \t" for c in item.lexeme):
                return False
            whitespace.append(_span_key(span))
        elif item.kind == "COMMENT":
            if not item.lexeme.startswith("//") or "\n" in item.lexeme or "\r" in item.lexeme:
                return False
            comments.append(_span_key(span))
        else:
            if item.lexeme != ("\n" if item.kind == "LF" else "\r\n"):
                return False
            breaks.append((item.kind, _span_key(span)))
        offset = span.end_offset
    return False


def _make_input(stream: lexical.LexicalStream) -> SyntaxInput:
    """Single guarded preparation allocation; source/items are not rewritten."""
    return SyntaxInput(stream.source_map, stream.items, _SEAL)


def prepare_syntax_input(result: object) -> PreparationResult:
    """Accept an exact I-5 result, not raw text, bytes, textus, or a raw tuple.

    Non-success outcomes preserve approved upstream reasons, with no input view.
    Malformed host records are host failures, never new source-language errors.
    Trusted-host checks are not an authentication or hostile-Python sandbox.
    """
    if type(result) is not lexical.LexicalResult:
        return _stopped(INPUT_REJECTED, EXPECTED_LEXICAL_RESULT, None)
    upstream = None
    try:
        if (type(result.outcome) is not str or result.outcome not in (lexical.LEXED,) + _STOP_OUTCOMES
                or (result.source_profile_outcome is not None and (
                    type(result.source_profile_outcome) is not str
                    or result.source_profile_outcome not in _PROFILE_OUTCOMES))
                or type(result.reasons) is not tuple
                or len(result.reasons) > source_profile.MAX_SOURCE_DIAGNOSTICS + 1):
            return _stopped(HOST_FAILED, LEXICAL_RESULT_INVARIANT_FAILURE, None)
        upstream = result.outcome
        for reason in result.reasons:
            if (type(reason) is not lexical.LexicalReason or type(reason.code) is not str
                    or reason.code not in _UPSTREAM_CODES
                    or (reason.location is not None and not _span_shape(reason.location))):
                return _stopped(HOST_FAILED, LEXICAL_RESULT_INVARIANT_FAILURE, upstream)
        if upstream != lexical.LEXED:
            if result.stream is not None or not result.reasons:
                return _stopped(HOST_FAILED, LEXICAL_RESULT_INVARIANT_FAILURE, upstream)
            return PreparationResult(UPSTREAM_STOPPED, None,
                                     tuple(SyntaxReason(r.code, r.location) for r in result.reasons), upstream)
        if (type(result.stream) is not lexical.LexicalStream or result.reasons
                or result.source_profile_outcome != source_profile.PROFILE_CHECKED):
            return _stopped(HOST_FAILED, LEXICAL_RESULT_INVARIANT_FAILURE, upstream)
        stream = result.stream
        if (type(stream.profile_id) is not str or stream.profile_id != lexical.PROFILE_ID
                or type(stream.items) is not tuple or not stream.items):
            return _stopped(HOST_FAILED, LEXICAL_STREAM_INVARIANT_FAILURE, upstream)
        if len(stream.items) > MAX_INPUT_ITEMS + 1:
            return _stopped(LIMITED, SYNTAX_INPUT_LIMIT, upstream)
        if not _stream_valid(stream):
            return _stopped(HOST_FAILED, LEXICAL_STREAM_INVARIANT_FAILURE, upstream)
        return PreparationResult(PREPARED, _make_input(stream), (), upstream)
    except MemoryError:
        # Even diagnostic allocation can fail catastrophically: then stop.
        return _stopped(HOST_FAILED, RESOURCE_EXHAUSTED, upstream)


class ParserCursor:
    """Forward-only host cursor. It does not decide what any sequence means."""
    __slots__ = ("_input", "_index")

    def __init__(self, syntax_input: SyntaxInput) -> None:
        if type(syntax_input) is not SyntaxInput or syntax_input._seal is not _SEAL:
            raise TypeError("ParserCursor requires prepared syntax input.")
        self._input = syntax_input
        self._index = 0

    def __repr__(self) -> str:
        return "ParserCursor(<source omitted; grammar not evaluated>)"

    @property
    def position(self) -> int:
        return self._index

    @property
    def exhausted(self) -> bool:
        return self._index == len(self._input.items)

    def peek(self, ahead: int = 0) -> lexical.LexicalItem | None:
        if type(ahead) is not int:
            raise TypeError("Lookahead must be an exact host integer.")
        if ahead < 0:
            raise ValueError("Lookahead must not be negative.")
        if ahead >= len(self._input.items) - self._index:
            return None
        return self._input.items[self._index + ahead]

    def advance(self) -> lexical.LexicalItem | None:
        item = self.peek()
        if item is not None:
            self._index += 1
        return item

    def skip_trivia(self) -> int:
        """Explicitly traverse SPACE_TAB/COMMENT only. Never skip LF or CRLF."""
        start = self._index
        while self._index < len(self._input.items):
            if self._input.items[self._index].kind not in ("SPACE_TAB", "COMMENT"):
                break
            self._index += 1
        return self._index - start

    def finish(self) -> ConsumptionResult:
        """Check full traversal, without moving or claiming grammar success."""
        item = self.peek()
        if item is None:
            return ConsumptionResult(FULLY_CONSUMED, ())
        code = EOF_NOT_CONSUMED if item.kind == "EOF" else UNCONSUMED_ITEMS
        return ConsumptionResult(INCOMPLETE, (SyntaxReason(code, item.span),))


__all__ = (
    "prepare_syntax_input", "SyntaxInput", "SyntaxReason", "SyntaxRange",
    "PreparationResult", "ParserCursor", "ConsumptionResult", "PROFILE_ID",
    "MAX_INPUT_ITEMS",
)
