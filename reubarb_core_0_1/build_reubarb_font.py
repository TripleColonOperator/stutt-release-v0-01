"""I-13 offline, fixed-input font builder. Run with the pinned build environment.

Only main() writes generated artifacts, beneath fonts/v0_1. No registration,
network, subprocess, source-language execution, or arbitrary input parser.
"""
from __future__ import annotations

import base64
import calendar
from hashlib import sha256
from html import escape
from importlib import metadata
from io import BytesIO
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "fonts" / "v0_1"
FONT_NAME = "ReubarbPiSymbols-Regular.ttf"
FAMILY = "Reubarb Pi Symbols"
VERSION = "0.100"
UPEM = 2048
ADVANCE = 1233  # 1233/2048 em, matching the common Consolas cell width.
SCALE = ADVANCE / 1000
TOP = 1420
ASCENT, DESCENT = 1664, -384
TIMESTAMP = calendar.timegm((2026, 9, 5, 0, 0, 0)) + 2082844800
CUBIC_ERROR = 0.20  # Font units; integer glyf rounding adds <= 0.5 per axis.
CONIC_SPLITS = 3  # Eight quadratic segments per rational conic.
STROKE_PRECISION = 32
TOOLS = {
    "fonttools": "4.64.0", "skia-python": "144.0.post2", "numpy": "2.5.2",
    "pybind11": "3.1.0", "opentype-sanitizer": "9.2.0", "uharfbuzz": "0.56.1",
}
MASTERS = (
    (2, 0xE100, "Congruent statement", "rp_g02_congruent_statement.svg", "cb8805479de603ed867059647a566dc6c746e020edff601a27955c1907380a42"),
    (3, 0xE101, "Fulfilled overlay", "rp_g03_fulfilled_overlay.svg", "1f4a08991e74d0694b6cc1c89c8458880773b497595e60d1a556ede7bfe7e2eb"),
    (4, 0xE102, "Strong", "rp_g04_strong_variant.svg", "3fdb6de995d28acbab65283652192a2d97393f50de0dbae478bd356c12d09ebe"),
    (5, 0xE103, "Neutral", "rp_g05_neutral_variant.svg", "9cbe50b63e497eca7a07a871885d0344f069149187f4c4d90bb6c6b22a093465"),
    (6, 0xE104, "Weak", "rp_g06_weak_variant.svg", "32ff2e96571b4030736f328257cdb78692e9bef441ba00e0a681bd411992d4d2"),
)


def check_environment() -> None:
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("The reproducible build profile requires Python 3.13")
    for name, expected in TOOLS.items():
        if metadata.version(name) != expected:
            raise RuntimeError(f"Expected {name}=={expected}; use the font build environment")


def master_bytes(filename: str, expected: str) -> bytes:
    data = (ROOT / "glyphs" / "v0_1" / filename).read_bytes()
    if sha256(data).hexdigest() != expected:
        raise RuntimeError(f"Approved SVG fingerprint changed: {filename}; review before rebuilding")
    return data


def svg_parts(filename: str, expected: str):
    """Read only a fingerprinted master and produce separate fill/stroke parts."""
    import skia
    from fontTools.pens.basePen import BasePen
    from fontTools.svgLib.path import parse_path

    class SkiaPen(BasePen):
        def __init__(self):
            super().__init__(None)
            self.path = skia.Path()

        def _moveTo(self, p): self.path.moveTo(*p)
        def _lineTo(self, p): self.path.lineTo(*p)
        def _curveToOne(self, a, b, c): self.path.cubicTo(*a, *b, *c)
        def _qCurveToOne(self, a, b): self.path.quadTo(*a, *b)
        def _closePath(self): self.path.close()
        def _endPath(self): pass

    doc = ET.fromstring(master_bytes(filename, expected))
    if doc.attrib.get("viewBox") != "0 0 1000 1200":
        raise ValueError("Unexpected approved frame")
    parts = []
    for node in doc:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "title":
            continue
        if tag == "circle":
            path = skia.Path()
            path.addCircle(float(node.attrib["cx"]), float(node.attrib["cy"]), float(node.attrib["r"]))
            paint = skia.Paint(AntiAlias=True, Color=skia.ColorBLACK)
        elif tag == "path":
            if (node.attrib["stroke-linecap"], node.attrib["stroke-linejoin"]) != ("round", "round"):
                raise ValueError("Unexpected stroke shape")
            pen = SkiaPen()
            parse_path(node.attrib["d"], pen)
            path = pen.path
            paint = skia.Paint(AntiAlias=True, Color=skia.ColorBLACK,
                               Style=skia.Paint.kStroke_Style,
                               StrokeWidth=float(node.attrib["stroke-width"]),
                               StrokeCap=skia.Paint.kRound_Cap,
                               StrokeJoin=skia.Paint.kRound_Join)
        else:
            raise ValueError("Unexpected SVG element")
        parts.append((path, paint))
    return parts


