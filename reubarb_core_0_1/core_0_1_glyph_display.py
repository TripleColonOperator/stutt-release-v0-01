"""I-12 dependency-free display references for approved Reubarb glyphs.

Canonical visual identity remains the approved SVG geometry.  Raw Private Use
Area characters may render as fallback boxes until a font is separately built
and deliberately installed.  These records provide a visible, local fallback
without interpreting or executing Reubarb source.
"""
from __future__ import annotations

from dataclasses import dataclass

import core_0_1_glyph_encoding as i10


@dataclass(frozen=True, slots=True)
class GlyphDisplayReference:
    """One source-free link between an encoded glyph and its SVG reference."""

    design_id: int
    code_point: int
    code_point_label: str
    asset_path: str
    accessible_label: str
    visible_fallback: str


DISPLAY_PROFILE = "gart-glyph-display-i12-0.1"
CANONICAL_DISPLAY_SOURCE = "approved-svg-geometry"
RAW_PUA_RENDERING_IS_NORMATIVE = False
FONT_INSTALLATION_STATUS = "not-performed"


DISPLAY_REFERENCES: tuple[GlyphDisplayReference, ...] = tuple(
    GlyphDisplayReference(
        design_id=item.design_id,
        code_point=item.code_point,
        code_point_label=item.code_point_label,
        asset_path=item.geometry.asset_path,
        accessible_label=f"Reubarb glyph G{item.design_id} visual geometry",
        visible_fallback=f"[Reubarb G{item.design_id} {item.code_point_label}]",
    )
    for item in i10.APPROVED_GLYPH_ENCODINGS
)


def get_display_reference(code_point: int) -> GlyphDisplayReference | None:
    """Return an exact host display reference by integer code point."""
    if type(code_point) is not int:
        raise TypeError("code_point must be an exact integer")
    for item in DISPLAY_REFERENCES:
        if item.code_point == code_point:
            return item
    return None


__all__ = (
    "GlyphDisplayReference",
    "DISPLAY_PROFILE",
    "CANONICAL_DISPLAY_SOURCE",
    "RAW_PUA_RENDERING_IS_NORMATIVE",
    "FONT_INSTALLATION_STATUS",
    "DISPLAY_REFERENCES",
    "get_display_reference",
)
