# GameTools TES — Windows build script
# Run from repo root: .\TES\executables\scripts\wintel\build_windows.ps1
# Requirements: Python 3.11+, pip, Nuitka, NSIS 3.x

param(
    [string]$Version = "1.0.0",
    [string]$PythonExe = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot  = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path
$SrcDir    = Join-Path $RepoRoot "TES\executables\src"
$DistDir   = Join-Path $RepoRoot "TES\executables\dist\wintel"
$ScriptDir = $PSScriptRoot
$BuildTmp  = Join-Path $env:TEMP "gametools-build-$$"

Write-Host "=== GameTools TES Windows Build v$Version ===" -ForegroundColor Cyan
Write-Host "Repo:  $RepoRoot"
Write-Host "Src:   $SrcDir"
Write-Host "Dist:  $DistDir"

# ── 1. Install dependencies ──────────────────────────────────────────────────
Write-Host "`n[1/5] Installing Python dependencies..." -ForegroundColor Yellow
& $PythonExe -m pip install -r "$SrcDir\requirements.txt" nuitka zstandard --quiet
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# ── 2. Compile with Nuitka (standalone directory) ────────────────────────────
# --onefile is NOT used: it extracts to %TEMP% at runtime, which means
# sys.argv[0] no longer points to the data files, causing a silent crash.
# --standalone produces a directory; NSIS installs the whole tree.
Write-Host "`n[2/5] Compiling with Nuitka (standalone)..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $BuildTmp | Out-Null

$NuitkaArgs = @(
    "-m", "nuitka",
    "--standalone",
    "--windows-console-mode=disable",       # no console window in production
    "--windows-icon-from-ico=$RepoRoot\TES\executables\assets\gametools.ico",
    "--include-data-dir=$SrcDir\ui=ui",
    "--include-data-dir=$RepoRoot\TES\mcp=rag",
    "--include-data-files=$RepoRoot\TES\database\gametools.sqlite3=data/gametools.sqlite3",
    "--output-filename=GameToolsTES.exe",
    "--output-dir=$BuildTmp",
    "--assume-yes-for-downloads",
    "--nofollow-import-to=uvloop",          # uvloop is Unix-only; exclude it
    "--nofollow-import-to=websockets",      # not used; version probe crashes on Windows
    "--nofollow-import-to=httptools",       # C extension; Nuitka stub missing HttpRequestParser
    "--include-module=h11",                 # uvicorn's HTTP/1.1 parser (force-include)
    "--include-module=asyncio.windows_events",  # Windows ProactorEventLoop; force-include
    "$SrcDir\main.py"
)
& $PythonExe @NuitkaArgs
if ($LASTEXITCODE -ne 0) { throw "Nuitka compilation failed" }

# Nuitka standalone names the output directory from the input file (main.dist).
$StandaloneDir = Get-ChildItem -Path $BuildTmp -Filter "*.dist" -Directory |
                 Select-Object -First 1
if (-not $StandaloneDir) { throw "No .dist directory found in $BuildTmp" }
Write-Host "Standalone output: $($StandaloneDir.FullName)"

# ── 3. Build NSIS installer ──────────────────────────────────────────────────
Write-Host "`n[3/5] Building NSIS installer..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
$NsiScript = Join-Path $ScriptDir "gametools_tes.nsi"
$NsisExe   = "makensis"
try {
    & $NsisExe `
        "/DVERSION=$Version" `
        "/DSRC_DIR=$($StandaloneDir.FullName)" `
        "/DOUT_DIR=$DistDir" `
        "$NsiScript"
    if ($LASTEXITCODE -ne 0) { throw "NSIS failed" }
} catch {
    Write-Warning "NSIS not found or failed — skipping installer creation."
    Write-Warning "Install NSIS 3.x from https://nsis.sourceforge.io/Download and re-run."
}

# ── 4. Copy README ───────────────────────────────────────────────────────────
Write-Host "`n[4/5] Copying README..." -ForegroundColor Yellow
Copy-Item "$RepoRoot\TES\executables\README.md" "$DistDir\README.md" -Force -ErrorAction SilentlyContinue

# ── 5. Verify ────────────────────────────────────────────────────────────────
Write-Host "`n[5/5] Artifacts in $DistDir:" -ForegroundColor Yellow
Get-ChildItem $DistDir | Format-Table Name, Length, LastWriteTime

Write-Host "`n=== Build complete! ===" -ForegroundColor Green
