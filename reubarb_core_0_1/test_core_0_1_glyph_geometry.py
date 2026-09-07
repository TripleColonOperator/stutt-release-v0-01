"""Finite I-9 checks for the approved native-glyph visual geometries."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import core_0_1_glyph_geometry as glyphs
import core_0_1_glyph_technical as i8


_SVG = "{http://www.w3.org/2000/svg}"


class GlyphGeometryTests(unittest.TestCase):
    def test_exact_approved_glyph_membership(self) -> None:
        self.assertEqual(glyphs.APPROVED_GLYPH_IDS, (2, 3, 4, 5, 6))
        self.assertEqual(len(glyphs.APPROVED_GLYPHS), 5)

    def test_every_registered_geometry_is_approved(self) -> None:
        for glyph in glyphs.APPROVED_GLYPHS:
            self.assertIs(glyph.status, glyphs.GeometryStatus.APPROVED)

    def test_construction_component_is_not_a_glyph(self) -> None:
        self.assertFalse(glyphs.CONSTRUCTION_COMPONENT_IS_GLYPH)
        self.assertNotIn(1, glyphs.APPROVED_GLYPH_IDS)
        self.assertIsNone(glyphs.get_approved_glyph(1))

    def test_g2_is_exact_congruent_statement_geometry(self) -> None:
        glyph = glyphs.G2_GEOMETRY
        self.assertEqual(glyph.circles, ())
        self.assertEqual(tuple(path.commands for path in glyph.paths), (
            "M500 150L220 500L500 950L780 500Z",
            "M500 350L330 500L500 650L670 500Z",
        ))

    def test_g3_is_exact_registered_overlay(self) -> None:
        glyph = glyphs.G3_GEOMETRY
        self.assertEqual(glyph.circles, glyphs.SHARED_FRAME_CIRCLES)
        self.assertEqual(glyph.paths, glyphs.CONGRUENT_STATEMENT_PATHS)

    def test_centered_variants_use_approved_frame_and_exact_centers(self) -> None:
        self.assertEqual(glyphs.G4_GEOMETRY.circles, glyphs.SHARED_FRAME_CIRCLES)
        self.assertEqual(glyphs.G5_GEOMETRY.circles, glyphs.SHARED_FRAME_CIRCLES)
        self.assertEqual(glyphs.G6_GEOMETRY.circles, glyphs.SHARED_FRAME_CIRCLES)
        self.assertEqual(tuple(path.commands for path in glyphs.G4_GEOMETRY.paths), (
            "M500 410V630M390 520H610",
        ))
        self.assertEqual(tuple(path.commands for path in glyphs.G5_GEOMETRY.paths), (
            "M360 535C405 455 455 615 500 535S595 455 640 535",
        ))
        self.assertEqual(tuple(path.commands for path in glyphs.G6_GEOMETRY.paths), (
            "M390 520H610",
        ))

    def test_shared_frame_matches_i8_approved_component(self) -> None:
        expected = tuple(
            glyphs.CircleGeometry(dot.x, dot.y, dot.radius)
            for dot in i8.APPROVED_SHARED_FRAME.dots
        )
        self.assertEqual(glyphs.SHARED_FRAME_CIRCLES, expected)

    def test_exact_svg_assets_match_registry(self) -> None:
        root = Path(__file__).resolve().parent
        for glyph in glyphs.APPROVED_GLYPHS:
            document = ET.parse(root / glyph.asset_path).getroot()
            self.assertEqual(document.attrib["viewBox"], f"0 0 {glyph.width} {glyph.height}")
            self.assertEqual(document.attrib["preserveAspectRatio"], "xMidYMid meet")
            circles = tuple(
                glyphs.CircleGeometry(
                    int(node.attrib["cx"]),
                    int(node.attrib["cy"]),
                    int(node.attrib["r"]),
                )
                for node in document.findall(f"{_SVG}circle")
            )
            paths = tuple(
                glyphs.PathGeometry(
                    node.attrib["d"],
                    int(node.attrib["stroke-width"]),
                    node.attrib["stroke-linecap"],
                    node.attrib["stroke-linejoin"],
                )
                for node in document.findall(f"{_SVG}path")
            )
            self.assertEqual(circles, glyph.circles)
            self.assertEqual(paths, glyph.paths)

    def test_geometry_records_are_frozen(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            glyphs.G4_GEOMETRY.design_id = 99  # type: ignore[misc]

    def test_lookup_is_exact_and_unknown_ids_stay_unmapped(self) -> None:
        for glyph in glyphs.APPROVED_GLYPHS:
            self.assertIs(glyphs.get_approved_glyph(glyph.design_id), glyph)
        self.assertIsNone(glyphs.get_approved_glyph(0))
        self.assertIsNone(glyphs.get_approved_glyph(7))

    def test_i8_proposal_record_remains_historical_and_unchanged(self) -> None:
        for variant in i8.all_variants():
            self.assertIs(variant.status, i8.ProposalStatus.PROVISIONAL)

    def test_registry_does_not_assign_encoding_or_shortcuts(self) -> None:
        forbidden = {"scalar", "unicode", "shortcut", "token", "syntax", "meaning"}
        fields = set(glyphs.ApprovedGlyphGeometry.__dataclass_fields__)
        self.assertTrue(fields.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
