"""I-7: one approved BHS-anchored reading instruction and bounded adapter.

    ReadUnit ::= Padding WORD('leg') SPACE_TAB WORD Padding EOF
    Padding  ::= (SPACE_TAB | COMMENT | LF | CRLF)*

Parsing is inert. Only an explicit observe_read_unit invocation can call I-2
leg, once, after complete parsing and exact agreement with its supplied label.
The one-call host association is not a language environment or Source grant.
Transcript payload is never admitted, lexed, interpreted, displayed, or executed
here. The BHS research modules are evidence references, not runtime imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import core_0_1_lexical_frontend as lexical
import core_0_1_source_profile as source_profile
import core_0_1_syntax_skeleton as syntax
import core_0_1_transcript_runtime as runtime

PROFILE_ID: Final[str] = "gart-read-instruction-i7-0.1"
PARSED: Final[str] = "parsed"
SYNTAX_REJECTED: Final[str] = "syntax-rejected"
TARGET_REJECTED: Final[str] = "target-rejected"
HOST_FAILED: Final[str] = "host-failed"

EXPECTED_READ_HEAD: Final[str] = "GART.CORE_0_1.SYNTAX.EXPECTED_READ_HEAD"
EXPECTED_HORIZONTAL_GAP: Final[str] = "GART.CORE_0_1.SYNTAX.EXPECTED_HORIZONTAL_GAP"
EXPECTED_TARGET_NAME: Final[str] = "GART.CORE_0_1.SYNTAX.EXPECTED_TARGET_NAME"
EXPECTED_READ_EOF: Final[str] = "GART.CORE_0_1.SYNTAX.EXPECTED_READ_EOF"
INVALID_TARGET_LABEL: Final[str] = "GART.CORE_0_1.READ.INVALID_TARGET_LABEL"
TARGET_NAME_MISMATCH: Final[str] = "GART.CORE_0_1.READ.TARGET_NAME_MISMATCH"
RESOURCE_EXHAUSTED: Final[str] = "GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED"

_PADDING: Final[tuple[str, ...]] = ("SPACE_TAB", "COMMENT", "LF", "CRLF")


@dataclass(frozen=True, slots=True)
class ReadReason:
    """Source/payload-free reason; scalar locations refer only to instruction source."""
    code: str
    location: source_profile.ScalarSpan | None = None


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class ReadInstruction:
    """Host syntax record, not a runtime value, lookup, or authorization.

    The original read-only input retains all source records, including padding
    and EOF. Ranges are I-6 half-open intervals; nonempty ranges exclude EOF.
    """
    target_name: str
    syntax_input: syntax.SyntaxInput
    head_range: syntax.SyntaxRange
    target_range: syntax.SyntaxRange
    instruction_range: syntax.SyntaxRange
    unit_range: syntax.SyntaxRange

    def __repr__(self) -> str:
        return "ReadInstruction(<source omitted; no observation or authorization>)"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class ReadParseResult:
    outcome: str
    instruction: ReadInstruction | None
    reasons: tuple[ReadReason | syntax.SyntaxReason, ...]
    preparation: syntax.PreparationResult
    source_profile_outcome: str | None

    @property
    def succeeded(self) -> bool:
        """Success for this single read grammar, not authorization or execution."""
        return self.outcome == PARSED

    def __repr__(self) -> str:
        return "ReadParseResult(<source omitted; no observation or authorization>)"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class ReadObservationResult:
    outcome: str
    parse_result: ReadParseResult
    reasons: tuple[ReadReason | syntax.SyntaxReason, ...]
    observation: runtime.ObservationResult | None

    @property
    def succeeded(self) -> bool:
        return self.outcome == runtime.OBSERVED

    def __repr__(self) -> str:
        return "ReadObservationResult(<source and payload omitted>)"


def _skip_padding(cursor: syntax.ParserCursor) -> None:
    # Line records may surround the instruction, never separate head and target.
    while (item := cursor.peek()) is not None and item.kind in _PADDING:
        cursor.advance()


def _parse_prepared(preparation: syntax.PreparationResult,
                    profile_outcome: str | None) -> ReadParseResult:
    """Finite grammar traversal and guarded syntax-record allocation."""
    view = preparation.syntax_input
    if view is None:
        raise RuntimeError("Prepared read-input invariant failed.")
    cursor = syntax.ParserCursor(view)

    def reject(code: str) -> ReadParseResult:
        item = cursor.peek()
        if item is None:
            raise RuntimeError("Read cursor reached unexpected exhaustion.")
        return ReadParseResult(SYNTAX_REJECTED, None,
                               (ReadReason(code, item.span),),
                               preparation, profile_outcome)

    _skip_padding(cursor)
    head_index = cursor.position
    head = cursor.peek()
    if head.kind != "WORD" or head.lexeme != "leg":
        return reject(EXPECTED_READ_HEAD)
    cursor.advance()
    if cursor.peek().kind != "SPACE_TAB":
        return reject(EXPECTED_HORIZONTAL_GAP)
    cursor.advance()
    target_index = cursor.position
    target = cursor.peek()
    if target.kind != "WORD":
        return reject(EXPECTED_TARGET_NAME)
    cursor.advance()
    instruction_end = cursor.position
    _skip_padding(cursor)
    if cursor.peek().kind != "EOF":
        return reject(EXPECTED_READ_EOF)
    cursor.advance()  # Looking at EOF alone is not full consumption in I-6.
    if not cursor.finish().complete:
        raise RuntimeError("Read full-consumption invariant failed.")

    instruction = ReadInstruction(
        target.lexeme, view,
        view.source_range(head_index, head_index + 1),
        view.source_range(target_index, target_index + 1),
        view.source_range(head_index, instruction_end),
        view.source_range(0, len(view.items) - 1),
    )
    return ReadParseResult(PARSED, instruction, (), preparation, profile_outcome)


def parse_read_unit(lexical_result: object) -> ReadParseResult:
    """Parse one exact I-5 result through I-6; never resolve or observe a target.

