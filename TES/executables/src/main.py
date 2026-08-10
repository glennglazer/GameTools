"""GameTools TES — entry point.

Locates data files, starts the FastAPI server on a free port,
and opens the default browser to the chat interface.
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


# ── Startup error log ─────────────────────────────────────────────────────────
# When compiled with --windows-console-mode=disable there is no terminal to
# show exceptions.  Any unhandled error during startup is written here so users
# can report it.
#
#   Windows : %APPDATA%\GameTools TES\startup.log
#   macOS   : ~/Library/Logs/GameTools TES/startup.log
#   Linux   : ~/.local/share/GameTools TES/startup.log

def _log_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Logs'
    else:
        base = Path.home() / '.local' / 'share'
    return base / 'GameTools TES'


def _write_startup_log(content: str) -> None:
    """Append a timestamped entry to the startup log.  Never raises."""
    try:
        import datetime
        log_path = _log_dir() / 'startup.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n{datetime.datetime.now().isoformat()}\n{content}\n")
    except Exception:
        pass


# ── Executable-directory detection ────────────────────────────────────────────

def _exe_dir() -> Path:
    """Return the directory that contains the compiled binary (or this script).

    In Nuitka standalone mode sys.argv[0] is the real executable path, which is
    exactly where --include-data-dir / --include-data-files puts the bundled
    data.  When running from source, sys.argv[0] is the Python interpreter or
    the script path, both of which lack 'data/' and 'ui/' siblings, so we fall
    back to __file__ (this script's location in TES/executables/src/).
    """
    compiled = getattr(sys.modules.get('__main__', None), '__compiled__', False)
    if compiled:
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent


def _find_ui_dir() -> Path:
    here = _exe_dir()
    return here / "ui"


def _find_rag_dir() -> Path:
    here = _exe_dir()
    compiled_rag = here / "rag"
    if compiled_rag.is_dir():
        return compiled_rag
    # Source layout: TES/executables/src/ → TES/executables/ → TES/ → TES/mcp/
    source_rag = here.parent.parent / "mcp"
    if source_rag.is_dir():
        return source_rag
    return compiled_rag   # will fail gracefully in claude_client.py


def _find_db() -> Path:
    here = _exe_dir()
    compiled_db = here / "data" / "gametools.sqlite3"
    if compiled_db.exists():
        return compiled_db
    # Source layout: TES/executables/src/ → TES/executables/ → TES/ → TES/database/
    source_db = here.parent.parent / "database" / "gametools.sqlite3"
    if source_db.exists():
        return source_db
    return compiled_db   # caller reports the missing file


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _open_browser(url: str, delay: float = 1.5) -> None:
    """Open browser after a short delay to let the server start."""
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    # ── Windows frozen-executable setup ───────────────────────────────────────
    # freeze_support() must be the very first call in a frozen Windows entry
    # point.  It is a no-op on macOS/Linux and when running from source.
    import multiprocessing
    multiprocessing.freeze_support()

    # uvicorn requires SelectorEventLoop; Windows Python 3.8+ defaults to
    # ProactorEventLoop (incompatible).  Set the policy before any async code.
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # ── end Windows setup ─────────────────────────────────────────────────────

    import uvicorn
    import server

    db_path = _find_db()
    ui_dir  = _find_ui_dir()
    rag_dir = _find_rag_dir()

    _write_startup_log(
        f"Starting GameTools TES\n"
        f"  exe_dir : {_exe_dir()}\n"
        f"  db_path : {db_path}  exists={db_path.exists()}\n"
        f"  ui_dir  : {ui_dir}  exists={ui_dir.is_dir()}\n"
        f"  rag_dir : {rag_dir}  exists={rag_dir.is_dir()}\n"
    )

    if not ui_dir.is_dir():
        msg = f"ERROR: UI directory not found at {ui_dir}"
        print(msg, file=sys.stderr)
        _write_startup_log(msg)
        sys.exit(1)

    server.configure(ui_dir=ui_dir, db_path=db_path, rag_dir=rag_dir)

    port = _free_port()
    url  = f"http://127.0.0.1:{port}"

    print(f"GameTools TES starting at {url}")
    if not db_path.exists():
        print(f"WARNING: Database not found at {db_path}. "
              "Queries will fail until the database is created.", file=sys.stderr)

    # Open browser in a background thread
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    uvicorn.run(
        server.app,
        host="127.0.0.1",
        port=port,
        log_level="warning",   # suppress per-request logs in the terminal
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        _write_startup_log("FATAL ERROR:\n" + traceback.format_exc())
        raise
