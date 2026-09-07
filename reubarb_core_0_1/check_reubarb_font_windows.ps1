# Native Windows WPF proof; direct local font URI, no installation or GUI.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore, WindowsBase
$fontRoot = Join-Path $PSScriptRoot 'fonts\v0_1'
$fontPath = Join-Path $fontRoot 'ReubarbPiSymbols-Regular.ttf'
$fontBefore = (Get-FileHash -LiteralPath $fontPath -Algorithm SHA256).Hash
$glyphFace = [System.Windows.Media.GlyphTypeface]::new([Uri]::new($fontPath))
if ($glyphFace.GlyphCount -ne 6 -or $glyphFace.CharacterToGlyphMap.Count -ne 5) {
    throw 'Unexpected native Windows glyph inventory.'
}
foreach ($fontOffset in 0..4) {
    $fontGid = $glyphFace.CharacterToGlyphMap[0xE100 + $fontOffset]
    if ($fontGid -ne $fontOffset + 1) { throw 'Windows mapping mismatch.' }
    if ([Math]::Abs($glyphFace.AdvanceWidths[$fontGid] - 1233.0 / 2048) -gt 0.000001) {
        throw 'Windows character advance mismatch.'
    }
}
$fontVisual = [System.Windows.Media.DrawingVisual]::new()
$fontDrawing = $fontVisual.RenderOpen()
try {
    $fontDrawing.DrawRectangle([System.Windows.Media.Brushes]::White, $null,
        [System.Windows.Rect]::new(0, 0, 1100, 840))
    $fontLabels = [System.Windows.Media.Typeface]::new('Segoe UI')
    $fontHeader = [System.Windows.Media.FormattedText]::new(
        'Reubarb Pi - native Windows font proof', [Globalization.CultureInfo]::InvariantCulture,
        [System.Windows.FlowDirection]::LeftToRight, $fontLabels, 30,
        [System.Windows.Media.Brushes]::Black, 1.0)
    $fontDrawing.DrawText($fontHeader, [System.Windows.Point]::new(32, 24))
    $fontRow = 0
    foreach ($fontSize in @(12, 14, 16, 18, 20, 22, 24, 32, 48, 128)) {
        $fontY = 100 + 58 * $fontRow
        $fontLabel = [System.Windows.Media.FormattedText]::new(
            "$fontSize px", [Globalization.CultureInfo]::InvariantCulture,
            [System.Windows.FlowDirection]::LeftToRight, $fontLabels, 18,
            [System.Windows.Media.Brushes]::Black, 1.0)
        $fontDrawing.DrawText($fontLabel, [System.Windows.Point]::new(32, $fontY - 20))
        $fontIndices = [System.Collections.Generic.List[UInt16]]::new()
        $fontAdvances = [System.Collections.Generic.List[Double]]::new()
        foreach ($fontOffset in 0..4) {
            $fontIndices.Add([UInt16]($fontOffset + 1))
            $fontAdvances.Add($fontSize * 1233.0 / 2048)
        }
        $fontRun = [System.Windows.Media.GlyphRun]::new($glyphFace, 0, $false,
            [double]$fontSize, $fontIndices, [System.Windows.Point]::new(155, $fontY),
            $fontAdvances, $null, $null, $null, $null, $null, $null)
        $fontDrawing.DrawGlyphRun([System.Windows.Media.Brushes]::Black, $fontRun)
        $fontRow++
    }
    $fontNote = [System.Windows.Media.FormattedText]::new(
        'Loaded directly from the local TTF. No font registration or editor setting changed.',
        [Globalization.CultureInfo]::InvariantCulture, [System.Windows.FlowDirection]::LeftToRight,
        $fontLabels, 18, [System.Windows.Media.Brushes]::Black, 1.0)
    $fontDrawing.DrawText($fontNote, [System.Windows.Point]::new(32, 760))
}
finally { $fontDrawing.Close() }
$fontBitmap = [System.Windows.Media.Imaging.RenderTargetBitmap]::new(1100, 840, 96, 96,
    [System.Windows.Media.PixelFormats]::Pbgra32)
$fontBitmap.Render($fontVisual)
$fontEncoder = [System.Windows.Media.Imaging.PngBitmapEncoder]::new()
$fontEncoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($fontBitmap))
$fontProof = Join-Path $fontRoot 'font-windows-proof.png'
$fontStream = [IO.File]::Open($fontProof, [IO.FileMode]::Create)
try { $fontEncoder.Save($fontStream) } finally { $fontStream.Dispose() }
if ((Get-FileHash -LiteralPath $fontPath -Algorithm SHA256).Hash -ne $fontBefore) {
    throw 'The font changed during its native Windows check.'
}
Write-Output 'Windows WPF font checks passed: 5 mappings, 6 glyphs, exact cell widths, 10 rendered sizes.'
Write-Output 'Created fonts/v0_1/font-windows-proof.png; no font installed.'
