"""GameTools TES — entry point.

Locates data files, starts the FastAPI server on a free port,
and opens the default browser to the chat interface.
"""
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


# ── Startup error log ─────────────────────────────────────────────────────────
# Written to:
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


def _install_log_file_handler() -> None:
    """Attach a FileHandler to the root logger so uvicorn's output also lands
    in startup.log.  Called once at startup; never raises."""
    try:
        import datetime
        log_path = _log_dir() / 'startup.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)-8s %(name)s: %(message)s'
        ))
        root = logging.getLogger()
        root.addHandler(fh)
        root.setLevel(logging.DEBUG)
    except Exception:
        pass


def _step(msg: str) -> None:
    """Print a timestamped step to stdout and write it to the startup log."""
    import datetime
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}"
    print(line, flush=True)
    _write_startup_log(msg)


# ── Executable-directory detection ────────────────────────────────────────────

def _exe_dir() -> Path:
    """Return the directory containing the compiled binary (or this script)."""
    compiled = getattr(sys.modules.get('__main__', None), '__compiled__', False)
    if compiled:
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent


def _find_ui_dir() -> Path:
    return _exe_dir() / "ui"


def _find_rag_dir() -> Path:
    here = _exe_dir()
    compiled_rag = here / "rag"
    if compiled_rag.is_dir():
        return compiled_rag
    source_rag = here.parent.parent / "mcp"
    if source_rag.is_dir():
        return source_rag
    return compiled_rag


def _find_db() -> Path:
    here = _exe_dir()
    compiled_db = here / "data" / "gametools.sqlite3"
    if compiled_db.exists():
        return compiled_db
    source_db = here.parent.parent / "database" / "gametools.sqlite3"
    if source_db.exists():
        return source_db
    return compiled_db


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _open_browser_when_ready(url: str, timeout: float = 30.0) -> None:
    """Poll /api/status until the server responds, then open the browser."""
    import urllib.request
    import urllib.error

    status_url = f"{url}/api/status"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(status_url, timeout=1)
            break
        except urllib.error.HTTPError:
            break  # server responded (even with an error) — it's up
        except (urllib.error.URLError, OSError):
            time.sleep(0.25)

    webbrowser.open(url)


def main() -> None:
    # ── Step 1: freeze_support ─────────────────────────────────────────────────
    import multiprocessing
    multiprocessing.freeze_support()

    # NOTE: we do NOT set WindowsSelectorEventLoopPolicy.
    # uvicorn 0.30+ works correctly with ProactorEventLoop (Windows default in
    # Python 3.8+). Forcing SelectorEventLoop caused silent stalls in the ASGI
    # middleware stack.

    # Attach a file handler to the root logger so uvicorn's output goes to
    # startup.log in addition to the console.
    _install_log_file_handler()
    _step("Step 1: freeze_support + logging configured")

    # ── Step 2: import heavy modules ───────────────────────────────────────────
    import uvicorn
    _step("Step 2: uvicorn imported")

    import server
    _step("Step 3: server module imported")

    # ── Step 3: locate data files ──────────────────────────────────────────────
    db_path = _find_db()
    ui_dir  = _find_ui_dir()
    rag_dir = _find_rag_dir()
    _step(
        f"Step 4: paths resolved\n"
        f"  exe_dir : {_exe_dir()}\n"
        f"  db_path : {db_path}  exists={db_path.exists()}\n"
        f"  ui_dir  : {ui_dir}  exists={ui_dir.is_dir()}\n"
        f"  rag_dir : {rag_dir}  exists={rag_dir.is_dir()}\n"
        f"  pid     : {os.getpid()}"
    )

    if not ui_dir.is_dir():
        msg = f"ERROR: UI directory not found at {ui_dir}"
        print(msg, flush=True)
        _write_startup_log(msg)
        sys.exit(1)

    # ── Step 4: configure server (loads RAG docs, sets DB path) ───────────────
    _step("Step 5: calling server.configure()...")
    server.configure(ui_dir=ui_dir, db_path=db_path, rag_dir=rag_dir)
    _step("Step 6: server.configure() complete")

    # ── Step 5: pick a free port ───────────────────────────────────────────────
    port = _free_port()
    url  = f"http://127.0.0.1:{port}"
    _step(f"Step 7: free port acquired → {url}")

    if not db_path.exists():
        print(
            f"WARNING: Database not found at {db_path}. "
            "Queries will fail until the database is created.",
            file=sys.stderr, flush=True,
        )

    # ── Step 6: start browser watcher thread ───────────────────────────────────
    threading.Thread(
        target=_open_browser_when_ready,
        args=(url,),
        daemon=True,
    ).start()
    _step("Step 8: browser watcher thread started")

    # ── Step 7: start uvicorn ──────────────────────────────────────────────────
    # Use uvicorn.Server directly (rather than uvicorn.run) so we can hand
    # the Server instance to the FastAPI app and let /api/shutdown signal it
    # to stop cleanly via server.should_exit = True.
    _step("Step 9: starting uvicorn server...")
    config     = uvicorn.Config(
        server.app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        http="h11",   # force h11; httptools is a C extension Nuitka can't bundle
        ws="none",
    )
    uv_server  = uvicorn.Server(config)
    server.set_server_instance(uv_server)
    uv_server.run()
    _step("Step 10: uvicorn stopped")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        _write_startup_log("FATAL ERROR:\n" + tb)
        print("FATAL ERROR:", tb, file=sys.stderr, flush=True)
        raise
