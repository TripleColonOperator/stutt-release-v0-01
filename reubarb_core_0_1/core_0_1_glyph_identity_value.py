"""I-16: inert immutable value for one recognized standalone native glyph.

This bounded layer connects the accepted I-15 source observation to a host
carrier that identifies one approved G2--G6 glyph.  The Python class name and
fields are host instrumentation, not adopted Reubarb spellings.

The value carries no fulfillment claim, pair, RECON operation, authorization,
state transition, evaluation, execution, persistence, or physical effect.
"""
from __future__ import annotations

from dataclasses import InitVar, dataclass
from typing import Final

import core_0_1_glyph_encoding as glyph_encoding
import core_0_1_glyph_recognizer as glyph_recognizer
import core_0_1_glyph_source_integration as glyph_source

PROFILE_ID: Final[str] = "gart-inert-glyph-identity-value-i16-0.1"
VALUE_AVAILABLE: Final[str] = "value-available"
NO_VALUE: Final[str] = "no-value"
HOST_FAILED: Final[str] = "host-failed"
GLYPH_IDENTITY_INVARIANT_FAILURE: Final[str] = (
    "GART.CORE_0_1.HOST.GLYPH_IDENTITY_INVARIANT_FAILURE"
)
RESOURCE_EXHAUSTED: Final[str] = "GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED"

_SEAL: Final[object] = object()


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class GlyphIdentityValue:
    """Opaque-sealed host carrier identifying one approved glyph geometry.

    Frozen host fields do not make this value an immutable fact and establish
    no target equality, copying, allocation, reference, or lifetime behavior.
    """

    design_id: int
    code_point_label: str
    _construction_seal: InitVar[object]

    def __post_init__(self, _construction_seal: object) -> None:
        if (
            _construction_seal is not _SEAL
            or type(self.design_id) is not int
            or type(self.code_point_label) is not str
        ):
            raise ValueError("invalid host glyph-identity carrier")
        mapping = glyph_encoding.get_encoding_by_design_id(self.design_id)
        if (
            type(mapping) is not glyph_encoding.GlyphEncoding
            or type(mapping.design_id) is not int
            or type(mapping.scalar) is not str
            or type(mapping.code_point_label) is not str
            or mapping.design_id != self.design_id
            or self.code_point_label != mapping.code_point_label
        ):
            raise ValueError("invalid host glyph-identity carrier")

    def __repr__(self) -> str:
        return (
            "GlyphIdentityValue("
            f"design_id={self.design_id!r}, "
            f"code_point_label={self.code_point_label!r})"
        )


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class GlyphIdentityResult:
    """Result with a source-redacted repr and complete preceding observation."""

    outcome: str
    value: GlyphIdentityValue | None
    source_observation: glyph_source.GlyphSourceObservationResult
    reasons: tuple[glyph_source.GlyphSourceReason, ...]

    def __post_init__(self) -> None:
        if (
            type(self.outcome) is not str
            or type(self.source_observation)
            is not glyph_source.GlyphSourceObservationResult
            or type(self.reasons) is not tuple
            or any(type(reason) is not glyph_source.GlyphSourceReason
                   for reason in self.reasons)
        ):
            raise ValueError("invalid host glyph-identity result")

        nested = self.source_observation.observation
        if self.outcome == VALUE_AVAILABLE:
            if (
                type(self.value) is not GlyphIdentityValue
                or self.reasons
                or self.source_observation.outcome != glyph_source.OBSERVED
                or nested is None
                or nested.outcome
                != glyph_recognizer.RecognitionOutcome.RECOGNIZED.value
                or self.value.design_id != nested.design_id
                or self.value.code_point_label != nested.code_point_label
            ):
                raise ValueError("invalid successful glyph-identity result")
            return

        if self.value is not None:
            raise ValueError("a stopped glyph-identity result cannot carry a value")
        if self.outcome == NO_VALUE:
            if (
                self.source_observation.outcome != glyph_source.OBSERVED
                or nested is None
                or nested.outcome
                != glyph_recognizer.RecognitionOutcome.UNRECOGNIZED.value
            ):
                raise ValueError("invalid unrecognized glyph-identity result")
            return
        if self.outcome == HOST_FAILED:
            if (
                len(self.reasons) != 1
                or self.reasons[0].code not in (
                    GLYPH_IDENTITY_INVARIANT_FAILURE,
                    RESOURCE_EXHAUSTED,
                )
            ):
                raise ValueError("invalid failed glyph-identity result")
            return
        if (
            self.source_observation.outcome == glyph_source.OBSERVED
            or self.outcome != self.source_observation.outcome
            or self.reasons != self.source_observation.reasons
        ):
            raise ValueError("invalid upstream-stopped glyph-identity result")

    @property
    def succeeded(self) -> bool:
        return self.outcome == VALUE_AVAILABLE

    def __repr__(self) -> str:
        return (
            f"GlyphIdentityResult(outcome={self.outcome!r}, "
            f"value={self.value!r}, source=<omitted>, "
            f"reason_count={len(self.reasons)})"
        )


