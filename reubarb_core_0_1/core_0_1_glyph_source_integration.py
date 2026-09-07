"""I-15: accepted native-glyph source-integration layer.

This module intentionally stays small and bounded:

* It accepts a verified source profile.
* It extracts a source-level non-trivia token stream.
* It treats one-and-only-one non-trivia token as a glyph-candidate observation.
* It preserves explicit source-profile outcomes.
* It delegates candidate meaning to the existing I-10/I-11 mapping profile.

This is a bounded recognition layer. It does not define execution, authorization,
scope, lifetime, assignment, or semantic precedence for the language.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Final

import core_0_1_glyph_recognizer as glyph_recognizer
import core_0_1_source_profile as source_profile

PROFILE_ID: Final[str] = "gart-native-glyph-source-integration-i15-0.1"
PARSED: Final[str] = "parsed"
OBSERVED: Final[str] = "observed"
INPUT_REJECTED: Final[str] = "input-rejected"
SOURCE_REJECTED: Final[str] = "source-rejected"
SYNTAX_REJECTED: Final[str] = "syntax-rejected"
EMPTY_GLYPH_SOURCE: Final[str] = "GART.CORE_0_1.GLYPH_SOURCE.EMPTY_GLYPH_SOURCE"
INCOMPLETE_GLYPH_RELATIONSHIP: Final[str] = (
    "GART.CORE_0_1.GLYPH_SOURCE.INCOMPLETE_GLYPH_RELATIONSHIP"
)
UNAUTHORIZED_SOURCE_FORM: Final[str] = (
    "GART.CORE_0_1.GLYPH_SOURCE.UNAUTHORIZED_SOURCE_FORM"
)
UNRECOGNIZED_GLYPH: Final[str] = "GART.CORE_0_1.GLYPH_SOURCE.UNRECOGNIZED_GLYPH"
HOST_FAILED: Final[str] = "GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class GlyphSourceReason:
    code: str
    location: source_profile.ScalarSpan | None = None


@dataclass(frozen=True, slots=True, repr=False)
class GlyphCandidateInstruction:
    candidate: str
    candidate_span: source_profile.ScalarSpan
    source_map: source_profile.SourceMap | None
    instruction_span: source_profile.ScalarSpan

    def __repr__(self) -> str:
        return "GlyphCandidateInstruction(<source omitted>)"


@dataclass(frozen=True, slots=True, repr=False)
class GlyphSourceParseResult:
    outcome: str
    instruction: GlyphCandidateInstruction | None
    reasons: tuple[GlyphSourceReason, ...]
    source_profile_outcome: str | None

    @property
    def succeeded(self) -> bool:
        return self.outcome == PARSED

    def __repr__(self) -> str:
        return "GlyphSourceParseResult(<source omitted>)"


@dataclass(frozen=True, slots=True)
class GlyphCandidateObservation:
    candidate: str
    candidate_span: source_profile.ScalarSpan
    outcome: str
    design_id: int | None
    code_point_label: str | None


@dataclass(frozen=True, slots=True, repr=False)
class GlyphSourceObservationResult:
    outcome: str
    parse_result: GlyphSourceParseResult
    reasons: tuple[GlyphSourceReason, ...]
    observation: GlyphCandidateObservation | None

    @property
    def succeeded(self) -> bool:
        return self.outcome == OBSERVED

    def __repr__(self) -> str:
        return "GlyphSourceObservationResult(<source omitted>)"


def _span(mapping: source_profile.SourceMap, start: int, end: int) -> source_profile.ScalarSpan:
    first = mapping.position(start)
    last = mapping.position(end)
    return source_profile.ScalarSpan(
        start, end, first.line, first.column, last.line, last.column
    )


def _line_starts(text: str) -> tuple[int, ...]:
    return (0,) + tuple(index + 1 for index, character in enumerate(text) if character == "\n")


def _text_span(text: str, start: int, end: int) -> source_profile.ScalarSpan:
    starts = _line_starts(text)
    first_row = bisect_right(starts, start) - 1
    last_row = bisect_right(starts, end) - 1
    return source_profile.ScalarSpan(
        start,
        end,
        first_row + 1,
        start - starts[first_row] + 1,
        last_row + 1,
        end - starts[last_row] + 1,
    )


def _trivia_spans(mapping: source_profile.SourceMap) -> tuple[tuple[int, int], ...]:
    intervals = []
    for span in mapping.horizontal_whitespace:
        intervals.append((span.start_offset, span.end_offset))
    for line_break in mapping.line_breaks:
        intervals.append((line_break.span.start_offset, line_break.span.end_offset))
    for comment in mapping.comments:
        intervals.append((comment.start_offset, comment.end_offset))
    return tuple(sorted(intervals, key=lambda value: value[0]))


def _extract_tokens(mapping: source_profile.SourceMap) -> tuple[
    tuple[str, source_profile.ScalarSpan], ...
]:
    text = mapping.source_text
    length = len(text)
    trivia = _trivia_spans(mapping)
    tokens: list[tuple[str, source_profile.ScalarSpan]] = []

    index = 0
    trivia_index = 0
    while index < length:
        while trivia_index < len(trivia) and trivia[trivia_index][1] <= index:
            trivia_index += 1
        if trivia_index < len(trivia):
            trivia_start, trivia_end = trivia[trivia_index]
            if trivia_start <= index < trivia_end:
                index = trivia_end
                continue

        start = index
        index += 1
        while index < length:
            while trivia_index < len(trivia) and trivia[trivia_index][1] <= index:
                trivia_index += 1
            if trivia_index < len(trivia):
                trivia_start, trivia_end = trivia[trivia_index]
                if trivia_start <= index < trivia_end:
                    break
            index += 1
        tokens.append((text[start:index], _span(mapping, start, index)))

    return tuple(tokens)


def _extract_tokens_from_text(text: str) -> tuple[
    tuple[str, source_profile.ScalarSpan], ...
]:
    """Resolve only the I-15 candidate boundary after I-4 requests context.

    A line comment is recognized only where the scanner is between tokens.
    Consequently, direct candidate/comment adjacency is retained as one
    unresolved source form rather than silently creating a new delimiter rule.
    """
    length = len(text)
    tokens: list[tuple[str, source_profile.ScalarSpan]] = []
    index = 0
    while index < length:
        if text[index] in (" ", "\t", "\n"):
            index += 1
            continue
        if text.startswith("\r\n", index):
            index += 2
            continue
        if text.startswith("//", index):
            index += 2
            while index < length and text[index] != "\n" and not text.startswith("\r\n", index):
                index += 1
            continue

        start = index
        index += 1
        while index < length:
            if text[index] in (" ", "\t", "\n") or text.startswith("\r\n", index):
                break
            index += 1
        tokens.append((text[start:index], _text_span(text, start, index)))

    return tuple(tokens)


def _parse_prepared_from_text(source: str) -> GlyphSourceParseResult:
    tokens = _extract_tokens_from_text(source)
    if not tokens:
        return _failure(
            SYNTAX_REJECTED, EMPTY_GLYPH_SOURCE, None, source_profile.CONTEXT_REQUIRED
        )
    if len(tokens) != 1:
        return _failure(
            SYNTAX_REJECTED, INCOMPLETE_GLYPH_RELATIONSHIP, tokens[1][1],
            source_profile.CONTEXT_REQUIRED,
        )

    candidate, span = tokens[0]
    if len(candidate) != 1:
        return _failure(
            SYNTAX_REJECTED,
            UNAUTHORIZED_SOURCE_FORM, span, source_profile.CONTEXT_REQUIRED,
        )

    instruction_span = _text_span(source, 0, len(source))
    return GlyphSourceParseResult(
        PARSED,
        GlyphCandidateInstruction(candidate, span, None, instruction_span),
        (),
        source_profile.CONTEXT_REQUIRED,
    )


def _failure(outcome: str, code: str | None,
             span: source_profile.ScalarSpan | None,
             profile_outcome: str | None) -> GlyphSourceParseResult:
    reasons = () if code is None else (GlyphSourceReason(code, span),)
    return GlyphSourceParseResult(outcome, None, reasons, profile_outcome)


def _parse_prepared(mapping: source_profile.SourceMap) -> GlyphSourceParseResult:
    tokens = _extract_tokens(mapping)
    if not tokens:
        return _failure(
            SYNTAX_REJECTED, EMPTY_GLYPH_SOURCE, None, source_profile.PROFILE_CHECKED
        )
    if len(tokens) != 1:
        return _failure(
            SYNTAX_REJECTED, INCOMPLETE_GLYPH_RELATIONSHIP, tokens[1][1],
            source_profile.PROFILE_CHECKED,
        )

    candidate, span = tokens[0]
    if len(candidate) != 1:
        return _failure(
            SYNTAX_REJECTED,
            UNAUTHORIZED_SOURCE_FORM, span, source_profile.PROFILE_CHECKED,
        )

    instruction_span = _span(mapping, 0, len(mapping.source_text))
    return GlyphSourceParseResult(
        PARSED,
        GlyphCandidateInstruction(candidate, span, mapping, instruction_span),
        (),
        source_profile.PROFILE_CHECKED,
    )


def parse_glyph_source_candidate(source_text: object) -> GlyphSourceParseResult:
    """Parse one standalone non-trivia glyph-candidate from checked source text."""
    if type(source_text) is not str:
        return GlyphSourceParseResult(
            INPUT_REJECTED,
            None,
            (GlyphSourceReason("GART.CORE_0_1.HOST.EXPECTED_STRING"),),
            None,
        )
    try:
        inspected = source_profile.inspect_source_profile(source_text)
        if inspected.outcome == source_profile.PROFILE_REJECTED:
            if inspected.reasons is None:
                return GlyphSourceParseResult(SOURCE_REJECTED, None, (), inspected.outcome)
            reasons = tuple(
                GlyphSourceReason(reason.code, reason.location) for reason in inspected.reasons
            )
            return GlyphSourceParseResult(SOURCE_REJECTED, None, reasons, inspected.outcome)

        if inspected.outcome == source_profile.PROFILE_CHECKED:
            if inspected.source_map is None:
                raise RuntimeError("Source-profile invariant failed.")
            return _parse_prepared(inspected.source_map)
        if inspected.outcome == source_profile.CONTEXT_REQUIRED:
            return _parse_prepared_from_text(source_text)

        reasons = tuple(
            GlyphSourceReason(reason.code, reason.location) for reason in inspected.reasons
        )
        return GlyphSourceParseResult(
            SOURCE_REJECTED, None, reasons, inspected.outcome
        )
    except MemoryError:
        return GlyphSourceParseResult(
            HOST_FAILED,
            None,
            (GlyphSourceReason(HOST_FAILED),),
            None,
        )


def observe_glyph_source_candidate(source_text: object) -> GlyphSourceObservationResult:
    """Parse and classify one candidate through I-11 recognition."""
    parsed = parse_glyph_source_candidate(source_text)
    if not parsed.succeeded:
        return GlyphSourceObservationResult(parsed.outcome, parsed, parsed.reasons, None)

    instruction = parsed.instruction
    if instruction is None:
        raise RuntimeError("Parsed glyph instruction missing despite success outcome.")

    try:
        recognition = glyph_recognizer.recognize_glyph_candidate(instruction.candidate)
        reasons = ()
        if recognition.outcome is glyph_recognizer.RecognitionOutcome.UNRECOGNIZED:
            reasons = (GlyphSourceReason(UNRECOGNIZED_GLYPH, instruction.candidate_span),)
        return GlyphSourceObservationResult(
            OBSERVED,
            parsed,
            reasons,
            GlyphCandidateObservation(
                instruction.candidate,
                instruction.candidate_span,
                recognition.outcome.value,
                recognition.design_id,
                recognition.code_point_label,
            ),
        )
    except MemoryError:
        return GlyphSourceObservationResult(
            HOST_FAILED,
            parsed,
            (GlyphSourceReason(HOST_FAILED),),
            None,
        )


__all__ = (
    "parse_glyph_source_candidate",
    "observe_glyph_source_candidate",
    "GlyphSourceReason",
    "GlyphSourceParseResult",
    "GlyphCandidateInstruction",
    "GlyphCandidateObservation",
    "GlyphSourceObservationResult",
    "PROFILE_ID",
)
