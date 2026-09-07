"""Packages I-1 through I-21: one foreground, fixed-suite laboratory test command.

No transcript input or path discovery. I-13 reads one fixed comment-only font
specimen; there is no personal source loading or source execution.
"""
from __future__ import annotations

import sys

# Also suppress normal imported-bytecode writes when launched by an editor.
sys.dont_write_bytecode = True

from hashlib import sha256
from pathlib import Path
import unittest

_EXACT_FILES = (
    "core_0_1_transport_kernel.py",
    "test_core_0_1_transport_kernel.py",
    "core_0_1_transcript_runtime.py",
    "test_core_0_1_transcript_runtime.py",
    "test_core_0_1_package_boundaries.py",
    "run_core_0_1_checks.py",
    "core_0_1_source_profile.py",
    "test_core_0_1_source_profile.py",
    "core_0_1_lexical_frontend.py",
    "test_core_0_1_lexical_frontend.py",
    "core_0_1_syntax_skeleton.py",
    "test_core_0_1_syntax_skeleton.py",
    "core_0_1_read_instruction.py",
    "test_core_0_1_read_instruction.py",
    "core_0_1_glyph_technical.py",
    "test_core_0_1_glyph_technical.py",
    "run_core_0_1_glyph_checks.py",
    "core_0_1_glyph_geometry.py",
    "test_core_0_1_glyph_geometry.py",
    "run_core_0_1_glyph_geometry_checks.py",
    "glyphs/v0_1/rp_component_four_dot_frame.svg",
    "glyphs/v0_1/rp_g02_congruent_statement.svg",
    "glyphs/v0_1/rp_g03_fulfilled_overlay.svg",
    "glyphs/v0_1/rp_g04_strong_variant.svg",
    "glyphs/v0_1/rp_g05_neutral_variant.svg",
    "glyphs/v0_1/rp_g06_weak_variant.svg",
    "core_0_1_glyph_encoding.py",
    "test_core_0_1_glyph_encoding.py",
    "run_core_0_1_glyph_encoding_checks.py",
    ".vscode/reubarb-glyphs.code-snippets",
    "core_0_1_glyph_recognizer.py",
    "test_core_0_1_glyph_recognizer.py",
    "run_core_0_1_glyph_recognition_checks.py",
    "core_0_1_glyph_display.py",
    "test_core_0_1_glyph_display.py",
    "run_core_0_1_glyph_display_checks.py",
    "reubarb_glyph_encoding_preview.html",
    "test_core_0_1_glyph_font.py",
    "core_0_1_glyph_source_integration.py",
    "test_core_0_1_glyph_source_integration.py",
    "run_core_0_1_glyph_source_integration_checks.py",
    "core_0_1_glyph_identity_value.py",
    "test_core_0_1_glyph_identity_value.py",
    "run_core_0_1_glyph_identity_value_checks.py",
    "core_0_1_occurrence_continuity.py",
    "test_core_0_1_occurrence_continuity.py",
    "run_core_0_1_occurrence_continuity_checks.py",
    "test_core_0_1_glyph_identity_path.py",
    "run_core_0_1_glyph_identity_path_checks.py",
    "test_core_0_1_reviewed_text_path.py",
    "run_core_0_1_reviewed_text_path_checks.py",
    "run_core_0_1_checks_full.py",
    "run_core_0_1_foundation_checks.py",
    "build_reubarb_font.py",
    "check_reubarb_font.py",
    "check_reubarb_font_windows.ps1",
    "font-build-requirements.txt",
    "fonts/v0_1/ReubarbPiSymbols-Regular.ttf",
    "fonts/v0_1/font-manifest.json",
    "fonts/v0_1/font-validation.json",
    "fonts/v0_1/font-proof.png",
    "fonts/v0_1/font-preview.html",
    "fonts/v0_1/glyph-specimen.gart",
)


def _snapshot(root: Path) -> dict[str, str]:
    """Hash exactly the fixed gate files; never enumerate a directory."""
    result: dict[str, str] = {}
    for name in _EXACT_FILES:
        digest = sha256()
        with (root / name).open("rb") as source:
            while chunk := source.read(65536):
                digest.update(chunk)
        result[name] = digest.hexdigest()
    return result


