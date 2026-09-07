"""Finite tests for V0.1 native-glyph technical draft geometry and draft metadata."""
from __future__ import annotations

import unittest

import core_0_1_glyph_technical as glyphs


class GlyphTechnicalTests(unittest.TestCase):
    def test_shared_frame_is_approved_geometry(self) -> None:
        frame = glyphs.get_shared_frame()
        self.assertEqual((frame.width, frame.height), (glyphs.VIEW_WIDTH, glyphs.VIEW_HEIGHT))
        self.assertEqual(tuple((dot.label, dot.x, dot.y, dot.radius) for dot in frame.dots), (
            ("north", 500, 150, glyphs.DOT_RADIUS),
            ("west", 220, 500, glyphs.DOT_RADIUS),
            ("east", 780, 500, glyphs.DOT_RADIUS),
            ("south", 500, 950, glyphs.DOT_RADIUS),
        ))

    def test_dot_coordinates_match_approved_cross_span(self) -> None:
        self.assertEqual(glyphs.frame_dot_coordinates(), (
            (500, 150),
            (220, 500),
            (780, 500),
            (500, 950),
        ))

    def test_shared_frame_is_reused_across_variants(self) -> None:
        for variant in glyphs.all_variants():
            self.assertIs(variant.frame, glyphs.APPROVED_SHARED_FRAME)
            self.assertEqual(variant.stroke_width, glyphs.STROKE_WIDTH)

    def test_centered_variants_have_expected_design_ids_and_names(self) -> None:
        actual = tuple((variant.design_id, variant.display_name) for variant in glyphs.all_variants())
        self.assertEqual(actual, ((4, "Strong"), (5, "Neutral"), (6, "Weak")))
        self.assertEqual(glyphs.REVERSION_DEPENDENCE_VARIANT_IDS, (4, 5, 6))
        self.assertEqual(glyphs.VARIANT_ORDER_BY_ID, (1, 4, 5, 6))

    def test_variant_center_paths_are_distinct(self) -> None:
        variant_paths = tuple(variant.center_path_cmds for variant in glyphs.all_variants())
        self.assertEqual(len({tuple(path) for path in variant_paths}), 3)

        strong, neutral, weak = glyphs.all_variants()
        self.assertEqual(strong.center_kind, "cross-plus")
        self.assertEqual(neutral.center_kind, "wave")
        self.assertEqual(weak.center_kind, "flatline")
        self.assertEqual(
            strong.center_path_cmds,
            ("M500 410V630", "M390 520H610"),
        )
        self.assertEqual(
            neutral.center_path_cmds,
            ("M360 535C405 455 455 615 500 535S595 455 640 535",),
        )
        self.assertEqual(weak.center_path_cmds, ("M390 520H610",))

    def test_construction_frame_is_marked_separate(self) -> None:
        draft = glyphs.get_variant(1)
        self.assertIs(draft, glyphs.CONSTRUCTION_DRAFT_FRAME)
        self.assertEqual(draft.status.name, "CONSTRUCTION_DRAFT")
        self.assertEqual(draft.center_kind, "none")
        self.assertEqual(draft.center_path_cmds, ())

    def test_lookup_unknown_design_id(self) -> None:
        self.assertIsNone(glyphs.get_variant(99))

    def test_all_variants_are_provisional_until_further_approval(self) -> None:
        for variant in glyphs.all_variants():
            self.assertEqual(variant.status, glyphs.ProposalStatus.PROVISIONAL)


if __name__ == "__main__":
    unittest.main()
