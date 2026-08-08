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

# ── 2. Compile with Nuitka ───────────────────────────────────────────────────
Write-Host "`n[2/5] Compiling with Nuitka (onefile)..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $BuildTmp | Out-Null

$NuitkaArgs = @(
    "-m", "nuitka",
    "--onefile",
    "--standalone",
    "--windows-console-mode=disable",       # no console window
    "--windows-icon-from-ico=$RepoRoot\TES\executables\assets\gametools.ico",
    "--include-data-dir=$SrcDir\ui=ui",
    "--include-data-dir=$RepoRoot\TES\mcp=rag",
    "--include-data-files=$RepoRoot\TES\database\gametools.sqlite3=data/gametools.sqlite3",
    "--output-filename=GameToolsTES.exe",
    "--output-dir=$BuildTmp",
    "--assume-yes-for-downloads",
    "--enable-plugin=anti-bloat",
    "--nofollow-import-to=tkinter,unittest,email,html,xml,xmlrpc,logging.handlers",
    "$SrcDir\main.py"
)
& $PythonExe @NuitkaArgs
if ($LASTEXITCODE -ne 0) { throw "Nuitka compilation failed" }

# ── 3. Copy to dist ──────────────────────────────────────────────────────────
Write-Host "`n[3/5] Copying to dist..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
Copy-Item "$BuildTmp\GameToolsTES.exe" "$DistDir\GameToolsTES.exe" -Force
Copy-Item "$RepoRoot\TES\executables\dist\wintel\README.md" "$DistDir\README.md" -Force -ErrorAction SilentlyContinue

# ── 4. Build NSIS installer ──────────────────────────────────────────────────
Write-Host "`n[4/5] Building NSIS installer..." -ForegroundColor Yellow
$NsiScript = Join-Path $ScriptDir "gametools_tes.nsi"
$NsisExe   = "makensis"
try {
    & $NsisExe /DVERSION=$Version /DSRC_EXE="$DistDir\GameToolsTES.exe" `
               /DOUT_DIR="$DistDir" $NsiScript
    if ($LASTEXITCODE -ne 0) { throw "NSIS failed" }
} catch {
    Write-Warning "NSIS not found or failed — skipping installer creation. Install NSIS and re-run step 4."
    Write-Warning "Download: https://nsis.sourceforge.io/Download"
}

# ── 5. Verify ────────────────────────────────────────────────────────────────
Write-Host "`n[5/5] Artifacts in $DistDir:" -ForegroundColor Yellow
Get-ChildItem $DistDir | Format-Table Name, Length, LastWriteTime

Write-Host "`n=== Build complete! ===" -ForegroundColor Green
