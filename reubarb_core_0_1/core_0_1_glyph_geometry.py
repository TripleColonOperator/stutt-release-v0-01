"""I-9 approved V0.1 native-glyph visual geometry registry.

The user approved every actual glyph form currently stored in the
``glyphs/v0_1`` project folder.  This module records the exact normalized
geometry of G2 through G6.  The four-dot SVG is a reusable construction
component, not a source glyph.

Design identifiers and review labels are host-side references.  This registry
does not assign Unicode scalars, shortcuts, language spellings, recognition
mappings, syntax, runtime values, authority, evaluation, or execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import core_0_1_glyph_technical as i8


class GeometryStatus(Enum):
    """Approval state within the bounded I-9 visual-geometry profile."""

    APPROVED = auto()


@dataclass(frozen=True, slots=True)
class CircleGeometry:
    """One filled circle in normalized vector coordinates."""

    x: int
    y: int
    radius: int


@dataclass(frozen=True, slots=True)
class PathGeometry:
    """One stroked SVG path in normalized vector coordinates."""

    commands: str
    stroke_width: int
    linecap: str = "round"
    linejoin: str = "round"


@dataclass(frozen=True, slots=True)
class ApprovedGlyphGeometry:
    """One approved visual form; fields do not constitute language syntax."""

    design_id: int
    review_label: str
    asset_path: str
    width: int
    height: int
    circles: tuple[CircleGeometry, ...]
    paths: tuple[PathGeometry, ...]
    status: GeometryStatus = GeometryStatus.APPROVED


VIEW_WIDTH = i8.VIEW_WIDTH
VIEW_HEIGHT = i8.VIEW_HEIGHT
STROKE_WIDTH = i8.STROKE_WIDTH

SHARED_FRAME_CIRCLES: tuple[CircleGeometry, ...] = tuple(
    CircleGeometry(dot.x, dot.y, dot.radius) for dot in i8.APPROVED_SHARED_FRAME.dots
)

CONGRUENT_STATEMENT_PATHS = (
    PathGeometry("M500 150L220 500L500 950L780 500Z", STROKE_WIDTH),
    PathGeometry("M500 350L330 500L500 650L670 500Z", STROKE_WIDTH),
)

G2_GEOMETRY = ApprovedGlyphGeometry(
    design_id=2,
    review_label="Congruent statement",
    asset_path="glyphs/v0_1/rp_g02_congruent_statement.svg",
    width=VIEW_WIDTH,
    height=VIEW_HEIGHT,
    circles=(),
    paths=CONGRUENT_STATEMENT_PATHS,
)

G3_GEOMETRY = ApprovedGlyphGeometry(
    design_id=3,
    review_label="Fulfilled overlay",
    asset_path="glyphs/v0_1/rp_g03_fulfilled_overlay.svg",
    width=VIEW_WIDTH,
    height=VIEW_HEIGHT,
    circles=SHARED_FRAME_CIRCLES,
    paths=CONGRUENT_STATEMENT_PATHS,
)


def _centered_variant_geometry(design_id: int, asset_name: str) -> ApprovedGlyphGeometry:
    variant = i8.get_variant(design_id)
    if variant is None or design_id == i8.CONSTRUCTION_DRAFT_FRAME.design_id:
        raise ValueError("I-9 centered geometry requires an I-8 centered variant")
    return ApprovedGlyphGeometry(
        design_id=design_id,
        review_label=variant.display_name,
        asset_path=f"glyphs/v0_1/{asset_name}",
        width=VIEW_WIDTH,
        height=VIEW_HEIGHT,
        circles=SHARED_FRAME_CIRCLES,
        paths=(PathGeometry("".join(variant.center_path_cmds), variant.stroke_width),),
    )


G4_GEOMETRY = _centered_variant_geometry(4, "rp_g04_strong_variant.svg")
G5_GEOMETRY = _centered_variant_geometry(5, "rp_g05_neutral_variant.svg")
G6_GEOMETRY = _centered_variant_geometry(6, "rp_g06_weak_variant.svg")

APPROVED_GLYPHS: tuple[ApprovedGlyphGeometry, ...] = (
    G2_GEOMETRY,
    G3_GEOMETRY,
    G4_GEOMETRY,
    G5_GEOMETRY,
    G6_GEOMETRY,
)
APPROVED_GLYPH_IDS = tuple(glyph.design_id for glyph in APPROVED_GLYPHS)

CONSTRUCTION_COMPONENT_ASSET = "glyphs/v0_1/rp_component_four_dot_frame.svg"
CONSTRUCTION_COMPONENT_IS_GLYPH = False


def get_approved_glyph(design_id: int) -> ApprovedGlyphGeometry | None:
    """Return an approved visual form by host design ID, or ``None``."""
    for glyph in APPROVED_GLYPHS:
        if glyph.design_id == design_id:
            return glyph
    return None


__all__ = (
    "GeometryStatus",
    "CircleGeometry",
    "PathGeometry",
    "ApprovedGlyphGeometry",
    "VIEW_WIDTH",
    "VIEW_HEIGHT",
    "STROKE_WIDTH",
    "SHARED_FRAME_CIRCLES",
    "CONGRUENT_STATEMENT_PATHS",
    "G2_GEOMETRY",
    "G3_GEOMETRY",
    "G4_GEOMETRY",
    "G5_GEOMETRY",
    "G6_GEOMETRY",
    "APPROVED_GLYPHS",
    "APPROVED_GLYPH_IDS",
    "CONSTRUCTION_COMPONENT_ASSET",
    "CONSTRUCTION_COMPONENT_IS_GLYPH",
    "get_approved_glyph",
)
