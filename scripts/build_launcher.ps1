$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    # Isolated packaging environment: does not change the backend lockfile.
    uv run --no-project --with 'pyinstaller==6.22.3' python scripts/desktop/build.py
    if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed.' }
    Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repoRoot 'dist/AstraLauncher.exe')
} finally {
    Pop-Location
}
