"""I-4: bounded inspection of the approved source profile, not program validity.

Input is explicitly supplied decoded source text, never a textus carrier.
Only SPACE/TAB, LF/CRLF, // comments, and opaque ASCII word-like content
have sufficient context for this first inspector. Unsupported syntax returns
context-required, not a guessed source-language error or success. Unconditional
source-control checks continue even when lexical context is unresolved.

No file loading, normalization, rendering, registry dispatch, source execution,
transcript admission, JSON serialization, network, or persistence occurs here.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Final

PROFILE_ID: Final[str] = "gart-source-profile-inspector-i4-0.1"
UNICODE_DATA_VERSION: Final[str] = "17.0.0"
MAX_SOURCE_CODE_POINTS: Final[int] = 65_536
MAX_SOURCE_DIAGNOSTICS: Final[int] = 128

PROFILE_CHECKED: Final[str] = "profile-checked"
PROFILE_REJECTED: Final[str] = "profile-rejected"
CONTEXT_REQUIRED: Final[str] = "context-required"
INPUT_REJECTED: Final[str] = "input-rejected"
LIMITED: Final[str] = "limited"
HOST_FAILED: Final[str] = "host-failed"

EXPECTED_DECODED_TEXT: Final[str] = "GART.CORE_0_1.SOURCE.EXPECTED_DECODED_TEXT"
NON_SCALAR_INPUT: Final[str] = "GART.CORE_0_1.SOURCE.NON_SCALAR_INPUT"
FORBIDDEN_CONTROL: Final[str] = "GART.CORE_0_1.SOURCE.FORBIDDEN_CONTROL"
UNSUPPORTED_LINE_BREAK: Final[str] = "GART.CORE_0_1.SOURCE.UNSUPPORTED_LINE_BREAK"
FEFF_FORBIDDEN: Final[str] = "GART.CORE_0_1.SOURCE.FEFF_FORBIDDEN"
BIDI_CONTROL_FORBIDDEN: Final[str] = "GART.CORE_0_1.SOURCE.BIDI_CONTROL_FORBIDDEN"
COMMENT_ONLY_CHARACTER: Final[str] = "GART.CORE_0_1.SOURCE.COMMENT_ONLY_CHARACTER"
LEXICAL_CONTEXT_REQUIRED: Final[str] = "GART.CORE_0_1.SOURCE.LEXICAL_CONTEXT_REQUIRED"
SOURCE_PROFILE_LIMIT: Final[str] = "GART.CORE_0_1.RESOURCE.SOURCE_PROFILE_LIMIT"
SOURCE_DIAGNOSTIC_LIMIT: Final[str] = "GART.CORE_0_1.RESOURCE.SOURCE_DIAGNOSTIC_LIMIT"
RESOURCE_EXHAUSTED: Final[str] = "GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED"

# Adjacent intervals merged without changing membership. Exactly 4,174 points.
# Source: Unicode 17.0.0 DerivedCoreProperties.txt, Default_Ignorable_Code_Point.
# https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt
# No ambient Python Unicode database and no runtime download is used.
DEFAULT_IGNORABLE_RANGES: Final[tuple[tuple[int, int], ...]] = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C),
    (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180F),
    (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F),
    (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF),
)

# Unicode data notice (applies to the derived property data above):
# UNICODE LICENSE V3
# COPYRIGHT AND PERMISSION NOTICE
# Copyright © 1991-2026 Unicode, Inc.
# NOTICE TO USER: Carefully read the following legal agreement. BY
# DOWNLOADING, INSTALLING, COPYING OR OTHERWISE USING DATA FILES, AND/OR
# SOFTWARE, YOU UNEQUIVOCALLY ACCEPT, AND AGREE TO BE BOUND BY, ALL OF THE
# TERMS AND CONDITIONS OF THIS AGREEMENT. IF YOU DO NOT AGREE, DO NOT
# DOWNLOAD, INSTALL, COPY, DISTRIBUTE OR USE THE DATA FILES OR SOFTWARE.
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of data files and any associated documentation (the "Data Files") or
# software and any associated documentation (the "Software") to deal in the
# Data Files or Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, and/or sell
# copies of the Data Files or Software, and to permit persons to whom the
# Data Files or Software are furnished to do so, provided that either (a)
# this copyright and permission notice appear with all copies of the Data
# Files or Software, or (b) this copyright and permission notice appear in
# associated Documentation.
# THE DATA FILES AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF
# THIRD PARTY RIGHTS.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS NOTICE
# BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL DAMAGES,
# OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
# ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THE DATA
# FILES OR SOFTWARE.
# Except as contained in this notice, the name of a copyright holder shall
# not be used in advertising or otherwise to promote the sale, use or other
# dealings in these Data Files or Software without prior written
# authorization of the copyright holder.


@dataclass(frozen=True, slots=True)
class SourcePosition:
    """Host coordinates: zero-based scalar offset, one-based line and column."""
    offset: int
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class ScalarSpan:
    """Half-open scalar span. This is a diagnostic record, not a runtime value."""
    start_offset: int
    end_offset: int
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    unit: str = field(default="UNICODE_SCALAR", init=False)


@dataclass(frozen=True, slots=True)
class ProfileReason:
    code: str
    location: ScalarSpan | None = None


@dataclass(frozen=True, slots=True)
class LineBreak:
    kind: str  # Host spelling LF or CRLF, not a target token.
    span: ScalarSpan


def _position(line_starts: tuple[int, ...], offset: int) -> SourcePosition:
    row = bisect_right(line_starts, offset) - 1
    return SourcePosition(offset, row + 1, offset - line_starts[row] + 1)


def _span(line_starts: tuple[int, ...], start: int, end: int) -> ScalarSpan:
    first, last = _position(line_starts, start), _position(line_starts, end)
    return ScalarSpan(start, end, first.line, first.column, last.line, last.column)


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class SourceMap:
    """Exact, bounded source plus spans, released only on profile success.

    The source is retained in memory for explicit inspection and span slicing.
    It is never placed in ordinary repr output or implicitly observed as textus.
    Host immutability does not protect against hostile code in the same process.
    """
    source_text: str
    line_starts: tuple[int, ...]
    comments: tuple[ScalarSpan, ...]
    horizontal_whitespace: tuple[ScalarSpan, ...]
    line_breaks: tuple[LineBreak, ...]

    @property
    def scalar_length(self) -> int:
        return len(self.source_text)

    @property
    def end_of_input(self) -> SourcePosition:
        return self.position(self.scalar_length)

    def position(self, offset: int) -> SourcePosition:
        if type(offset) is not int:
            raise TypeError("A source offset must be an exact host integer.")
        if not 0 <= offset <= self.scalar_length:
            raise ValueError("Source offset is outside the inspected boundary.")
        return _position(self.line_starts, offset)

    def __repr__(self) -> str:
        return "SourceMap(<source omitted>)"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class SourceProfileResult:
    outcome: str
    source_map: SourceMap | None
    reasons: tuple[ProfileReason, ...]
    checks_complete: bool

    @property
    def succeeded(self) -> bool:
        # Success concerns this profile inspection only, never valid-program status.
        return self.outcome == PROFILE_CHECKED

    def __repr__(self) -> str:
        return (
            f"SourceProfileResult(outcome={self.outcome!r}, "
            f"checks_complete={self.checks_complete!r}, "
            f"reason_count={len(self.reasons)}, source=<omitted>)"
        )


def _failure(outcome: str, code: str) -> SourceProfileResult:
    return SourceProfileResult(outcome, None, (ProfileReason(code),), False)


def _global_violation(source: str, index: int) -> str | None:
    point = ord(source[index])
    if point == 0x0D:
        return None if source.startswith("\r\n", index) else UNSUPPORTED_LINE_BREAK
    if point in (0x0B, 0x0C, 0x85, 0x2028, 0x2029):
        return UNSUPPORTED_LINE_BREAK
    if (point < 0x20 and point not in (0x09, 0x0A)) or 0x80 <= point <= 0x9F:
        return FORBIDDEN_CONTROL
    if point == 0xFEFF:
        return FEFF_FORBIDDEN
    if 0x202A <= point <= 0x202E or 0x2066 <= point <= 0x2069:
        return BIDI_CONTROL_FORBIDDEN
    return None


def _comment_only(point: int) -> bool:
    return any(start <= point <= end for start, end in DEFAULT_IGNORABLE_RANGES)


def _ascii_word_content(character: str) -> bool:
    # This does not bound or classify a token, identifier, integer, or atom.
    return ("A" <= character <= "Z" or "a" <= character <= "z"
            or "0" <= character <= "9" or character == "_")


def _reason_order(reason: ProfileReason) -> tuple[int, int, int, str]:
    location = reason.location
    if location is None:
        return (1, 0, 0, reason.code)
    return (0, location.start_offset, location.end_offset, reason.code)


def _make_source_map(source: str, starts: tuple[int, ...],
                     comments: list[ScalarSpan], whitespace: list[ScalarSpan],
                     breaks: list[LineBreak]) -> SourceMap:
    """Private allocation boundary; isolated by a finite host-failure test."""
    return SourceMap(source, starts, tuple(comments), tuple(whitespace), tuple(breaks))


def _inspect(source: str) -> SourceProfileResult:
    if len(source) > MAX_SOURCE_CODE_POINTS:
        return _failure(LIMITED, SOURCE_PROFILE_LIMIT)
    if any(0xD800 <= ord(character) <= 0xDFFF for character in source):
        # No scalar coordinates are asserted for a non-scalar host string.
        return _failure(INPUT_REJECTED, NON_SCALAR_INPUT)

    # A line starts after LF, including when LF is the second scalar of CRLF.
    # The position between CR and LF remains on the preceding line; no offset
    # is collapsed and both scalar boundaries remain individually addressable.
    starts = (0,) + tuple(i + 1 for i, char in enumerate(source) if char == "\n")
    comments: list[ScalarSpan] = []
    whitespace: list[ScalarSpan] = []
    breaks: list[LineBreak] = []
    reasons: list[ProfileReason] = []
    identities: set[tuple[str, int, int]] = set()
    unresolved = False
    found_violation = False
    diagnostic_limit = False
    comment_start: int | None = None
    index, length = 0, len(source)

    def add_reason(code: str, at: int) -> bool:
        identity = (code, at, at + 1)
        if identity in identities:
            return True
        if len(reasons) >= MAX_SOURCE_DIAGNOSTICS:
            return False
        identities.add(identity)
        reasons.append(ProfileReason(code, _span(starts, at, at + 1)))
        return True

    while index < length:
        character = source[index]
        violation = _global_violation(source, index)
        if violation is not None:
            found_violation = True
            if not add_reason(violation, index):
                diagnostic_limit = True
                break
            # Forbidden line-looking characters never end a line or a comment.
            index += 1
            continue

        if character == "\n" or source.startswith("\r\n", index):
            width = 1 if character == "\n" else 2
            if comment_start is not None:
                comments.append(_span(starts, comment_start, index))
                comment_start = None
            breaks.append(LineBreak("LF" if width == 1 else "CRLF",
                                    _span(starts, index, index + width)))
            index += width
            continue

        if unresolved or comment_start is not None:
            index += 1
            continue
        if character in (" ", "\t"):
            end = index + 1
            while end < length and source[end] in (" ", "\t"):
                end += 1
            whitespace.append(_span(starts, index, end))
            index = end
            continue
        if source.startswith("//", index):
            comment_start = index
            index += 2
            continue
        if _comment_only(ord(character)):
            found_violation = True
            if not add_reason(COMMENT_ONLY_CHARACTER, index):
                diagnostic_limit = True
                break
        elif not _ascii_word_content(character):
            # Unknown syntax could delimit a literal or another lexical form.
            # Do not infer comments anywhere after that unresolved boundary.
            unresolved = True
            if not add_reason(LEXICAL_CONTEXT_REQUIRED, index):
                diagnostic_limit = True
                break
        index += 1

    if diagnostic_limit:
        # At most 128 source reasons, plus one explicit host-limit reason.
        reasons.append(ProfileReason(SOURCE_DIAGNOSTIC_LIMIT))
        return SourceProfileResult(LIMITED, None,
                                   tuple(sorted(reasons, key=_reason_order)), False)

    if comment_start is not None:
        comments.append(_span(starts, comment_start, length))
    ordered = tuple(sorted(reasons, key=_reason_order))
    if found_violation:
        return SourceProfileResult(PROFILE_REJECTED, None, ordered, not unresolved)
    if unresolved:
        return SourceProfileResult(CONTEXT_REQUIRED, None, ordered, False)
    source_map = _make_source_map(source, starts, comments, whitespace, breaks)
    return SourceProfileResult(PROFILE_CHECKED, source_map, (), True)


def inspect_source_profile(source_text: object) -> SourceProfileResult:
    """Inspect explicitly supplied decoded source under the fixed I-4 profile.

    The caller retains responsibility for source-vs-data routing. This does
    not admit or observe transcripts, prove a valid program, or grant authority.
    A context-required result is not a rejection of a future language form.
    """
    if type(source_text) is not str:
        return _failure(INPUT_REJECTED, EXPECTED_DECODED_TEXT)
    try:
        return _inspect(source_text)
    except MemoryError:
        # If even this diagnostic cannot be allocated, propagate the host failure.
        # Never swallow unknown defects or cancellation, and never return success.
        return _failure(HOST_FAILED, RESOURCE_EXHAUSTED)


__all__ = (
    "inspect_source_profile", "SourceProfileResult", "SourceMap",
    "SourcePosition", "ScalarSpan", "ProfileReason", "LineBreak",
    "PROFILE_ID", "UNICODE_DATA_VERSION", "MAX_SOURCE_CODE_POINTS",
    "MAX_SOURCE_DIAGNOSTICS",
)