I-4/I-5 stops keep their outcome, reason codes, and locations. Malformed host
carriers remain I-6 input/host failures, not newly invented syntax failures.
There is no prefix success, recovery, repair, or implicit empty instruction.
"""
    preparation = syntax.prepare_syntax_input(lexical_result)
    profile_outcome = None
    if preparation.outcome in (syntax.PREPARED, syntax.UPSTREAM_STOPPED):
        # I-6 has now checked the exact carrier and its outcome field types.
        profile_outcome = lexical_result.source_profile_outcome
    if preparation.outcome != syntax.PREPARED:
        outcome = (preparation.upstream_outcome
                   if preparation.outcome == syntax.UPSTREAM_STOPPED
                   else preparation.outcome)
        return ReadParseResult(outcome, None, preparation.reasons,
                               preparation, profile_outcome)
    try:
        return _parse_prepared(preparation, profile_outcome)
    except MemoryError:
        # Diagnostic allocation may itself fail catastrophically; then stop.
        return ReadParseResult(HOST_FAILED, None, (ReadReason(RESOURCE_EXHAUSTED),),
                               preparation, profile_outcome)


def _valid_label(label: object) -> bool:
    # Do not invoke conversion, Unicode identifier policy, or subclass hooks.
    if type(label) is not str or not label:
        return False
    first = label[0]
    if not ("A" <= first <= "Z" or "a" <= first <= "z" or first == "_"):
        return False
    return all("A" <= c <= "Z" or "a" <= c <= "z"
               or "0" <= c <= "9" or c == "_" for c in label)


def observe_read_unit(source_text: object, *, target_name: object = None,
                      target_value: object = None) -> ReadObservationResult:
    """Observe one supplied, already-admitted textus under its exact label.

Order: lex source once, parse completely, check label shape and exact agreement,
then call accepted I-2 leg once. Missing names diagnose; unsupported or missing
values after name agreement use I-2's unchanged failure. No previous invocation
can supply a fallback name/value, and no payload is passed into the frontend.
The returned I-2 observation (including its diagnostic on failure) is retained
unchanged; read reasons also expose that diagnostic's exact reason identity.
"""
    parsed = parse_read_unit(lexical.lex_source(source_text))
    if not parsed.succeeded:
        return ReadObservationResult(parsed.outcome, parsed, parsed.reasons, None)
    instruction = parsed.instruction
    if instruction is None:
        raise RuntimeError("Successful read-parse invariant failed.")
    try:
        if not _valid_label(target_name):
            return ReadObservationResult(TARGET_REJECTED, parsed,
                                         (ReadReason(INVALID_TARGET_LABEL),), None)
        if target_name != instruction.target_name:
            return ReadObservationResult(
                TARGET_REJECTED, parsed,
                (ReadReason(TARGET_NAME_MISMATCH, instruction.target_range.span),), None)
        observation = runtime.leg(target_value)
        reasons = (() if observation.diagnostic is None else
                   (ReadReason(observation.diagnostic.reason),))
        return ReadObservationResult(observation.outcome, parsed, reasons, observation)
    except MemoryError:
        # Never return a partial payload or recategorize a host stop as FALSE/0.
        return ReadObservationResult(HOST_FAILED, parsed,
                                     (ReadReason(RESOURCE_EXHAUSTED),), None)


__all__ = (
    "parse_read_unit", "observe_read_unit", "ReadInstruction", "ReadReason",
    "ReadParseResult", "ReadObservationResult", "PROFILE_ID",
)
