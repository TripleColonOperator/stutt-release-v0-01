"""I-5: lossless lexical foundation for the already-approved source subset.

This is not a parser, evaluator, keyword-reservation policy, or program checker.
WORD means the approved ASCII identifier form; optional spelling metadata does
not decide whether a later grammar treats that word as a reserved keyword.
Only isolated 0 is an EXACT_ATOM. Undecided digit forms/adjacency need context.

The two BHS evidence modules are design references, not runtime dependencies.
No draft word, gloss, expansion, witness siglum, or sign promotes itself here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import core_0_1_source_profile as source_profile

PROFILE_ID: Final[str] = "gart-lexical-frontend-i5-0.1"
MAX_LEXICAL_ITEMS: Final[int] = 16_384  # Non-EOF items, including retained trivia.

LEXED: Final[str] = "lexed"
SOURCE_REJECTED: Final[str] = "source-rejected"
CONTEXT_REQUIRED: Final[str] = "context-required"
INPUT_REJECTED: Final[str] = "input-rejected"
LIMITED: Final[str] = "limited"
HOST_FAILED: Final[str] = "host-failed"

ZERO_BOUNDARY_REQUIRED: Final[str] = "GART.CORE_0_1.LEXICAL.ZERO_BOUNDARY_REQUIRED"
DIGIT_FORM_REQUIRED: Final[str] = "GART.CORE_0_1.LEXICAL.DIGIT_FORM_REQUIRED"
LEXICAL_ITEM_LIMIT: Final[str] = "GART.CORE_0_1.RESOURCE.LEXICAL_ITEM_LIMIT"
RESOURCE_EXHAUSTED: Final[str] = "GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class ApprovedSpelling:
    """Fixed evidence metadata, never a callable or dispatch instruction."""
    spelling: str
    role: str
    decision_ref: str
    evidence_group: str


# First eight spellings match the unchanged historical lexical-core registry.
# The last three come from the later explicit I-2 runtime approval, NOT from
# upgrading its BHS working-draft entries or borrowing their lexical glosses.
APPROVED_SPELLINGS: Final[tuple[ApprovedSpelling, ...]] = (
    ApprovedSpelling("0", "boundary-local zero", "USR-ZERO", "original-eight"),
    ApprovedSpelling("WITH", "conjunction", "USR-WITH", "original-eight"),
    ApprovedSpelling("OR", "disjunction", "USR-OR", "original-eight"),
    ApprovedSpelling("FALSE", "negation", "USR-FALSE", "original-eight"),
    ApprovedSpelling("RECON", "reconcile within reversion", "USR-RECON", "original-eight"),
    ApprovedSpelling("DPEND", "congruent relation within reversion", "USR-DPEND", "original-eight"),
    ApprovedSpelling("IDENTITY", "identity", "USR-IDENTITY-PROMOTION", "original-eight"),
    ApprovedSpelling("BOUNDARY", "boundary", "USR-BOUNDARY-PROMOTION", "original-eight"),
    ApprovedSpelling("textus", "reviewed-transcript runtime type", "I-2", "transcript-runtime"),
    ApprovedSpelling("transcriptio", "reviewed-transcript admission operation", "I-2", "transcript-runtime"),
    ApprovedSpelling("leg", "whole-transcript exact observation operation", "I-2", "transcript-runtime"),
)


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class LexicalItem:
    """Exact host lexeme and scalar span; ordinary repr omits source content."""
    kind: str  # WORD, EXACT_ATOM, SPACE_TAB, COMMENT, LF, CRLF, or EOF.
    lexeme: str
    span: source_profile.ScalarSpan
    approved_spelling: ApprovedSpelling | None = None

    def __repr__(self) -> str:
        return "LexicalItem(<source omitted>)"


@dataclass(frozen=True, slots=True)
class LexicalReason:
    code: str
    location: source_profile.ScalarSpan | None = None


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class LexicalStream:
    """Complete lossless host record, not a Reubarb value or executable unit."""
    source_map: source_profile.SourceMap
    items: tuple[LexicalItem, ...]
    profile_id: str = field(default=PROFILE_ID, init=False)

    def __repr__(self) -> str:
        return "LexicalStream(<source omitted>)"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class LexicalResult:
    outcome: str
    stream: LexicalStream | None
    reasons: tuple[LexicalReason, ...]
    source_profile_outcome: str | None

    @property
    def succeeded(self) -> bool:
        """Success only for this lexical subset; never means a valid program."""
        return self.outcome == LEXED

    def __repr__(self) -> str:
        return (
            f"LexicalResult(outcome={self.outcome!r}, "
            f"source_profile_outcome={self.source_profile_outcome!r}, "
            f"reason_count={len(self.reasons)}, source=<omitted>)"
        )


def _word_start(character: str) -> bool:
    return "A" <= character <= "Z" or "a" <= character <= "z" or character == "_"


def _word_continue(character: str) -> bool:
    return _word_start(character) or "0" <= character <= "9"


def _approved(lexeme: str) -> ApprovedSpelling | None:
    # Eleven fixed entries; no registry population or dispatch from user input.
    for record in APPROVED_SPELLINGS:
        if lexeme == record.spelling:
            return record
    return None


def _span(source_map: source_profile.SourceMap, start: int,
          end: int) -> source_profile.ScalarSpan:
    first, last = source_map.position(start), source_map.position(end)
    return source_profile.ScalarSpan(start, end, first.line, first.column,
                                     last.line, last.column)


def _failure(outcome: str, code: str, location: source_profile.ScalarSpan | None,
             profile_outcome: str | None) -> LexicalResult:
    return LexicalResult(outcome, None, (LexicalReason(code, location),), profile_outcome)


def _make_stream(source_map: source_profile.SourceMap,
                 items: list[LexicalItem]) -> LexicalStream:
    """One guarded allocation boundary for the complete stream."""
    return LexicalStream(source_map, tuple(items))


def _scan(source_map: source_profile.SourceMap) -> LexicalResult:
    source = source_map.source_text
    spans: list[tuple[str, source_profile.ScalarSpan]] = []
    spans.extend(("SPACE_TAB", span) for span in source_map.horizontal_whitespace)
    spans.extend(("COMMENT", span) for span in source_map.comments)
    spans.extend((line.kind, line.span) for line in source_map.line_breaks)
    spans.sort(key=lambda value: value[1].start_offset)

    # I-4 supplies these records; do not duplicate or broaden its comment rules.
    trivia: dict[int, tuple[str, source_profile.ScalarSpan]] = {}
    previous_end = 0
    for kind, span in spans:
        if (kind not in ("SPACE_TAB", "COMMENT", "LF", "CRLF")
                or not previous_end <= span.start_offset < span.end_offset <= len(source)):
            raise RuntimeError("Source-profile trivia invariant failed.")
        trivia[span.start_offset] = (kind, span)
        previous_end = span.end_offset

    items: list[LexicalItem] = []
    index, length = 0, len(source)
    while index < length:
        if len(items) >= MAX_LEXICAL_ITEMS:
            # No prefix stream or synthesized EOF is exposed as a success.
            return _failure(LIMITED, LEXICAL_ITEM_LIMIT, None,
                            source_profile.PROFILE_CHECKED)
        entry = trivia.get(index)
        if entry is not None:
            kind, span = entry
            items.append(LexicalItem(kind, source[index:span.end_offset], span))
            index = span.end_offset
            continue

        if not _word_continue(source[index]):
            # Unreachable through the supported I-4 profile, not a guessed
            # target-language error for an unapproved operator or literal.
            raise RuntimeError("Source-profile content invariant failed.")
        end = index + 1
        while end < length and _word_continue(source[end]):
            end += 1
        lexeme = source[index:end]
        span = _span(source_map, index, end)
        if _word_start(lexeme[0]):
            # Complete maximal identifier-form run before exact spelling match.
            item = LexicalItem("WORD", lexeme, span, _approved(lexeme))
        elif lexeme == "0":
            # The genuinely isolated atom is already established. Adjacency to
            # a comment marker without whitespace stays unresolved in I-5.
            left_known = index == 0 or source[index - 1] in " \t\r\n"
            right_known = end == length or source[end] in " \t\r\n"
            if not (left_known and right_known):
                return _failure(CONTEXT_REQUIRED, ZERO_BOUNDARY_REQUIRED, span,
                                source_profile.PROFILE_CHECKED)
            item = LexicalItem("EXACT_ATOM", lexeme, span, _approved(lexeme))
        else:
            reason = ZERO_BOUNDARY_REQUIRED if lexeme[0] == "0" else DIGIT_FORM_REQUIRED
            return _failure(CONTEXT_REQUIRED, reason, span,
                            source_profile.PROFILE_CHECKED)
        items.append(item)
        index = end

    # Every non-EOF item is positive-width and adjacent to the next. Checked
    # here independently of the scanning branches, with source-free failures.
    offset = 0
    for item in items:
        if (item.span.start_offset != offset
                or item.span.end_offset <= offset
                or item.lexeme != source[offset:item.span.end_offset]):
            raise RuntimeError("Lexical full-accounting invariant failed.")
        offset = item.span.end_offset
    if offset != length:
        raise RuntimeError("Lexical end-of-input invariant failed.")
    items.append(LexicalItem("EOF", "", _span(source_map, length, length)))
    stream = _make_stream(source_map, items)
    return LexicalResult(LEXED, stream, (), source_profile.PROFILE_CHECKED)


def lex_source(source_text: object) -> LexicalResult:
    """Inspect explicitly supplied decoded source and lex its supported subset.

    Bytes, textus values, and lookalikes are not coerced or observed. Existing
    I-4 failure/context/limit reasons retain their exact identities and spans.
    No incomplete stream is released; unknown defects and cancellation escape
    rather than being hidden behind a source-invalid or successful result.
    """
    profile_outcome: str | None = None
    try:
        profile = source_profile.inspect_source_profile(source_text)
        profile_outcome = profile.outcome
        if profile.outcome != source_profile.PROFILE_CHECKED:
            outcomes = {
                source_profile.PROFILE_REJECTED: SOURCE_REJECTED,
                source_profile.CONTEXT_REQUIRED: CONTEXT_REQUIRED,
                source_profile.INPUT_REJECTED: INPUT_REJECTED,
                source_profile.LIMITED: LIMITED,
                source_profile.HOST_FAILED: HOST_FAILED,
            }
            if profile.outcome not in outcomes:
                raise RuntimeError("Unknown source-profile outcome.")
            reasons = tuple(LexicalReason(reason.code, reason.location)
                            for reason in profile.reasons)
            return LexicalResult(outcomes[profile.outcome], None, reasons, profile.outcome)
        if profile.source_map is None or not profile.checks_complete or profile.reasons:
            raise RuntimeError("Successful source-profile invariant failed.")
        return _scan(profile.source_map)
    except MemoryError:
        # Allocating even this reason can fail catastrophically; then let the
        # host stop. Never claim complete recovery or release a partial stream.
        return _failure(HOST_FAILED, RESOURCE_EXHAUSTED, None, profile_outcome)


__all__ = (
    "lex_source", "ApprovedSpelling", "APPROVED_SPELLINGS", "LexicalItem",
    "LexicalReason", "LexicalStream", "LexicalResult", "PROFILE_ID",
    "MAX_LEXICAL_ITEMS",
)
