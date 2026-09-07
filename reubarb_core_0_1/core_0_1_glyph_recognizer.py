"""I-11 exact, non-executable recognizer for one separated glyph candidate.

The recognizer consumes an already-decoded host string.  It performs no byte
decoding, splitting, trimming, normalization, case repair, glyph inference,
nomination, persistence, parsing, evaluation, or execution.  Recognition uses
only the approved I-10 scalar mappings.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import core_0_1_glyph_encoding as i10


class RecognitionOutcome(str, Enum):
    """The three confirmed external Core 0.1 candidate outcomes."""

    RECOGNIZED = "RECOGNIZED"
    UNRECOGNIZED = "UNRECOGNIZED"
    INVALID_INPUT = "INVALID_INPUT"


class CandidateLimitError(ValueError):
    """Host processing limit; deliberately not a recognition outcome."""


@dataclass(frozen=True, slots=True)
class GlyphRecognitionObservation:
    """Source-free observation for one handled candidate submission."""

    outcome: RecognitionOutcome
    design_id: int | None = None
    code_point_label: str | None = None

    def __post_init__(self) -> None:
        has_mapping = self.design_id is not None or self.code_point_label is not None
        if self.outcome is RecognitionOutcome.RECOGNIZED:
            if type(self.design_id) is not int or type(self.code_point_label) is not str:
                raise ValueError("a recognized observation requires exact mapping metadata")
        elif has_mapping:
            raise ValueError("an unrecognized or invalid observation cannot carry a mapping")

    @property
    def nomination_eligible(self) -> bool:
        """Only an unrecognized candidate may enter a separate nomination gate."""
        return self.outcome is RecognitionOutcome.UNRECOGNIZED


MAX_CANDIDATE_SCALARS = 65_536

_ENCODING_BY_SCALAR = {
    item.scalar: item for item in i10.APPROVED_GLYPH_ENCODINGS
}


def recognize_glyph_candidate(candidate: str) -> GlyphRecognitionObservation:
    """Classify one exact already-separated decoded-scalar candidate."""
    if type(candidate) is not str:
        raise TypeError("candidate must be an exact built-in string")
    if len(candidate) > MAX_CANDIDATE_SCALARS:
        raise CandidateLimitError("candidate exceeds the bounded host profile")
    if not candidate or any(0xD800 <= ord(scalar) <= 0xDFFF for scalar in candidate):
        return GlyphRecognitionObservation(RecognitionOutcome.INVALID_INPUT)

    mapping = _ENCODING_BY_SCALAR.get(candidate)
    if mapping is None:
        return GlyphRecognitionObservation(RecognitionOutcome.UNRECOGNIZED)
    return GlyphRecognitionObservation(
        RecognitionOutcome.RECOGNIZED,
        design_id=mapping.design_id,
        code_point_label=mapping.code_point_label,
    )


__all__ = (
    "RecognitionOutcome",
    "CandidateLimitError",
    "GlyphRecognitionObservation",
    "MAX_CANDIDATE_SCALARS",
    "recognize_glyph_candidate",
)
