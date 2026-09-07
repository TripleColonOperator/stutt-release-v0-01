"""I-13 shipped-font contract checks, using only Python's standard library.

These inspect the binary; they do not import the font builder or third-party
tools. Full rebuild/raster/shaping checks live in check_reubarb_font.py.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parent
ART = ROOT / "fonts" / "v0_1"
FONT = ART / "ReubarbPiSymbols-Regular.ttf"


def u16(data, offset): return struct.unpack_from(">H", data, offset)[0]
def i16(data, offset): return struct.unpack_from(">h", data, offset)[0]
def u32(data, offset): return struct.unpack_from(">I", data, offset)[0]


def checksum(data):
    data += b"\0" * (-len(data) % 4)
    return sum(struct.unpack(">" + "I" * (len(data) // 4), data)) & 0xFFFFFFFF


class GlyphFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = FONT.read_bytes()
        cls.manifest = json.loads((ART / "font-manifest.json").read_text(encoding="utf-8"))
        cls.tables, cls.directory = {}, []
        for index in range(u16(cls.data, 4)):
            tag, digest, offset, length = struct.unpack_from(">4sIII", cls.data, 12 + index * 16)
            tag = tag.decode("ascii")
            cls.directory.append((tag, digest, offset, length))
            cls.tables[tag] = cls.data[offset:offset + length]

    def cmaps(self):
        data = self.tables["cmap"]
        result = []
        for index in range(u16(data, 2)):
            platform, encoding, offset = struct.unpack_from(">HHI", data, 4 + index * 8)
            self.assertEqual(u16(data, offset), 4)
            sub = data[offset:offset + u16(data, offset + 2)]
            segments = u16(sub, 6) // 2
            mapping = {}
            for segment in range(segments):
                end = u16(sub, 14 + 2 * segment)
                start = u16(sub, 16 + 2 * segments + 2 * segment)
                delta = i16(sub, 16 + 4 * segments + 2 * segment)
                pointer = 16 + 6 * segments + 2 * segment
                relative = u16(sub, pointer)
                self.assertLessEqual(end - start, 5)
                for cp in range(start, end + 1):
                    gid = u16(sub, pointer + relative + 2 * (cp - start)) if relative else cp
                    if not relative or gid:
                        gid = (gid + delta) & 0xFFFF
                    if gid:
                        mapping[cp] = gid
            result.append((platform, encoding, mapping))
        return result

    def glyphs(self):
        loca = self.tables["loca"]
        long_offsets = i16(self.tables["head"], 50) == 1
        size = 4 if long_offsets else 2
        read = u32 if long_offsets else lambda b, o: 2 * u16(b, o)
        count = u16(self.tables["maxp"], 4)
        return [self.tables["glyf"][read(loca, i * size):read(loca, (i + 1) * size)] for i in range(count)]

    def test_manifest_binds_delivered_font(self):
        self.assertEqual(self.manifest["font_sha256"], sha256(self.data).hexdigest())
        self.assertEqual(self.manifest["font_bytes"], len(self.data))
        self.assertLess(len(self.data), 65536)

    def test_sfnt_table_bounds_alignment_and_checksums(self):
        self.assertEqual(self.data[:4], b"\0\1\0\0")
        self.assertEqual(checksum(self.data), 0xB1B0AFBA)
        self.assertEqual(len(self.tables), len(self.directory))
        spans = []
        for tag, digest, offset, length in self.directory:
            self.assertEqual(offset % 4, 0)
            self.assertGreaterEqual(offset, 12 + 16 * len(self.directory))
            self.assertLessEqual(offset + length, len(self.data))
            block = self.tables[tag]
            if tag == "head": block = block[:8] + b"\0" * 4 + block[12:]
            self.assertEqual(checksum(block), digest, tag)
            spans.append((offset, offset + length))
        spans.sort()
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])))

    def test_only_static_outline_tables_are_present(self):
        self.assertEqual(set(self.tables), {"head", "hhea", "maxp", "OS/2", "hmtx", "cmap", "loca", "glyf", "name", "post", "gasp"})

    def test_compiled_units_and_metrics_match_profile(self):
        self.assertEqual(u16(self.tables["head"], 18), 2048)
        self.assertEqual(u32(self.tables["head"], 12), 0x5F0F3CF5)
        hhea, os2 = self.tables["hhea"], self.tables["OS/2"]
        self.assertEqual(tuple(i16(hhea, x) for x in (4, 6, 8)), (1664, -384, 0))
        self.assertEqual(tuple(i16(os2, x) for x in (68, 70, 72)), (1664, -384, 0))
        self.assertGreaterEqual(u16(os2, 74), i16(self.tables["head"], 42))
        self.assertGreaterEqual(u16(os2, 76), -i16(self.tables["head"], 38))
        self.assertEqual(u16(os2, 62) & 0xC0, 0xC0)

    def test_exact_five_unicode_mappings_no_construction_or_ascii(self):
        maps = self.cmaps()
        self.assertEqual({(p, e) for p, e, _ in maps}, {(0, 3), (3, 1)})
        for _, _, mapping in maps:
            self.assertEqual(mapping, {0xE100 + i: i + 1 for i in range(5)})

    def test_six_visible_unhinted_simple_glyphs_keep_required_contours(self):
        glyphs = self.glyphs()
        self.assertEqual(len(glyphs), 6)
        for glyph, expected in zip(glyphs, (2, 4, 4, 5, 5, 5)):
            self.assertEqual(i16(glyph, 0), expected)
            self.assertEqual(u16(glyph, 10 + 2 * expected), 0)  # instruction length
            self.assertLess(i16(glyph, 2), i16(glyph, 6))
            self.assertLess(i16(glyph, 4), i16(glyph, 8))

    def test_uniform_advances_and_uncropped_bounds(self):
        number = u16(self.tables["hhea"], 34)
        hmtx = self.tables["hmtx"]
        for index, glyph in enumerate(self.glyphs()):
            width = u16(hmtx, 4 * min(index, number - 1))
            bearing = i16(hmtx, 4 * index + 2) if index < number else i16(hmtx, 4 * number + 2 * (index - number))
            self.assertEqual(width, 1233)
            self.assertEqual(bearing, i16(glyph, 2))
            self.assertGreaterEqual(i16(glyph, 2), 0)
            self.assertLessEqual(i16(glyph, 6), width)
            self.assertGreaterEqual(i16(glyph, 4), -384)
            self.assertLessEqual(i16(glyph, 8), 1664)

    def test_source_and_builder_provenance_remain_bound(self):
        for entry in self.manifest["sources"]:
            self.assertEqual(sha256((ROOT / entry["asset"]).read_bytes()).hexdigest(), entry["sha256"])
        for name, key in (("build_reubarb_font.py", "build_source_sha256"), ("font-build-requirements.txt", "requirements_sha256")):
            self.assertEqual(sha256((ROOT / name).read_bytes()).hexdigest(), self.manifest[key])

    def test_tool_license_notices_are_retained(self):
        entries = self.manifest["tool_licenses"]
        self.assertEqual({e["tool"] for e in entries}, set(self.manifest["tools"]))
        for entry in entries:
            self.assertEqual(sha256((ART / entry["file"]).read_bytes()).hexdigest(), entry["sha256"])

    def test_offline_preview_uses_actual_font_and_unique_svg_titles(self):
        html = (ART / "font-preview.html").read_text(encoding="utf-8")
        embedded = re.search(r"data:font/ttf;base64,([A-Za-z0-9+/=]+)", html)
        self.assertIsNotNone(embedded)
        self.assertEqual(base64.b64decode(embedded[1], validate=True), self.data)
        self.assertEqual(re.findall(r'id="(title-g\d)"', html), [f"title-g{i}" for i in range(2, 7)])
        self.assertNotRegex(html, r"(?i)<script|<iframe|<form|https?://(?!www\.w3\.org/2000/svg)")
        self.assertIn("default-src 'none'", html)

    def test_full_validation_report_matches_current_artifacts(self):
        report = json.loads((ART / "font-validation.json").read_text(encoding="utf-8"))
        self.assertEqual(report["result"], "passed")
        self.assertTrue(report["rebuild_byte_identical"])
        self.assertEqual(report["font_sha256"], sha256(self.data).hexdigest())
        self.assertEqual(report["ots"]["exit_code"], 0)
        self.assertEqual(report["ots"]["warnings"], "")
        self.assertEqual(report["checker_sha256"], sha256((ROOT / "check_reubarb_font.py").read_bytes()).hexdigest())
        self.assertEqual(report["proof_sha256"], sha256((ART / "font-proof.png").read_bytes()).hexdigest())
        self.assertEqual([c["design_id"] for c in report["glyph_comparisons"]], [2, 3, 4, 5, 6])
        for comparison in report["glyph_comparisons"]:
            self.assertLess(comparison["relative_ink_error_at_2048_px"], .02)

    def test_editor_specimen_is_comments_with_exact_characters(self):
        sample = (ART / "glyph-specimen.gart").read_text(encoding="utf-8")
        self.assertTrue(all(line.startswith("//") or not line for line in sample.splitlines()))
        for cp in range(0xE100, 0xE105): self.assertEqual(sample.count(chr(cp)), 1)
        from core_0_1_lexical_frontend import lex_source
        self.assertEqual(lex_source(sample).outcome, "lexed")


if __name__ == "__main__":
    unittest.main()
