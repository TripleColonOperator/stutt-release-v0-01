"""I-10 host encoding catalogue for the approved Reubarb glyph geometries.

Unicode 17.0 reserves U+E000..U+F8FF for private agreement and describes an
end-user convention that allocates upward from the low end of that area.  This
project keeps its earlier E1xx reservation and assigns five consecutive scalar
values to approved G2 through G6.  Unicode itself supplies no meaning for them.

The accompanying workspace snippets are an external input convenience.  Their
prefixes are not Reubarb source aliases or macros.  This module does not parse,
recognize, authorize, evaluate, execute, render, or install a font.

Primary technical source:
https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-23/
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import core_0_1_glyph_geometry as i9


class EncodingStatus(Enum):
    """Approval state within the bounded I-10 host encoding profile."""

    APPROVED = auto()


@dataclass(frozen=True, slots=True)
class GlyphEncoding:
    """One private agreement linking geometry, scalar, and host shortcut."""

    design_id: int
    code_point: int
    scalar: str
    code_point_label: str
    shortcut_prefix: str
    geometry: i9.ApprovedGlyphGeometry
    status: EncodingStatus = EncodingStatus.APPROVED


UNICODE_PROFILE = "Unicode 17.0.0"
PRIMARY_PRIVATE_USE_START = 0xE000
PRIMARY_PRIVATE_USE_END = 0xF8FF
REUBARB_GLYPH_BLOCK_START = 0xE100
SHORTCUT_COMPLETION = "deliberate-editor-completion"


def _make_encoding(design_id: int, offset: int) -> GlyphEncoding:
    geometry = i9.get_approved_glyph(design_id)
    if geometry is None:
        raise ValueError("I-10 can encode only an I-9 approved glyph geometry")
    code_point = REUBARB_GLYPH_BLOCK_START + offset
    return GlyphEncoding(
        design_id=design_id,
        code_point=code_point,
        scalar=chr(code_point),
        code_point_label=f"U+{code_point:04X}",
        shortcut_prefix=f"rb.g{design_id}",
        geometry=geometry,
    )


APPROVED_GLYPH_ENCODINGS: tuple[GlyphEncoding, ...] = tuple(
    _make_encoding(design_id, offset)
    for offset, design_id in enumerate(i9.APPROVED_GLYPH_IDS)
)

APPROVED_CODE_POINTS = tuple(item.code_point for item in APPROVED_GLYPH_ENCODINGS)
APPROVED_SCALARS = tuple(item.scalar for item in APPROVED_GLYPH_ENCODINGS)
APPROVED_SHORTCUT_PREFIXES = tuple(
    item.shortcut_prefix for item in APPROVED_GLYPH_ENCODINGS
)


def get_encoding_by_design_id(design_id: int) -> GlyphEncoding | None:
    """Return a host encoding record by exact design ID, or ``None``."""
    for item in APPROVED_GLYPH_ENCODINGS:
        if item.design_id == design_id:
            return item
    return None


__all__ = (
    "EncodingStatus",
    "GlyphEncoding",
    "UNICODE_PROFILE",
    "PRIMARY_PRIVATE_USE_START",
    "PRIMARY_PRIVATE_USE_END",
    "REUBARB_GLYPH_BLOCK_START",
    "SHORTCUT_COMPLETION",
    "APPROVED_GLYPH_ENCODINGS",
    "APPROVED_CODE_POINTS",
    "APPROVED_SCALARS",
    "APPROVED_SHORTCUT_PREFIXES",
    "get_encoding_by_design_id",
)