def _construct_glyph_identity(
    design_id: int, code_point_label: str
) -> GlyphIdentityValue:
    """Guarded allocation boundary used by the finite I-16 checks."""

    return GlyphIdentityValue(design_id, code_point_label, _SEAL)


def _host_failure(
    observation: glyph_source.GlyphSourceObservationResult, reason: str
) -> GlyphIdentityResult:
    return GlyphIdentityResult(
        HOST_FAILED,
        None,
        observation,
        (glyph_source.GlyphSourceReason(reason),),
    )


def form_glyph_identity_value(source_text: object) -> GlyphIdentityResult:
    """Form only an inert identity value from one recognized I-15 candidate."""

    observed = glyph_source.observe_glyph_source_candidate(source_text)
    if observed.outcome != glyph_source.OBSERVED:
        return GlyphIdentityResult(
            observed.outcome, None, observed, observed.reasons
        )

    candidate = observed.observation
    if candidate is None:
        return _host_failure(observed, GLYPH_IDENTITY_INVARIANT_FAILURE)
    if candidate.outcome == glyph_recognizer.RecognitionOutcome.UNRECOGNIZED.value:
        return GlyphIdentityResult(NO_VALUE, None, observed, observed.reasons)
    if candidate.outcome != glyph_recognizer.RecognitionOutcome.RECOGNIZED.value:
        return _host_failure(observed, GLYPH_IDENTITY_INVARIANT_FAILURE)

    if (
        type(candidate.design_id) is not int
        or type(candidate.code_point_label) is not str
        or type(candidate.candidate) is not str
    ):
        return _host_failure(observed, GLYPH_IDENTITY_INVARIANT_FAILURE)

    mapping = glyph_encoding.get_encoding_by_design_id(candidate.design_id)
    if (
        type(mapping) is not glyph_encoding.GlyphEncoding
        or type(mapping.design_id) is not int
        or type(mapping.scalar) is not str
        or type(mapping.code_point_label) is not str
        or mapping.design_id != candidate.design_id
        or candidate.candidate != mapping.scalar
        or candidate.code_point_label != mapping.code_point_label
    ):
        return _host_failure(observed, GLYPH_IDENTITY_INVARIANT_FAILURE)

    try:
        value = _construct_glyph_identity(
            mapping.design_id, mapping.code_point_label
        )
        return GlyphIdentityResult(VALUE_AVAILABLE, value, observed, ())
    except MemoryError:
        return _host_failure(observed, RESOURCE_EXHAUSTED)


__all__ = (
    "form_glyph_identity_value",
    "GlyphIdentityValue",
    "GlyphIdentityResult",
    "PROFILE_ID",
    "VALUE_AVAILABLE",
    "NO_VALUE",
    "HOST_FAILED",
    "GLYPH_IDENTITY_INVARIANT_FAILURE",
    "RESOURCE_EXHAUSTED",
)
