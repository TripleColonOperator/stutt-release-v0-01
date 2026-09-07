"""Reubarb Pi Early Core 0.1 — bounded reviewed-transcript runtime component.

This module implements only the approved Package I-2 host reference boundary:

    transcriptio(payload, *, reviewed=False, accepted=False) -> AdmissionResult
    leg(value) -> ObservationResult

It does not tokenize, parse, normalize, interpret, authorize, evaluate, execute,
persist, transmit, display, or log transcript payloads. Python is only the host.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


MAX_TRANSCRIPT_SCALARS: Final[int] = 65_536

ADMITTED: Final[str] = "admitted"
REJECTED: Final[str] = "rejected"
LIMITED: Final[str] = "limited"
HOST_FAILED: Final[str] = "host-failed"
OBSERVED: Final[str] = "observed"

INVALID_REVIEW_STATE: Final[str] = (
    "GART.CORE_0_1.TRANSCRIPT.INVALID_REVIEW_STATE"
)
REVIEW_REQUIRED: Final[str] = "GART.CORE_0_1.TRANSCRIPT.REVIEW_REQUIRED"
ACCEPTANCE_REQUIRED: Final[str] = (
    "GART.CORE_0_1.TRANSCRIPT.ACCEPTANCE_REQUIRED"
)
EXPECTED_TEXT: Final[str] = "GART.CORE_0_1.TRANSCRIPT.EXPECTED_TEXT"
NON_SCALAR_CONTENT: Final[str] = (
    "GART.CORE_0_1.TRANSCRIPT.NON_SCALAR_CONTENT"
)
TRANSCRIPT_LIMIT: Final[str] = "GART.CORE_0_1.RESOURCE.TRANSCRIPT_LIMIT"
EXPECTED_TEXTUS: Final[str] = "GART.CORE_0_1.TRANSCRIPT.EXPECTED_TEXTUS"
RESOURCE_EXHAUSTED: Final[str] = "GART.CORE_0_1.HOST.RESOURCE_EXHAUSTED"
TRANSCRIPT_INVARIANT_FAILURE: Final[str] = (
    "GART.CORE_0_1.HOST.TRANSCRIPT_INVARIANT_FAILURE"
)


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class Diagnostic:
    """Payload-free host diagnostic record."""

    operation: str
    reason: str

    def __repr__(self) -> str:
        return f"Diagnostic(operation={self.operation!r}, reason={self.reason!r})"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class textus:
    """Dedicated host carrier for one accepted reviewed transcript.

    Construction is intentionally private-by-convention. Supported creation is
    through transcriptio(). The private field is not a Reubarb string API.
    """

    _payload: str
    _seal: object

    def __repr__(self) -> str:
        return "textus(<opaque>)"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class AdmissionResult:
    """Host result for transcriptio; never includes transcript text in repr."""

    outcome: str
    value: textus | None
    diagnostic: Diagnostic | None

    def __repr__(self) -> str:
        return (
            f"AdmissionResult(outcome={self.outcome!r}, "
            f"value={'textus(<opaque>)' if self.value is not None else None}, "
            f"diagnostic={self.diagnostic!r})"
        )


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class ObservationResult:
    """Host result for leg; repr never includes observed transcript text."""

    outcome: str
    payload: str | None
    diagnostic: Diagnostic | None

    def __repr__(self) -> str:
        return (
            f"ObservationResult(outcome={self.outcome!r}, "
            f"payload={'<opaque>' if self.payload is not None else None!r}, "
            f"diagnostic={self.diagnostic!r})"
        )


@dataclass(frozen=True, slots=True)
class Binding:
    """Host metadata recording the three explicitly approved spellings."""

    spelling: str
    role: str


BINDINGS: Final[tuple[Binding, ...]] = (
    Binding("textus", "reviewed-transcript runtime type"),
    Binding("transcriptio", "reviewed-transcript admission operation"),
    Binding("leg", "whole-transcript exact observation operation"),
)

_SEAL: Final[object] = object()


def _diagnostic(operation: str, reason: str) -> Diagnostic:
    return Diagnostic(operation=operation, reason=reason)


def _admission_failure(outcome: str, reason: str) -> AdmissionResult:
    return AdmissionResult(
        outcome=outcome,
        value=None,
        diagnostic=_diagnostic("transcriptio", reason),
    )


def _observation_failure(reason: str) -> ObservationResult:
    return ObservationResult(
        outcome=REJECTED,
        payload=None,
        diagnostic=_diagnostic("leg", reason),
    )


def _contains_non_scalar(payload: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in payload)


def _construct_textus(payload: str) -> textus:
    """Guarded construction boundary; patchable by the finite test suite."""

    return textus(_payload=payload, _seal=_SEAL)


def _make_observation(payload: str) -> ObservationResult:
    """Guarded observation-result boundary; patchable by the finite test suite."""

    return ObservationResult(outcome=OBSERVED, payload=payload, diagnostic=None)


def transcriptio(
    payload: object,
    *,
    reviewed: bool = False,
    accepted: bool = False,
) -> AdmissionResult:
    """Admit one already-reviewed and explicitly accepted exact text payload."""

    if type(reviewed) is not bool or type(accepted) is not bool:
        return _admission_failure(REJECTED, INVALID_REVIEW_STATE)
    if not reviewed:
        return _admission_failure(REJECTED, REVIEW_REQUIRED)
    if not accepted:
        return _admission_failure(REJECTED, ACCEPTANCE_REQUIRED)
    if type(payload) is not str:
        return _admission_failure(REJECTED, EXPECTED_TEXT)
    if len(payload) > MAX_TRANSCRIPT_SCALARS:
        return _admission_failure(LIMITED, TRANSCRIPT_LIMIT)
    if _contains_non_scalar(payload):
        return _admission_failure(REJECTED, NON_SCALAR_CONTENT)

    try:
        carrier = _construct_textus(payload)
        return AdmissionResult(outcome=ADMITTED, value=carrier, diagnostic=None)
    except MemoryError:
        return _admission_failure(HOST_FAILED, RESOURCE_EXHAUSTED)


def leg(value: object) -> ObservationResult:
    """Observe one exact textus payload without interpreting or consuming it."""

    if type(value) is not textus:
        return _observation_failure(EXPECTED_TEXTUS)

    if value._seal is not _SEAL or type(value._payload) is not str:
        return ObservationResult(
            outcome=HOST_FAILED,
            payload=None,
            diagnostic=_diagnostic("leg", TRANSCRIPT_INVARIANT_FAILURE),
        )

    try:
        return _make_observation(value._payload)
    except MemoryError:
        return ObservationResult(
            outcome=HOST_FAILED,
            payload=None,
            diagnostic=_diagnostic("leg", RESOURCE_EXHAUSTED),
        )


__all__ = (
    "AdmissionResult",
    "Binding",
    "BINDINGS",
    "Diagnostic",
    "MAX_TRANSCRIPT_SCALARS",
    "ObservationResult",
    "leg",
    "textus",
    "transcriptio",
)
