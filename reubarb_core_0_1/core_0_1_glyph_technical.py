"""Host-only technical draft for V0.1 native-glyph geometry.

This module captures the approved shared frame and the centered Strong/Neutral/Weak
variant drafts as exact host data. It does not define syntax, Source authorization,
recognition mapping, scalar assignments, shortcut spelling, or runtime semantics.

The data in this module is intentionally narrow and reversible. It is a proposed
technical profile to support review and future parser/host integration.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class ProposalStatus(Enum):
    """Status of a proposed data element."""

    PROVISIONAL = auto()
    CONSTRUCTION_DRAFT = auto()


@dataclass(frozen=True, slots=True)
class Dot:
    """One approved shared-frame dot."""

    label: str
    x: int
    y: int
    radius: int


@dataclass(frozen=True, slots=True)
class SharedFrame:
    """Normalized 1000x1200 viewport and approved cross-frame dots."""

    width: int
    height: int
    dots: tuple[Dot, ...]


@dataclass(frozen=True, slots=True)
class GlyphVariant:
    """One centered variant draft for the Reversion/Dependence family."""

    design_id: int
    display_name: str
    frame: SharedFrame
    status: ProposalStatus
    center_kind: str
    center_path_cmds: tuple[str, ...]
    stroke_width: int


VIEW_WIDTH: int = 1000
VIEW_HEIGHT: int = 1200
STROKE_WIDTH: int = 30
DOT_RADIUS: int = 70
NORTH_DOT = Dot("north", 500, 150, DOT_RADIUS)
WEST_DOT = Dot("west", 220, 500, DOT_RADIUS)
EAST_DOT = Dot("east", 780, 500, DOT_RADIUS)
SOUTH_DOT = Dot("south", 500, 950, DOT_RADIUS)

APPROVED_SHARED_FRAME = SharedFrame(
    width=VIEW_WIDTH,
    height=VIEW_HEIGHT,
    dots=(NORTH_DOT, WEST_DOT, EAST_DOT, SOUTH_DOT),
)

CENTERED_VARIANTS: tuple[GlyphVariant, ...] = (
    GlyphVariant(
        design_id=4,
        display_name="Strong",
        frame=APPROVED_SHARED_FRAME,
        status=ProposalStatus.PROVISIONAL,
        center_kind="cross-plus",
        center_path_cmds=("M500 410V630", "M390 520H610"),
        stroke_width=STROKE_WIDTH,
    ),
    GlyphVariant(
        design_id=5,
        display_name="Neutral",
        frame=APPROVED_SHARED_FRAME,
        status=ProposalStatus.PROVISIONAL,
        center_kind="wave",
        center_path_cmds=("M360 535C405 455 455 615 500 535S595 455 640 535",),
        stroke_width=STROKE_WIDTH,
    ),
    GlyphVariant(
        design_id=6,
        display_name="Weak",
        frame=APPROVED_SHARED_FRAME,
        status=ProposalStatus.PROVISIONAL,
        center_kind="flatline",
        center_path_cmds=("M390 520H610",),
        stroke_width=STROKE_WIDTH,
    ),
)

CONSTRUCTION_DRAFT_FRAME = GlyphVariant(
    design_id=1,
    display_name="Centered construction-only frame",
    frame=APPROVED_SHARED_FRAME,
    status=ProposalStatus.CONSTRUCTION_DRAFT,
    center_kind="none",
    center_path_cmds=(),
    stroke_width=STROKE_WIDTH,
)

# The exact order and membership are part of this technical draft.
VARIANT_ORDER_BY_ID = (1, 4, 5, 6)
REVERSION_DEPENDENCE_VARIANT_IDS = tuple(variant.design_id for variant in CENTERED_VARIANTS)


def frame_dot_coordinates(frame: SharedFrame = APPROVED_SHARED_FRAME) -> tuple[tuple[int, int], ...]:
    """Return ordered frame-dot coordinates for deterministic review and tests."""
    return tuple((dot.x, dot.y) for dot in frame.dots)


def get_shared_frame() -> SharedFrame:
    """Return the host representation of the approved shared frame."""
    return APPROVED_SHARED_FRAME


def get_variant(design_id: int) -> GlyphVariant | None:
    """Return a centered draft variant or construction frame draft by design id."""
    if design_id == CONSTRUCTION_DRAFT_FRAME.design_id:
        return CONSTRUCTION_DRAFT_FRAME
    for variant in CENTERED_VARIANTS:
        if variant.design_id == design_id:
            return variant
    return None


def all_variants() -> tuple[GlyphVariant, ...]:
    """Return all known V0.1 variant drafts in review order."""
    return CENTERED_VARIANTS


__all__ = (
    "ProposalStatus",
    "Dot",
    "SharedFrame",
    "GlyphVariant",
    "VIEW_WIDTH",
    "VIEW_HEIGHT",
    "STROKE_WIDTH",
    "DOT_RADIUS",
    "NORTH_DOT",
    "WEST_DOT",
    "EAST_DOT",
    "SOUTH_DOT",
    "APPROVED_SHARED_FRAME",
    "CONSTRUCTION_DRAFT_FRAME",
    "CENTERED_VARIANTS",
    "frame_dot_coordinates",
    "get_shared_frame",
    "get_variant",
    "all_variants",
    "VARIANT_ORDER_BY_ID",
    "REVERSION_DEPENDENCE_VARIANT_IDS",
)
