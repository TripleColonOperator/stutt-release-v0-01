"""I-18: inert same-occurrence continuity assessment.

This bounded host layer reduces five already-established observations.  It does
not compare or create target identities.  The observations are injected host
premises, not proof that an entity, need, or boundary is actually unchanged or
that fulfillment or closure is actually absent.

Only three UNCHANGED anchor observations together with explicit ABSENT
fulfillment and closure observations produce SAME_OCCURRENCE.  Every other
well-formed combination stops classification.  The layer never creates a new
occurrence, invokes Source, retries, records an attempt, changes state, or
performs fulfillment, closure, authorization, persistence, or execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Final


PROFILE_ID: Final[str] = "gart-occurrence-continuity-i18-0.1"
SAME_OCCURRENCE: Final[str] = "same-occurrence"
CLASSIFICATION_STOPPED: Final[str] = "classification-stopped"

ENTITY_ANCHOR_DIFFERENT: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.ENTITY_ANCHOR_DIFFERENT"
)
ENTITY_ANCHOR_UNAVAILABLE: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.ENTITY_ANCHOR_UNAVAILABLE"
)
NEED_ANCHOR_DIFFERENT: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.NEED_ANCHOR_DIFFERENT"
)
NEED_ANCHOR_UNAVAILABLE: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.NEED_ANCHOR_UNAVAILABLE"
)
BOUNDARY_ANCHOR_DIFFERENT: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.BOUNDARY_ANCHOR_DIFFERENT"
)
BOUNDARY_ANCHOR_UNAVAILABLE: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.BOUNDARY_ANCHOR_UNAVAILABLE"
)
INTERVENING_FULFILLMENT_PRESENT: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.INTERVENING_FULFILLMENT_PRESENT"
)
INTERVENING_FULFILLMENT_UNAVAILABLE: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.INTERVENING_FULFILLMENT_UNAVAILABLE"
)
EXPLICIT_CLOSURE_PRESENT: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.EXPLICIT_CLOSURE_PRESENT"
)
EXPLICIT_CLOSURE_UNAVAILABLE: Final[str] = (
    "GART.CORE_0_1.CONTINUITY.EXPLICIT_CLOSURE_UNAVAILABLE"
)

_ISSUE_ORDER: Final[tuple[str, ...]] = (
    ENTITY_ANCHOR_DIFFERENT,
    ENTITY_ANCHOR_UNAVAILABLE,
    NEED_ANCHOR_DIFFERENT,
    NEED_ANCHOR_UNAVAILABLE,
    BOUNDARY_ANCHOR_DIFFERENT,
    BOUNDARY_ANCHOR_UNAVAILABLE,
    INTERVENING_FULFILLMENT_PRESENT,
    INTERVENING_FULFILLMENT_UNAVAILABLE,
    EXPLICIT_CLOSURE_PRESENT,
    EXPLICIT_CLOSURE_UNAVAILABLE,
)

_MUTUALLY_EXCLUSIVE_ISSUE_GROUPS: Final[tuple[tuple[str, str], ...]] = (
    (ENTITY_ANCHOR_DIFFERENT, ENTITY_ANCHOR_UNAVAILABLE),
    (NEED_ANCHOR_DIFFERENT, NEED_ANCHOR_UNAVAILABLE),
    (BOUNDARY_ANCHOR_DIFFERENT, BOUNDARY_ANCHOR_UNAVAILABLE),
    (
        INTERVENING_FULFILLMENT_PRESENT,
        INTERVENING_FULFILLMENT_UNAVAILABLE,
    ),
    (EXPLICIT_CLOSURE_PRESENT, EXPLICIT_CLOSURE_UNAVAILABLE),
)


class AnchorObservation(Enum):
    """Host premise about one already-established identity anchor."""

    UNCHANGED = auto()
    DIFFERENT = auto()
    UNAVAILABLE = auto()


class EndObservation(Enum):
    """Host premise about an intervening occurrence-ending condition."""

    ABSENT = auto()
    PRESENT = auto()
    UNAVAILABLE = auto()


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class SameOccurrenceEvidence:
    """Five required host observations; not identity evidence or a target value."""

    entity_anchor: AnchorObservation
    unresolved_need_anchor: AnchorObservation
    authorized_boundary_anchor: AnchorObservation
    intervening_fulfillment: EndObservation
    explicit_closure: EndObservation

    def __post_init__(self) -> None:
        if (
            type(self.entity_anchor) is not AnchorObservation
            or type(self.unresolved_need_anchor) is not AnchorObservation
            or type(self.authorized_boundary_anchor) is not AnchorObservation
            or type(self.intervening_fulfillment) is not EndObservation
            or type(self.explicit_closure) is not EndObservation
        ):
            raise ValueError("invalid host same-occurrence evidence")

    def __repr__(self) -> str:
        return "SameOccurrenceEvidence(<host premises omitted>)"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class ContinuityIssue:
    """One source-free host diagnostic identity."""

    code: str

    def __post_init__(self) -> None:
        if type(self.code) is not str or self.code not in _ISSUE_ORDER:
            raise ValueError("invalid host continuity issue")

    def __repr__(self) -> str:
        return "ContinuityIssue(<diagnostic identity omitted>)"


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class SameOccurrenceAssessment:
    """Classification only; never an occurrence, transition, or Source action."""

    outcome: str
    issues: tuple[ContinuityIssue, ...]

    def __post_init__(self) -> None:
        if (
            type(self.outcome) is not str
            or type(self.issues) is not tuple
            or any(type(issue) is not ContinuityIssue for issue in self.issues)
        ):
            raise ValueError("invalid host same-occurrence assessment")
        codes = tuple(issue.code for issue in self.issues)
        if len(codes) != len(set(codes)):
            raise ValueError("duplicate host continuity issue")
        ordered = tuple(code for code in _ISSUE_ORDER if code in codes)
        if codes != ordered:
            raise ValueError("host continuity issues are out of order")
        if any(
            all(code in codes for code in alternatives)
            for alternatives in _MUTUALLY_EXCLUSIVE_ISSUE_GROUPS
        ):
            raise ValueError("contradictory host continuity issues")
        if self.outcome == SAME_OCCURRENCE:
            if self.issues:
                raise ValueError("same-occurrence assessment cannot carry issues")
            return
        if self.outcome == CLASSIFICATION_STOPPED:
            if not self.issues:
                raise ValueError("stopped continuity assessment requires an issue")
            return
        raise ValueError("unknown host continuity outcome")

    def __repr__(self) -> str:
        return (
            f"SameOccurrenceAssessment(outcome={self.outcome!r}, "
            f"issue_count={len(self.issues)})"
        )


def _anchor_issue(
    observation: AnchorObservation,
    different: str,
    unavailable: str,
) -> str | None:
    if observation is AnchorObservation.UNCHANGED:
        return None
    if observation is AnchorObservation.DIFFERENT:
        return different
    return unavailable


def _end_issue(
    observation: EndObservation,
    present: str,
    unavailable: str,
) -> str | None:
    if observation is EndObservation.ABSENT:
        return None
    if observation is EndObservation.PRESENT:
        return present
    return unavailable


def assess_same_occurrence(evidence: object) -> SameOccurrenceAssessment:
    """Reduce exact host premises without comparing target identities.

    DIFFERENT or UNAVAILABLE anchor premises require a later explicit Source
    decision under the accepted rule.  This function only stops classification;
    it does not request, queue, model, or perform that decision.
    """

    if type(evidence) is not SameOccurrenceEvidence:
        raise TypeError("expected exact SameOccurrenceEvidence host record")

    codes = tuple(
        code
        for code in (
            _anchor_issue(
                evidence.entity_anchor,
                ENTITY_ANCHOR_DIFFERENT,
                ENTITY_ANCHOR_UNAVAILABLE,
            ),
            _anchor_issue(
                evidence.unresolved_need_anchor,
                NEED_ANCHOR_DIFFERENT,
                NEED_ANCHOR_UNAVAILABLE,
            ),
            _anchor_issue(
                evidence.authorized_boundary_anchor,
                BOUNDARY_ANCHOR_DIFFERENT,
                BOUNDARY_ANCHOR_UNAVAILABLE,
            ),
            _end_issue(
                evidence.intervening_fulfillment,
                INTERVENING_FULFILLMENT_PRESENT,
                INTERVENING_FULFILLMENT_UNAVAILABLE,
            ),
            _end_issue(
                evidence.explicit_closure,
                EXPLICIT_CLOSURE_PRESENT,
                EXPLICIT_CLOSURE_UNAVAILABLE,
            ),
        )
        if code is not None
    )
    if not codes:
        return SameOccurrenceAssessment(SAME_OCCURRENCE, ())
    return SameOccurrenceAssessment(
        CLASSIFICATION_STOPPED,
        tuple(ContinuityIssue(code) for code in codes),
    )


__all__ = (
    "assess_same_occurrence",
    "SameOccurrenceEvidence",
    "SameOccurrenceAssessment",
    "ContinuityIssue",
    "AnchorObservation",
    "EndObservation",
    "PROFILE_ID",
    "SAME_OCCURRENCE",
    "CLASSIFICATION_STOPPED",
    "ENTITY_ANCHOR_DIFFERENT",
    "ENTITY_ANCHOR_UNAVAILABLE",
    "NEED_ANCHOR_DIFFERENT",
    "NEED_ANCHOR_UNAVAILABLE",
    "BOUNDARY_ANCHOR_DIFFERENT",
    "BOUNDARY_ANCHOR_UNAVAILABLE",
    "INTERVENING_FULFILLMENT_PRESENT",
    "INTERVENING_FULFILLMENT_UNAVAILABLE",
    "EXPLICIT_CLOSURE_PRESENT",
    "EXPLICIT_CLOSURE_UNAVAILABLE",
)
