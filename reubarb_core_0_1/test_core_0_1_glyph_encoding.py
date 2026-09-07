"""Finite I-10 checks for private-use mappings and workspace shortcuts."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unicodedata
import unittest

import core_0_1_glyph_encoding as encoding
import core_0_1_glyph_geometry as geometry


class GlyphEncodingTests(unittest.TestCase):
    def test_exact_design_id_to_scalar_mapping(self) -> None:
        self.assertEqual(
            tuple((item.design_id, item.code_point_label) for item in encoding.APPROVED_GLYPH_ENCODINGS),
            ((2, "U+E100"), (3, "U+E101"), (4, "U+E102"), (5, "U+E103"), (6, "U+E104")),
        )

    def test_code_points_are_consecutive_in_reserved_e1_block(self) -> None:
        self.assertEqual(encoding.APPROVED_CODE_POINTS, tuple(range(0xE100, 0xE105)))
        self.assertEqual(encoding.REUBARB_GLYPH_BLOCK_START, 0xE100)

    def test_every_mapping_is_one_valid_bmp_private_use_scalar(self) -> None:
        for item in encoding.APPROVED_GLYPH_ENCODINGS:
            self.assertEqual(len(item.scalar), 1)
            self.assertEqual(ord(item.scalar), item.code_point)
            self.assertLessEqual(encoding.PRIMARY_PRIVATE_USE_START, item.code_point)
            self.assertLessEqual(item.code_point, encoding.PRIMARY_PRIVATE_USE_END)

    def test_scalars_and_shortcuts_are_unique(self) -> None:
        self.assertEqual(len(set(encoding.APPROVED_SCALARS)), 5)
        self.assertEqual(len(set(encoding.APPROVED_SHORTCUT_PREFIXES)), 5)

    def test_private_use_scalars_are_stable_under_unicode_normalization(self) -> None:
        for scalar in encoding.APPROVED_SCALARS:
            for form in ("NFC", "NFD", "NFKC", "NFKD"):
                self.assertEqual(unicodedata.normalize(form, scalar), scalar)

    def test_each_encoding_references_exact_approved_geometry(self) -> None:
        for item in encoding.APPROVED_GLYPH_ENCODINGS:
            self.assertIs(item.geometry, geometry.get_approved_glyph(item.design_id))
            self.assertIs(item.status, encoding.EncodingStatus.APPROVED)

    def test_construction_component_has_no_mapping_or_shortcut(self) -> None:
        self.assertIsNone(encoding.get_encoding_by_design_id(1))
        self.assertNotIn("rb.g1", encoding.APPROVED_SHORTCUT_PREFIXES)

    def test_shortcut_prefixes_follow_exact_design_ids(self) -> None:
        self.assertEqual(
            encoding.APPROVED_SHORTCUT_PREFIXES,
            ("rb.g2", "rb.g3", "rb.g4", "rb.g5", "rb.g6"),
        )

    def test_workspace_snippets_insert_exact_mapped_scalars(self) -> None:
        path = Path(__file__).resolve().parent / ".vscode" / "reubarb-glyphs.code-snippets"
        snippets = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(tuple(snippets), tuple(f"Reubarb G{i}" for i in range(2, 7)))
        for item in encoding.APPROVED_GLYPH_ENCODINGS:
            snippet = snippets[f"Reubarb G{item.design_id}"]
            self.assertEqual(snippet["prefix"], item.shortcut_prefix)
            self.assertEqual(snippet["body"], item.scalar)
            self.assertIn(item.code_point_label, snippet["description"])

    def test_workspace_snippets_are_limited_to_gart_files(self) -> None:
        path = Path(__file__).resolve().parent / ".vscode" / "reubarb-glyphs.code-snippets"
        snippets = json.loads(path.read_text(encoding="utf-8"))
        for snippet in snippets.values():
            self.assertEqual(snippet["include"], ["**/*.gart"])
            self.assertNotIn("scope", snippet)

    def test_shortcuts_are_input_conveniences_not_source_aliases(self) -> None:
        self.assertEqual(encoding.SHORTCUT_COMPLETION, "deliberate-editor-completion")
        for item in encoding.APPROVED_GLYPH_ENCODINGS:
            self.assertNotEqual(item.shortcut_prefix, item.scalar)

    def test_mapping_records_are_frozen(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            encoding.APPROVED_GLYPH_ENCODINGS[0].code_point = 0xE200  # type: ignore[misc]

    def test_exact_lookup_does_not_invent_unmapped_designs(self) -> None:
        for item in encoding.APPROVED_GLYPH_ENCODINGS:
            self.assertIs(encoding.get_encoding_by_design_id(item.design_id), item)
        for unmapped in (0, 1, 7, 0xE100):
            self.assertIsNone(encoding.get_encoding_by_design_id(unmapped))

    def test_catalogue_exposes_no_parser_recognizer_or_runtime_operation(self) -> None:
        for operation in ("parse", "recognize", "authorize", "evaluate", "execute", "render"):
            self.assertFalse(hasattr(encoding, operation))


if __name__ == "__main__":
    unittest.main()
