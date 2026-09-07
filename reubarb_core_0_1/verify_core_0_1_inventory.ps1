# I-23 host-only, read-only candidate inventory check. No Reubarb source runs.
# This detects drift against a trusted manifest; it is not a digital signature.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

try {
    if ($args.Count -ne 0) { throw 'This fixed inventory check takes no arguments.' }
    $inventoryRoot = [IO.Path]::GetFullPath($PSScriptRoot)
    $rootPrefix = $inventoryRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $manifestPath = Join-Path $inventoryRoot 'core_0_1_freeze_manifest.json'
    $manifestItem = Get-Item -LiteralPath $manifestPath -Force
    if ($manifestItem.PSIsContainer -or $manifestItem.Length -gt 1048576 -or
        ($manifestItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'The fixed manifest must be a regular file of at most 1 MiB.'
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.format -cne 'reubarb-core-inventory-1' -or
        $manifest.candidate -cne 'core-0.1-i23-candidate-1' -or
        $manifest.algorithm -cne 'SHA256' -or $manifest.file_count -ne 91 -or
        @($manifest.files).Count -ne 91) {
        throw 'Unexpected candidate manifest or file count; expected exactly 91 files.'
    }

    # Validate the entire finite list before hashing any payload file. Reject
    # path aliases, alternate streams, traversal and duplicate Windows paths.
    $seen = @{}
    foreach ($entry in $manifest.files) {
        $name = $entry.path
        if ($name -isnot [string] -or $name.Length -gt 240 -or
            $name -cnotmatch '^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$') {
            throw 'Invalid relative inventory path.'
        }
        foreach ($part in $name.Split('/')) {
            if ($part -in @('.', '..') -or $part.EndsWith('.') -or
                $part -imatch '^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\.|$)') {
                throw 'Disallowed inventory path component.'
            }
        }
        if ($seen.ContainsKey($name)) { throw 'Duplicate inventory path.' }
        $seen[$name] = $true
        if (($entry.bytes -isnot [int] -and $entry.bytes -isnot [long]) -or
            $entry.bytes -lt 0 -or $entry.bytes -gt 16777216 -or
            $entry.sha256 -isnot [string] -or
            $entry.sha256 -cnotmatch '^[0-9a-f]{64}$') {
            throw 'Invalid size or SHA256 in manifest.'
        }
        $full = [IO.Path]::GetFullPath((Join-Path $inventoryRoot $name))
        if (-not $full.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Inventory path escaped the fixed package root.'
        }
    }

    $mismatches = 0
    foreach ($entry in $manifest.files) {
        $current = $inventoryRoot
        $available = $true
        foreach ($part in $entry.path.Split('/')) {
            $current = Join-Path $current $part
            if (-not (Test-Path -LiteralPath $current)) { $available = $false; break }
            $item = Get-Item -LiteralPath $current -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'A listed file or parent directory is a reparse point; stopped.'
            }
        }
        if (-not $available -or $item.PSIsContainer) {
            Write-Output ('MISSING: ' + $entry.path)
            $mismatches++
            continue
        }
        if ($item.Length -ne $entry.bytes -or
            (Get-FileHash -LiteralPath $current -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.sha256) {
            Write-Output ('CHANGED: ' + $entry.path)
            $mismatches++
        }
    }
    if ($mismatches -ne 0) {
        Write-Output ('INVENTORY NOT VERIFIED: ' + $mismatches + ' missing or changed file(s). Nothing was repaired.')
        exit 1
    }
    Write-Output 'INVENTORY VERIFIED: 91 of 91 files match core-0.1-i23-candidate-1. No files were changed.'
    Write-Output 'This is integrity evidence only, not freeze approval or permission to publish.'
    exit 0
} catch {
    Write-Output ('INVENTORY CHECK STOPPED: ' + $_.Exception.Message)
    exit 2
}