def expanded_outline(filename: str, expected: str):
    """Resolve actual stroked ink and overlaps before font contour conversion."""
    import skia
    merged = skia.Path()
    for path, paint in svg_parts(filename, expected):
        filled = skia.Path()
        if not paint.getFillPath(path, filled, resScale=STROKE_PRECISION):
            raise ValueError("Hairline geometry cannot be a filled font outline")
        merged = skia.Op(merged, filled, skia.PathOp.kUnion_PathOp)
    # Simplify resolves overlapping ink but uses even-odd contours. Preserve
    # those boundaries: AsWinding alone can misorient deeply nested rings.
    return skia.Simplify(merged)


def outline_to_glyph(path):
    import skia
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.transformPen import TransformPen

    sink = TTGlyphPen(None)
    quadratic = Cu2QuPen(sink, CUBIC_ERROR, reverse_direction=False, all_quadratic=True)
    pen = TransformPen(quadratic, (SCALE, 0, 0, -SCALE, 0, TOP))
    iterator = skia.Path.RawIter(path)
    # RawIter.__iter__ returns a copy in the pinned binding. Advance THIS
    # iterator explicitly so conicWeight() belongs to the current segment.
    while True:
        verb, points = iterator.next()
        if verb == skia.Path.kDone_Verb:
            break
        pairs = [tuple(p) for p in points]
        if verb == skia.Path.kMove_Verb:
            pen.moveTo(pairs[0])
        elif verb == skia.Path.kLine_Verb:
            pen.lineTo(pairs[1])
        elif verb == skia.Path.kQuad_Verb:
            pen.qCurveTo(*pairs[1:])
        elif verb == skia.Path.kCubic_Verb:
            pen.curveTo(*pairs[1:])
        elif verb == skia.Path.kConic_Verb:
            quads = skia.Path.ConvertConicToQuads(*points, iterator.conicWeight(), CONIC_SPLITS)
            for i in range(1, len(quads), 2):
                pen.qCurveTo(tuple(quads[i]), tuple(quads[i + 1]))
        elif verb == skia.Path.kClose_Verb:
            pen.closePath()
        elif verb != skia.Path.kDone_Verb:
            raise ValueError("Unsupported outline verb")
    glyph = sink.glyph()
    if glyph.numberOfContours <= 0 or len(glyph.coordinates) > 4096:
        raise ValueError("Empty or unexpectedly complex glyph")
    return normalize_winding(glyph)


def normalize_winding(glyph):
    """Orient disjoint, already-unioned contours by their nesting depth.

    TrueType exteriors are clockwise (negative signed area in font space);
    holes are counterclockwise. Each contour's first on-curve point is tested
    against other contours, never its own boundary. The source has already
    been unioned, so contours have no crossings or shared interior edges.
    """
    import skia
    from fontTools.pens.areaPen import AreaPen
    from fontTools.pens.basePen import BasePen
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.reverseContourPen import ReverseContourPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    class ContourPen(BasePen):
        def __init__(self):
            super().__init__(None)
            self.path = skia.Path()
        def _moveTo(self, p): self.path.moveTo(*p)
        def _lineTo(self, p): self.path.lineTo(*p)
        def _qCurveToOne(self, a, b): self.path.quadTo(*a, *b)
        def _curveToOne(self, a, b, c): self.path.cubicTo(*a, *b, *c)
        def _closePath(self): self.path.close()

    recording = RecordingPen()
    glyph.draw(recording, None)
    contours, current = [], []
    for command in recording.value:
        current.append(command)
        if command[0] == "closePath":
            contours.append(current)
            current = []
    if current:
        raise ValueError("Unclosed font contour")
    paths, areas = [], []
    for contour in contours:
        boundary, area = ContourPen(), AreaPen()
        for op, args in contour:
            getattr(boundary, op)(*args)
            getattr(area, op)(*args)
        paths.append(boundary.path)
        areas.append(area.value)
    sink = TTGlyphPen(None)
    for i, contour in enumerate(contours):
        point = contour[0][1][0]
        depth = sum(path.contains(*point) for j, path in enumerate(paths) if i != j)
        require_positive = depth % 2 == 1
        if areas[i] == 0:
            raise ValueError("Degenerate font contour")
        pen = sink if (areas[i] > 0) == require_positive else ReverseContourPen(sink)
        for op, args in contour:
            getattr(pen, op)(*args)
    return sink.glyph()


