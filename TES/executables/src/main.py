"""GameTools TES — entry point.

Locates data files, starts the FastAPI server on a free port,
and opens the default browser to the chat interface.
"""
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _find_data_dir() -> Path:
    """Locate the data directory next to this executable / script."""
    # When compiled with Nuitka onefile, __file__ is in the extraction dir.
    # When running from source, it's in TES/executables/src/.
    here = Path(__file__).resolve().parent
    # Compiled layout: data/ sits alongside main.py in the extraction dir
    candidate = here / "data"
    if candidate.is_dir():
        return candidate
    # Running from source: data lives two levels up in TES/database/ for the DB
    # and TES/mcp/ for the RAG docs — but we handle that separately.
    return here / "data"   # caller checks what it needs


def _find_ui_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here / "ui"


def _find_rag_dir() -> Path:
    here = Path(__file__).resolve().parent
    # Compiled: rag/ next to main.py
    compiled_rag = here / "rag"
    if compiled_rag.is_dir():
        return compiled_rag
    # Source: TES/mcp/
    source_rag = here.parent.parent.parent / "mcp"
    if source_rag.is_dir():
        return source_rag
    return compiled_rag


def _find_db() -> Path:
    here = Path(__file__).resolve().parent
    # Compiled: data/gametools.sqlite3
    compiled_db = here / "data" / "gametools.sqlite3"
    if compiled_db.exists():
        return compiled_db
    # Source: TES/database/gametools.sqlite3
    source_db = here.parent.parent.parent / "database" / "gametools.sqlite3"
    if source_db.exists():
        return source_db
    return compiled_db   # will fail gracefully in tools.py


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _open_browser(url: str, delay: float = 1.5) -> None:
    """Open browser after a short delay to let the server start."""
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    import uvicorn
    import server

    db_path = _find_db()
    ui_dir = _find_ui_dir()
    rag_dir = _find_rag_dir()

    # Validate critical paths
    if not ui_dir.is_dir():
        print(f"ERROR: UI directory not found at {ui_dir}", file=sys.stderr)
        sys.exit(1)

    server.configure(ui_dir=ui_dir, db_path=db_path, rag_dir=rag_dir)

    port = _free_port()
    url = f"http://127.0.0.1:{port}"

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
        log_level="warning",   # suppress request logs in the terminal
    )


if __name__ == "__main__":
    main()