def main() -> int:
    if sys.version_info[:2] != (3, 13):
        print(
            "Use Python 3.13 for this laboratory check. No installation was attempted.",
            file=sys.stderr,
        )
        return 2
    if len(sys.argv) != 1:
        print("This check takes no arguments or transcript input.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    missing = tuple(name for name in _EXACT_FILES if not (root / name).is_file())
    if missing:
        print("Keep these files beside this runner: " + ", ".join(missing), file=sys.stderr)
        return 2

    try:
        before = _snapshot(root)
    except OSError:
        print(
            "Could not read one of the fixed gate files. Nothing was rewritten.",
            file=sys.stderr,
        )
        return 2

    import importlib
    from types import ModuleType

    modules: tuple[tuple[str, str], ...] = (
        ("i1", "test_core_0_1_transport_kernel"),
        ("i2", "test_core_0_1_transcript_runtime"),
        ("i3", "test_core_0_1_package_boundaries"),
        ("i4", "test_core_0_1_source_profile"),
        ("i5", "test_core_0_1_lexical_frontend"),
        ("i6", "test_core_0_1_syntax_skeleton"),
        ("i7", "test_core_0_1_read_instruction"),
        ("i8", "test_core_0_1_glyph_technical"),
        ("i9", "test_core_0_1_glyph_geometry"),
        ("i10", "test_core_0_1_glyph_encoding"),
        ("i11", "test_core_0_1_glyph_recognizer"),
        ("i12", "test_core_0_1_glyph_display"),
        ("i13", "test_core_0_1_glyph_font"),
        ("i15", "test_core_0_1_glyph_source_integration"),
        ("i16", "test_core_0_1_glyph_identity_value"),
        ("i18", "test_core_0_1_occurrence_continuity"),
        ("i20", "test_core_0_1_glyph_identity_path"),
        ("i21", "test_core_0_1_reviewed_text_path"),
    )

    loaded: dict[str, ModuleType] = {}
    for label, module_name in modules:
        try:
            loaded[label] = importlib.import_module(module_name)
        except (ImportError, SyntaxError) as exc:
            print(
                f"Named laboratory module {module_name!r} could not load: {exc}",
                file=sys.stderr,
            )
            print(
                "A named laboratory module could not load. Check all required gate files.",
                file=sys.stderr,
            )
            return 2

    i1 = loaded["i1"]
    i2 = loaded["i2"]
    i3 = loaded["i3"]
    i4 = loaded["i4"]
    i5 = loaded["i5"]
    i6 = loaded["i6"]
    i7 = loaded["i7"]
    i8 = loaded["i8"]
    i9 = loaded["i9"]
    i10 = loaded["i10"]
    i11 = loaded["i11"]
    i12 = loaded["i12"]
    i13 = loaded["i13"]
    i15 = loaded["i15"]
    i16 = loaded["i16"]
    i18 = loaded["i18"]
    i20 = loaded["i20"]
    i21 = loaded["i21"]

    del loaded, modules, module_name, label
    del importlib

    loader = unittest.TestLoader()
    groups = (
        loader.loadTestsFromTestCase(i1.TransportKernelTests),
        loader.loadTestsFromTestCase(i2.TranscriptRuntimeTests),
        loader.loadTestsFromTestCase(i3.PackageBoundaryTests),
        loader.loadTestsFromTestCase(i4.SourceProfileTests),
        loader.loadTestsFromTestCase(i5.LexicalFrontendTests),
        loader.loadTestsFromTestCase(i6.SyntaxSkeletonTests),
        loader.loadTestsFromTestCase(i7.ReadInstructionTests),
        loader.loadTestsFromTestCase(i8.GlyphTechnicalTests),
        loader.loadTestsFromTestCase(i9.GlyphGeometryTests),
        loader.loadTestsFromTestCase(i10.GlyphEncodingTests),
        loader.loadTestsFromTestCase(i11.GlyphRecognizerTests),
        loader.loadTestsFromTestCase(i12.GlyphDisplayTests),
        loader.loadTestsFromTestCase(i13.GlyphFontTests),
        loader.loadTestsFromTestCase(i15.GlyphSourceIntegrationTests),
        loader.loadTestsFromTestCase(i16.GlyphIdentityValueTests),
        loader.loadTestsFromTestCase(i18.OccurrenceContinuityTests),
        loader.loadTestsFromTestCase(i20.GlyphIdentityPathTests),
        loader.loadTestsFromTestCase(i21.ReviewedTextPathTests),
    )
    counts = tuple(group.countTestCases() for group in groups)
    if counts != (23, 24, 16, 36, 42, 44, 60, 8, 12, 14, 20, 12, 12, 11, 16, 18, 20, 12):
        print(
            "Unexpected test inventory; expected I-1=23, I-2=24, I-3=16, I-4=36, "
            "I-5=42, I-6=44, I-7=60, I-8=8, I-9=12, I-10=14, I-11=20, "
            "I-12=12, I-13=12, I-15=11, I-16=16, I-18=18, I-20=20, "
            "I-21=12. "
            "Stopped.",
            file=sys.stderr,
        )
        return 2

    print(
        "GART laboratory checks: I-1=23, I-2=24, I-3=16, I-4=36, I-5=42, I-6=44, "
        "I-7=60, I-8=8, I-9=12, I-10=14, I-11=20, I-12=12, I-13=12, "
        "I-15=11, I-16=16, I-18=18, I-20=20, I-21=12; total=400.",
        file=sys.stderr,
    )
    print(
        "Synthetic I-7 operations and I-8 through I-21 checks do not interpret or "
        "execute transcript payloads.",
        file=sys.stderr,
    )
    try:
        result = unittest.TextTestRunner(verbosity=2, tb_locals=False).run(
            unittest.TestSuite(groups)
        )
    except KeyboardInterrupt:
        print("Checks interrupted. This run is not a pass.", file=sys.stderr)
        return 130

    try:
        after = _snapshot(root)
    except OSError:
        print(
            "Post-run file verification failed. This run is not accepted as a pass.",
            file=sys.stderr,
        )
        return 2
    if before != after:
        print(
            "A named code file changed during the run. Stop and review; no rollback was run.",
            file=sys.stderr,
        )
        return 2

    complete = (
        result.testsRun == 400
        and result.wasSuccessful()
        and not result.skipped
        and not result.expectedFailures
        and not result.unexpectedSuccesses
    )
    if not complete:
        print(
            "CHECKS NOT COMPLETE: review the test output. No automatic repair was attempted.",
            file=sys.stderr,
        )
        return 1

    print("CHECKS PASSED: 400 of 400. All fixed gate files are unchanged.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
