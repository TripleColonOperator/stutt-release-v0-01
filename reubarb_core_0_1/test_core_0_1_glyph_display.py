"""Finite I-12 checks for dependency-free glyph display references."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from html.parser import HTMLParser
from pathlib import Path
import unittest

import core_0_1_glyph_display as display
import core_0_1_glyph_encoding as encoding


class _PreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.figures: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.scripts = 0
        self.forms = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "figure":
            self.figures.append(values)
        elif tag == "img":
            self.images.append(values)
        elif tag == "script":
            self.scripts += 1
        elif tag == "form":
            self.forms += 1


class GlyphDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preview_path = Path(__file__).resolve().parent / "reubarb_glyph_encoding_preview.html"
        cls.preview_text = cls.preview_path.read_text(encoding="utf-8")
        cls.parser = _PreviewParser()
        cls.parser.feed(cls.preview_text)

    def test_display_profile_is_explicit(self) -> None:
        self.assertEqual(display.DISPLAY_PROFILE, "gart-glyph-display-i12-0.1")
        self.assertEqual(display.CANONICAL_DISPLAY_SOURCE, "approved-svg-geometry")

    def test_every_encoding_has_one_display_reference(self) -> None:
        self.assertEqual(len(display.DISPLAY_REFERENCES), 5)
        self.assertEqual(
            tuple(item.design_id for item in display.DISPLAY_REFERENCES),
            tuple(item.design_id for item in encoding.APPROVED_GLYPH_ENCODINGS),
        )

    def test_display_references_use_exact_encoding_and_svg_assets(self) -> None:
        for reference, encoded in zip(display.DISPLAY_REFERENCES, encoding.APPROVED_GLYPH_ENCODINGS):
            self.assertEqual(reference.code_point, encoded.code_point)
            self.assertEqual(reference.code_point_label, encoded.code_point_label)
            self.assertEqual(reference.asset_path, encoded.geometry.asset_path)

    def test_visible_fallbacks_are_exact_and_unique(self) -> None:
        actual = tuple(item.visible_fallback for item in display.DISPLAY_REFERENCES)
        self.assertEqual(actual, tuple(f"[Reubarb G{i} U+E{0xFE + i:03X}]" for i in range(2, 7)))
        self.assertEqual(len(set(actual)), 5)

    def test_raw_pua_rendering_is_not_normative_and_no_font_is_installed(self) -> None:
        self.assertFalse(display.RAW_PUA_RENDERING_IS_NORMATIVE)
        self.assertEqual(display.FONT_INSTALLATION_STATUS, "not-performed")

    def test_lookup_is_exact_and_host_typed(self) -> None:
        for item in display.DISPLAY_REFERENCES:
            self.assertIs(display.get_display_reference(item.code_point), item)
        self.assertIsNone(display.get_display_reference(0xE105))
        with self.assertRaises(TypeError):
            display.get_display_reference("U+E100")  # type: ignore[arg-type]

    def test_display_records_are_frozen(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            display.DISPLAY_REFERENCES[0].asset_path = "other.svg"  # type: ignore[misc]

    def test_preview_has_exact_five_cards(self) -> None:
        self.assertEqual(
            tuple((item["data-design-id"], item["data-code-point"]) for item in self.parser.figures),
            tuple((str(i), f"U+E{0xFE + i:03X}") for i in range(2, 7)),
        )

    def test_preview_images_match_display_manifest(self) -> None:
        self.assertEqual(
            tuple((item["src"], item["alt"]) for item in self.parser.images),
            tuple((item.asset_path, item.accessible_label) for item in display.DISPLAY_REFERENCES),
        )

    def test_preview_contains_raw_entities_shortcuts_and_fallbacks(self) -> None:
        for item in encoding.APPROVED_GLYPH_ENCODINGS:
            self.assertIn(f"&#x{item.code_point:X};", self.preview_text)
            self.assertIn(item.shortcut_prefix, self.preview_text)
            self.assertIn(f"[Reubarb G{item.design_id} {item.code_point_label}]", self.preview_text)

    def test_preview_has_no_script_form_or_remote_reference(self) -> None:
        self.assertEqual(self.parser.scripts, 0)
        self.assertEqual(self.parser.forms, 0)
        lowered = self.preview_text.lower()
        for forbidden in ("http://", "https://", "fetch(", "xmlhttprequest", "localstorage", "clipboard"):
            self.assertNotIn(forbidden, lowered)

    def test_display_layer_exposes_no_renderer_parser_or_execution_operation(self) -> None:
        for operation in ("render", "parse", "recognize", "authorize", "evaluate", "execute"):
            self.assertFalse(hasattr(display, operation))


if __name__ == "__main__":
    unittest.main()
