"""I-13 finite offline font QA; writes only the proof and validation report.

One ots-sanitize child, waited on with a 15-second deadline and killed on
cancellation. No GUI, font installation, network, or source execution.
"""
from __future__ import annotations

from collections import deque
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import build_reubarb_font as build


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def topology(mask):
    """Count 4-connected ink components and enclosed background regions."""
    import numpy as np

    def components(binary):
        seen = np.zeros(binary.shape, dtype=bool)
        count, interior = 0, 0
        height, width = binary.shape
        for y, x in zip(*np.nonzero(binary)):
            if seen[y, x]:
                continue
            count += 1
            edge = False
            seen[y, x] = True
            todo = deque([(int(y), int(x))])
            while todo:
                yy, xx = todo.popleft()
                edge |= yy == 0 or yy == height - 1 or xx == 0 or xx == width - 1
                for ny, nx in ((yy - 1, xx), (yy + 1, xx), (yy, xx - 1), (yy, xx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and binary[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        todo.append((ny, nx))
            interior += not edge
        return count, interior

    return components(mask)[0], components(~mask)[1]


def render_pair(typeface, master, size):
    import skia
    import math
    width = math.ceil(build.ADVANCE * size / build.UPEM) + 4
    height = size + 4
    images = []
    for reference in (True, False):
        surface = skia.Surface(width, height)
        canvas = surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        canvas.translate(2, 2)
        if reference:
            data = build.master_bytes(master[3], master[4])
            dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(data))
            require(dom is not None, "SVG renderer did not accept a fixed master")
            dom.setContainerSize(skia.Size(1000, 1200))
            canvas.scale(size / build.UPEM, size / build.UPEM)
            canvas.translate(0, build.ASCENT - build.TOP)
            canvas.scale(build.SCALE, build.SCALE)
            dom.render(canvas)
        else:
            font = skia.Font(typeface, size)
            font.setHinting(skia.FontHinting.kNone)
            font.setSubpixel(True)
            font.setEdging(skia.Font.Edging.kAntiAlias)
            canvas.drawString(chr(master[1]), 0, build.ASCENT * size / build.UPEM,
                              font, skia.Paint(AntiAlias=True, Color=skia.ColorBLACK))
        images.append(surface.makeImageSnapshot())
    return images


def ink(image):
    import skia
    return 255 - image.toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)[:, :, 0].astype("int16")


def sanitize(font_path):
    import ots
    executable = Path(ots.OTS_SANITIZE)
    if not executable.is_file():
        executable = executable.with_suffix(".exe")
    require(executable.is_file(), "Pinned OTS executable is missing")
    # OTS is a single native command with no worker/descendant launcher.
    with tempfile.TemporaryDirectory(prefix="reubarb-ots-") as temporary:
        result_path = Path(temporary) / "sanitized.ttf"
        process = subprocess.Popen([str(executable), str(font_path), str(result_path)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            stdout, stderr = process.communicate(timeout=15)
        except BaseException:
            process.kill()
            process.wait()
            raise
        require(process.returncode == 0, "OTS validation failed: " + stderr.decode(errors="replace"))
        require(not stderr.strip(), "OTS reported warnings: " + stderr.decode(errors="replace"))
        data = result_path.read_bytes()
    return {"exit_code": process.returncode, "output": stdout.decode(errors="replace").strip(),
            "warnings": stderr.decode(errors="replace").strip(), "sanitized_sha256": sha256(data).hexdigest()}, data


def make_proof(typeface):
    """PNG contains real font text, not recreated glyph illustrations."""
    import skia
    width, height = 1360, 1080
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorSetRGB(246, 244, 238))
    dark = skia.ColorSetRGB(23, 37, 45)
    light = skia.ColorSetRGB(239, 244, 238)
    text_face = skia.FontMgr.RefDefault().matchFamilyStyle("Segoe UI", skia.FontStyle.Normal())
    require(text_face is not None, "Proof label font unavailable")

    def text(value, x, baseline, size=18, color=dark, native=False):
        font = skia.Font(typeface if native else text_face, size)
        font.setHinting(skia.FontHinting.kNone)
        font.setSubpixel(True)
        font.setEdging(skia.Font.Edging.kAntiAlias)
        canvas.drawString(value, x, baseline, font, skia.Paint(AntiAlias=True, Color=color))

    text("REUBARB PI  /  FONT PROOF 0.100", 48, 47, 17)
    text("Five approved forms. Actual font characters.", 48, 99, 36)
    text("Uniform geometry  |  Round strokes  |  Private-use mappings  |  Offline", 48, 136, 18)
    for i, (design, cp, label, *_rest) in enumerate(build.MASTERS):
        x = 48 + i * 255
        canvas.drawRoundRect(skia.Rect.MakeXYWH(x, 173, 235, 310), 10, 10,
                             skia.Paint(Color=skia.ColorWHITE))
        text(f"G{design}", x + 18, 208, 22)
        text(label, x + 18, 234, 16)
        text(chr(cp), x + 56, 416, 205, native=True)
        text(f"U+{cp:04X}   /   rb.g{design}", x + 18, 461, 16)
    sequence = "".join(chr(m[1]) for m in build.MASTERS)
    text("READING SIZES — same characters, no weight changes", 48, 531, 18)
    for x, background, foreground in ((48, skia.ColorWHITE, dark), (696, dark, light)):
        canvas.drawRoundRect(skia.Rect.MakeXYWH(x, 551, 616, 356), 10, 10,
                             skia.Paint(Color=background))
        for row, size in enumerate((12, 14, 16, 18, 20, 22, 24, 32)):
            baseline = 585 + row * 42
            text(f"{size}px", x + 22, baseline, 16, foreground)
            text(sequence, x + 116, baseline, size, foreground, native=True)
    text("Start at 24px; use 32px for closer inspection. Fine strokes are delicate at small sizes.", 48, 957, 20)
    text("The preview HTML shows the font beside the original SVGs and in code comments.", 48, 994, 18)
    text("Display only. SVG masters remain canonical. No font has been installed.", 48, 1030, 17)
    build.write_generated(build.OUT / "font-proof.png", bytes(surface.makeImageSnapshot().encodeToData()))


def main():
    if len(sys.argv) != 1:
        raise SystemExit("This fixed font check takes no arguments")
    build.check_environment()
    import numpy as np
    import skia
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont

    font_path = build.OUT / build.FONT_NAME
    data = font_path.read_bytes()
    manifest = json.loads((build.OUT / "font-manifest.json").read_text(encoding="utf-8"))
    require(sha256(data).hexdigest() == manifest["font_sha256"], "Font fingerprint mismatch")
    require(build.build_font() == data, "Fresh build differs from the delivered font")
    require(sha256(Path(build.__file__).read_bytes()).hexdigest() == manifest["build_source_sha256"], "Builder changed since artifact creation")
    font = TTFont(BytesIO(data), checkChecksums=2, lazy=False, recalcTimestamp=False)
    font.ensureDecompiled()
    require(font["head"].unitsPerEm == build.UPEM, "Incorrect units-per-em in compiled font")
    expected = {m[1]: f"uni{m[1]:04X}" for m in build.MASTERS}
    require(font.getBestCmap() == expected, "Unexpected cmap")
    require(set(font.keys()) == {"GlyphOrder", "head", "hhea", "maxp", "OS/2", "hmtx", "cmap", "loca", "glyf", "name", "post", "gasp"}, "Unexpected font table")
    for name in font.getGlyphOrder():
        glyph = font["glyf"][name]
        require(not glyph.isComposite(), "Unexpected composite glyph")
        require(len(glyph.program.getBytecode()) == 0, "Unexpected TrueType instructions")
        require(0 <= glyph.xMin < glyph.xMax <= build.ADVANCE, "Horizontal clipping")
        require(build.DESCENT <= glyph.yMin < glyph.yMax <= build.ASCENT, "Vertical clipping")
        require(font["hmtx"][name] == (build.ADVANCE, glyph.xMin), "Incorrect advance or bearing")

    ots_report, sanitized_data = sanitize(font_path)
    sanitized = TTFont(BytesIO(sanitized_data), lazy=False)
    require(sanitized.getBestCmap() == expected, "Sanitizer changed the mapping")
    for name in font.getGlyphOrder():
        require(font["glyf"][name].getCoordinates(font["glyf"]) == sanitized["glyf"][name].getCoordinates(sanitized["glyf"]), "Sanitizer changed geometry")

    face = hb.Face(data)
    shaping_font = hb.Font(face)
    shaping_font.scale = (build.UPEM, build.UPEM)
    sequence = "".join(chr(m[1]) for m in build.MASTERS)
    for sample in (sequence, sequence[::-1], sequence * 64):
        buffer = hb.Buffer()
        buffer.add_str(sample)
        buffer.guess_segment_properties()
        hb.shape(shaping_font, buffer)
        require([g.codepoint for g in buffer.glyph_infos] == [ord(c) - 0xE100 + 1 for c in sample], "Shaping altered glyph identities")
        require(all(p.x_advance == build.ADVANCE and p.y_advance == p.x_offset == p.y_offset == 0 for p in buffer.glyph_positions), "Shaping changed placement")
    for cp in (0, 0x20, 0x41, 0xE0FF, 0xE105, 0xF8FF):
        require(shaping_font.get_nominal_glyph(cp) is None, "Unexpected additional encoded glyph")

    typeface = skia.Typeface.MakeFromData(skia.Data.MakeWithCopy(data))
    require(typeface is not None, "Native renderer refused font")
    require(typeface.unicharsToGlyphs([m[1] for m in build.MASTERS]) == [1, 2, 3, 4, 5], "Native renderer mapping mismatch")
    comparisons = []
    for master in build.MASTERS:
        reference, rendered = map(ink, render_pair(typeface, master, 2048))
        error = float(np.abs(reference - rendered).sum() / reference.sum())
        require(error < 0.02, f"G{master[0]} excessive high-resolution ink error: {error}")
        high_bounds = []
        for bitmap in (reference, rendered):
            ys, xs = np.nonzero(bitmap > 127)
            high_bounds.append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
        require(max(abs(a - b) for a, b in zip(*high_bounds)) <= 1, "SVG/font bounds differ by more than 1 font unit")
        topologies = [topology(ink(im) > 127) for im in render_pair(typeface, master, 256)]
        expected_topology = (2, 2) if master[0] in (2, 3) else (5, 0)
        require(topologies == [expected_topology, expected_topology], f"G{master[0]} topology mismatch: {topologies}")
        for size in (12, 14, 16, 18, 20, 22, 24, 32, 48, 96):
            actual = ink(render_pair(typeface, master, size)[1])
            require(actual.sum() > 0, "Invisible glyph")
            require(not any((actual[0].any(), actual[-1].any(), actual[:, 0].any(), actual[:, -1].any())), "Ink clipped at a reading size")
        comparisons.append({"design_id": master[0], "relative_ink_error_at_2048_px": error,
                            "reference_bounds": high_bounds[0], "font_bounds": high_bounds[1],
                            "components_and_holes_at_256_px": topologies[1]})
    make_proof(typeface)
    report = {"profile": "reubarb-font-i13-qa-0.100", "font_sha256": sha256(data).hexdigest(),
              "result": "passed", "rebuild_byte_identical": True, "ots": ots_report,
              "harfbuzz": "5 exact mappings; forward, reverse, 320-character sequence; uniform advances; 6 unmapped controls",
              "renderer": "Skia native font loading/rasterization compared with its independent SVG DOM rendering path",
              "sizes_px": [12, 14, 16, 18, 20, 22, 24, 32, 48, 96], "glyph_comparisons": comparisons,
              "proof_sha256": sha256((build.OUT / "font-proof.png").read_bytes()).hexdigest(),
              "checker_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
              "limits": ["Finite checks are not proof of absolute correctness or complete security.",
                         "SVG and font comparison paths share Skia; OTS and HarfBuzz are independent validators.",
                         "Visual proof must be inspected; actual VS Code cursor/fallback behavior is a later installation check."]}
    build.write_generated(build.OUT / "font-validation.json", (json.dumps(report, indent=2) + "\n").encode())
    print("I-13 font QA passed: reproducibility, OTS, HarfBuzz, native rendering, all five SVG comparisons, 10 sizes.")
    print("Highest relative ink difference at 2048px:", max(c["relative_ink_error_at_2048_px"] for c in comparisons))
    print("Proof and validation report written. No font installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
