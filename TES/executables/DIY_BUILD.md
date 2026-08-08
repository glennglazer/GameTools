# DIY Build Instructions

Build GameTools TES from source — no pre-built binary required.  
You need Python 3.11, Git, and an Anthropic API key.

---

## 1. Clone the repository

```bash
git clone https://github.com/glennglazer/GameTools.git
cd GameTools
```

---

## 2. Set up Python environment (recommended: virtualenv)

```bash
python3.11 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows (PowerShell)

pip install -r TES/executables/src/requirements.txt
```

---

## 3. Create an empty SQLite database

```bash
mkdir -p TES/database
python3.11 -c "import sqlite3; sqlite3.connect('TES/database/gametools.sqlite3').close()"
```

---

## 4. Run the data pipelines

Each pipeline stage has a script that reads raw data and writes to the database.  
The master update script runs all stages in order:

```bash
python3.11 TES/update_tes.py TES/database/gametools.sqlite3
```

This takes a few minutes (it runs scrapers, parsers, and SQL loaders for all three games).  
On first run it fetches data from the UESP and Fandom wikis — an internet connection is required.

To run individual game pipelines:

```bash
python3.11 TES/update_tes.py TES/database/gametools.sqlite3 --game skyrim
python3.11 TES/update_tes.py TES/database/gametools.sqlite3 --game oblivion
python3.11 TES/update_tes.py TES/database/gametools.sqlite3 --game morrowind
```

---

## 5. Launch the app in development mode

No compilation needed — run directly from source:

```bash
python3.11 TES/executables/src/main.py
```

Your browser opens automatically. On first run, click ⚙ **Settings** and enter your Anthropic API key.

---

## 6. (Optional) Compile to a standalone executable

Run the platform build script from the repo root.  
Requires Nuitka (`pip install nuitka`) plus platform-specific tools:

**Windows** (requires NSIS for the installer):
```powershell
.\TES\executables\scripts\wintel\build_windows.ps1 -Version 1.0.0
```

**macOS Intel** (requires `brew install create-dmg`):
```bash
bash TES/executables/scripts/macos/intel/build_macos_intel.sh 1.0.0
```

**macOS ARM**:
```bash
bash TES/executables/scripts/macos/ARM/build_macos_arm.sh 1.0.0
```

**Cross-platform via GitHub Actions**: Push a `tes-v*` tag to trigger the CI workflow that builds all three platforms automatically. See `.github/workflows/build-tes.yml`.

---

## Directory layout (relevant parts)

```
TES/
├── database/
│   └── gametools.sqlite3       ← populated by step 4
├── executables/
│   ├── src/
│   │   ├── main.py             ← entry point
│   │   ├── server.py           ← FastAPI routes
│   │   ├── tools.py            ← all 36 database tool functions
│   │   ├── claude_client.py    ← Anthropic API tool-use loop
│   │   ├── credentials.py      ← OS-native API key storage
│   │   ├── requirements.txt
│   │   └── ui/
│   │       └── index.html      ← browser chat interface
│   ├── scripts/                ← platform build scripts
│   └── dist/                   ← compiled outputs go here
├── mcp/
│   ├── tes_mcp_server.py       ← MCP server (VS Code / Claude Code integration)
│   └── *.md                    ← RAG rules documents (also used by standalone app)
└── <Game>/<system>/            ← pipeline scripts and raw data
```