def missing_glyph():
    """Visible conventional missing-character box, deliberately unencoded."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    pen = TTGlyphPen(None)
    for points in (((230, 100), (230, 1250), (1003, 1250), (1003, 100)),
                   ((300, 170), (933, 170), (933, 1180), (300, 1180))):
        pen.moveTo(points[0])
        for point in points[1:]: pen.lineTo(point)
        pen.closePath()
    return pen.glyph()


def build_font() -> bytes:
    """Build in memory, with fixed tables, deterministic timestamps and ordering."""
    check_environment()
    from fontTools.fontBuilder import FontBuilder
    from fontTools.ttLib import newTable
    import core_0_1_glyph_encoding as encoding

    if tuple((e.design_id, e.code_point) for e in encoding.APPROVED_GLYPH_ENCODINGS) != tuple((m[0], m[1]) for m in MASTERS):
        raise ValueError("Accepted glyph mapping changed; review the font profile")
    order = [".notdef"] + [f"uni{cp:04X}" for _, cp, *_ in MASTERS]
    glyphs = {".notdef": missing_glyph()}
    for _, cp, _, filename, digest in MASTERS:
        glyphs[f"uni{cp:04X}"] = outline_to_glyph(expanded_outline(filename, digest))
    fb = FontBuilder(UPEM, isTTF=True)
    fb.font.recalcTimestamp = False
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({cp: f"uni{cp:04X}" for _, cp, *_ in MASTERS})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({name: (ADVANCE, glyph.xMin) for name, glyph in glyphs.items()})
    fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=0)
    fb.setupNameTable({
        "familyName": FAMILY, "styleName": "Regular",
        "uniqueFontIdentifier": f"GART:{FAMILY}:{VERSION}",
        "fullName": FAMILY + " Regular", "psName": "ReubarbPiSymbols-Regular",
        "version": "Version " + VERSION,
        "copyright": "Glyph artwork belongs to its project owner. Local review font; redistribution terms not assigned.",
        "description": "Five approved Reubarb Pi private-use glyphs, U+E100-U+E104. Display only. SVG masters remain canonical.",
        "licenseDescription": "For authorized local project use, review and editable embedding. No third-party artwork included. Standalone redistribution terms have not been assigned.",
    })
    fb.setupOS2(version=4, sTypoAscender=ASCENT, sTypoDescender=DESCENT,
                sTypoLineGap=0, usWinAscent=ASCENT, usWinDescent=-DESCENT,
                usWeightClass=400, usWidthClass=5, fsType=0x0008,
                fsSelection=0x00C0, achVendID="GART",
                ulUnicodeRange1=0, ulUnicodeRange2=1 << 28,
                ulUnicodeRange3=0, ulUnicodeRange4=0,
                ulCodePageRange1=0, ulCodePageRange2=0,
                sCapHeight=1321, sxHeight=0)
    fb.setupPost(isFixedPitch=1, underlinePosition=-200, underlineThickness=80)
    fb.setupMaxp()
    fb.updateHead(created=TIMESTAMP, modified=TIMESTAMP, fontRevision=0.1)
    fb.font["gasp"] = newTable("gasp")
    fb.font["gasp"].version = 1
    fb.font["gasp"].gaspRange = {65535: 0x000A}
    stream = BytesIO()
    fb.font.save(stream, reorderTables=True)
    data = stream.getvalue()
    if len(data) > 65536:
        raise ValueError("Unexpectedly large font")
    return data


def specimen_html(data: bytes) -> str:
    """Self-contained font specimen: actual characters + inline canonical SVGs."""
    cards = []
    for design, cp, label, filename, digest in MASTERS:
        svg = master_bytes(filename, digest).decode("utf-8")
        svg = svg.replace('id="title"', f'id="title-g{design}"').replace('aria-labelledby="title"', f'aria-labelledby="title-g{design}"')
        cards.append(f'<article><h2>G{design} <small>{escape(label)}</small></h2>'
                     f'<div class="pair"><div><div class="master">{svg}</div><p>Approved SVG</p></div>'
                     f'<div><div class="glyph" role="img" aria-label="G{design} {escape(label)}">&#{cp};</div><p>Actual font character</p></div></div>'
                     f'<p class="meta">U+{cp:04X} &nbsp; · &nbsp; rb.g{design}</p></article>')
    chars = "".join(f"&#{cp};" for _, cp, *_ in MASTERS)
    rows = "".join(f'<div class="size-row"><span>{size}px</span><span class="native" style="font-size:{size}px">{chars}</span></div>' for size in (100, 128, 192, 256))
    return f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; font-src data:; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<title>Reubarb Pi — font proof 0.100</title>
<style>
@font-face{{font-family:'Reubarb Pi Symbols';src:url(data:font/ttf;base64,{base64.b64encode(data).decode()}) format('truetype');font-style:normal;font-weight:400;font-display:block}}
*{{box-sizing:border-box}}body{{margin:0;background:#f6f4ee;color:#172d36;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:48px 24px}}h1{{font-size:40px;line-height:1.15;margin:8px 0 20px}}h2{{font-size:21px;margin:0}}small{{font-weight:400;font-size:15px;margin-left:12px}}.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:#46645d}}.intro{{max-width:760px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin:32px 0}}article,.panel{{border:1px solid #ccd5cd;border-radius:12px;padding:24px;background:#fffefa}}.pair{{display:flex;justify-content:space-around;text-align:center}}.pair p{{font-size:12px;color:#46645d}}.master,.glyph{{height:180px;display:flex;align-items:center;justify-content:center}}.master svg{{width:110px;height:132px}}.glyph{{font:{110 * UPEM / ADVANCE:.8f}px/1 'Reubarb Pi Symbols';width:145px}}.meta{{font:14px Consolas,monospace;color:#46645d}}.native{{font-family:'Reubarb Pi Symbols',Consolas,monospace;font-weight:400;font-style:normal;font-synthesis:none;letter-spacing:0}}.size-row{{display:flex;align-items:center;min-height:50px;gap:28px}}.size-row>span:first-child{{width:55px;font-size:13px;opacity:.7}}.themes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}.dark{{background:#17252d;color:#eef4ee;border-color:#17252d}}code{{font-family:Consolas,monospace}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}footer{{margin-top:30px;font-size:13px;color:#46645d}}
:root{{--glyph-display-size:clamp(100px,36vw,60vh)}}
.cards{{grid-template-columns:minmax(0,1fr)}}
.pair{{flex-wrap:wrap;gap:24px}}
.master,.glyph{{height:calc(var(--glyph-display-size) * 1.2);width:auto}}
.master svg{{width:calc(var(--glyph-display-size) * {ADVANCE / UPEM});height:calc(var(--glyph-display-size) * {1.2 * ADVANCE / UPEM})}}
.glyph{{font-size:var(--glyph-display-size);font-weight:400;font-style:normal;font-synthesis:none}}
.themes{{grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr))}}
.panel,.native{{min-width:0}}
.size-row{{flex-direction:column;align-items:stretch;gap:8px;margin:24px 0}}
.size-row .native{{overflow-wrap:anywhere;line-height:1.3}}
.comment-glyph{{font-size:100px;line-height:1.3}}
@media(max-width:600px){{:root{{--glyph-display-size:clamp(100px,80vw,70vh)}}.pair{{flex-direction:column}}}}
</style><main><p class="eyebrow">GART language laboratory · I-13 · font 0.100</p>
<h1>Reubarb Pi, in its own hand.</h1><p class="intro">Five approved forms, now real selectable characters. Compare the original drawings with the font, then inspect the sizes below. This page embeds the actual font and works offline without installation.</p>
<div class="cards">{''.join(cards)}</div><h2>Large reading sizes</h2><p>Only glyphs are enlarged. The comparisons above scale to the window; these samples show 100–256px on light and dark backgrounds while ordinary text stays at its normal size. The original small-size QA proof is retained separately.</p>
<div class="themes"><section class="panel" aria-label="Light background">{rows}</section><section class="panel dark" aria-label="Dark background">{rows}</section></div>
<h2 style="margin-top:32px">In code comments</h2><div class="panel"><pre class="native" style="font-size:24px">// G2 <span class="comment-glyph">&#57600;</span>
// G3 <span class="comment-glyph">&#57601;</span>
// G4 <span class="comment-glyph">&#57602;</span>
// G5 <span class="comment-glyph">&#57603;</span>
// G6 <span class="comment-glyph">&#57604;</span>
// Display specimen only; these marks do not execute.
leg transcriptA</pre></div>
<footer>U+E100–U+E104 are project private-use mappings. The SVG masters remain the shape authority. Font display does not add grammar, grant authority, or perform reconciliation. No scripts, external fonts, tracking, or installation.</footer></main></html>
'''


def write_generated(path: Path, data: bytes) -> None:
    """Write only the fixed artifact tree; do not follow an output symlink."""
    if OUT.resolve() != ROOT / "fonts" / "v0_1" or path.is_symlink():
        raise RuntimeError("Unexpected font output path")
    if not path.resolve().is_relative_to(OUT.resolve()):
        raise RuntimeError("Font output escaped its directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("This fixed font build takes no arguments")
    data = build_font()
    if build_font() != data:
        raise RuntimeError("In-memory builds were not reproducible")
    write_generated(OUT / FONT_NAME, data)
    write_generated(OUT / "font-preview.html", specimen_html(data).encode("utf-8"))
    license_records = []
    for name in TOOLS:
        dist = metadata.distribution(name)
        for entry in sorted(dist.files or (), key=str):
            if any(part.lower().startswith(("license", "licence", "copying", "notice")) for part in entry.parts):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    content = source.read_bytes()
                    filename = f"{name}--{'_'.join(entry.parts[1:])}"
                    write_generated(OUT / "tool-licenses" / filename, content)
                    license_records.append({"tool": name, "file": "tool-licenses/" + filename, "sha256": sha256(content).hexdigest()})
    manifest = {
        "profile": "reubarb-font-i13-0.100", "family": FAMILY, "version": VERSION,
        "font": FONT_NAME, "font_sha256": sha256(data).hexdigest(), "font_bytes": len(data),
        "units_per_em": UPEM, "advance": ADVANCE, "uniform_scale": SCALE,
        "svg_to_font_transform": [SCALE, 0, 0, -SCALE, 0, TOP],
        "ascent": ASCENT, "descent": DESCENT, "line_gap": 0,
        "full_svg_frame_preserved": True, "hint_bytecode": False,
        "embedding": "OS/2 fsType 0x0008; editable embedding for authorized local project use and review",
        "cubic_conversion_max_error_font_units": CUBIC_ERROR,
        "conic_quadratics_per_segment": 2 ** CONIC_SPLITS,
        "stroke_precision": STROKE_PRECISION,
        "tools": TOOLS, "python_profile": "CPython 3.13 / Windows x64",
        "sources": [{"design_id": d, "code_point": f"U+{cp:04X}", "asset": "glyphs/v0_1/" + f, "sha256": h} for d, cp, _, f, h in MASTERS],
        "build_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "requirements_sha256": sha256((ROOT / "font-build-requirements.txt").read_bytes()).hexdigest(),
        "tool_licenses": license_records,
        "installation": "not-performed", "package_acceptance": "pending-user-review",
        "limitations": ["SVGs remain canonical. Cubic conversion is bounded at 0.2 font units; integer rounding adds up to 0.5 per axis. Total stroke/conic conversion error is measured by QA, not analytically bounded here.",
                        "Font rendering is display only; it does not extend source syntax.",
                        "Cross-platform/editor integration requires observation in each target environment.",
                        "No public artwork redistribution license is assigned by this build."],
    }
    write_generated(OUT / "font-manifest.json", (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode())
    print(f"Built {FONT_NAME}: {len(data)} bytes; SHA-256 {sha256(data).hexdigest()}")
    print("Repeated in-memory build is byte-identical. No font installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
