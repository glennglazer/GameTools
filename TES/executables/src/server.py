"""FastAPI server for the GameTools TES chat interface.

Serves the browser UI and provides REST endpoints for:
  POST /api/chat          — send a message, get a response
  GET/POST /api/settings  — manage API key and preferences
  GET /api/status         — health check / configuration status
"""
import json
import mimetypes
import os
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

import claude_client
import credentials
import tools as _tools


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Log when uvicorn transitions to 'accepting connections' state."""
    import datetime
    msg = f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Lifespan startup: uvicorn accepting connections"
    print(msg, flush=True)
    _log_request_error("STARTUP", "uvicorn accepting connections", "")
    yield
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Lifespan shutdown: uvicorn stopping", flush=True)
    _log_request_error("SHUTDOWN", "uvicorn shutting down", "")


app = FastAPI(title="GameTools TES", docs_url=None, redoc_url=None, lifespan=_lifespan)

_UI_DIR: Path | None = None

VALID_CONTEXTS = ["All Games", "Morrowind", "Oblivion", "Skyrim"]


def configure(ui_dir: Path, db_path: Path, rag_dir: Path) -> None:
    """Called by main.py before starting uvicorn."""
    global _UI_DIR
    _UI_DIR = ui_dir
    _tools.DB_PATH = db_path
    claude_client.set_rag_dir(rag_dir)


# ── Request error logging ─────────────────────────────────────────────────────

def _log_request_error(method: str, url: str, tb: str) -> None:
    """Append a request-level error to the startup log.  Never raises."""
    try:
        import datetime
        if sys.platform == 'win32':
            base = Path(os.environ.get('APPDATA', Path.home()))
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library' / 'Logs'
        else:
            base = Path.home() / '.local' / 'share'
        log_path = base / 'GameTools TES' / 'startup.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(
                f"\n{'='*60}\n{datetime.datetime.now().isoformat()}\n"
                f"Request error: {method} {url}\n{tb}\n"
            )
    except Exception:
        pass


@app.exception_handler(Exception)
async def _global_exc_handler(request: Request, exc: Exception) -> Response:
    """Catch any unhandled exception, log it, and return a JSON 500."""
    if isinstance(exc, HTTPException):
        # Let FastAPI's built-in HTTPException handler manage 4xx/5xx from routes.
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    _log_request_error(request.method, str(request.url), traceback.format_exc())
    return JSONResponse(status_code=500, content={"error": str(exc)})


# ─── Request / Response models ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    messages: list[dict]          # full conversation history in Anthropic format
    game_context: str = ""        # "Morrowind" | "Oblivion" | "Skyrim" | ""
    model: str = "claude-sonnet-5-20251101"


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[dict]
    warning: str | None
    error: str | None


class SettingsGet(BaseModel):
    api_key_configured: bool
    valid_contexts: list[str]


class SettingsSet(BaseModel):
    api_key: str | None = None
    clear_key: bool = False


class StatusResponse(BaseModel):
    ok: bool
    api_key_configured: bool
    db_connected: bool
    table_count: int


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    api_key_configured = credentials.is_configured()
    db_connected = False
    table_count = 0
    try:
        tables = _tools.list_tables()
        db_connected = True
        table_count = len(tables)
    except Exception:
        pass
    return StatusResponse(
        ok=api_key_configured and db_connected,
        api_key_configured=api_key_configured,
        db_connected=db_connected,
        table_count=table_count,
    )


@app.get("/api/settings", response_model=SettingsGet)
def get_settings() -> SettingsGet:
    return SettingsGet(
        api_key_configured=credentials.is_configured(),
        valid_contexts=VALID_CONTEXTS,
    )


@app.post("/api/settings")
def post_settings(body: SettingsSet) -> dict:
    if body.clear_key:
        credentials.delete_api_key()
        return {"ok": True, "message": "API key cleared."}
    if body.api_key is not None:
        key = body.api_key.strip()
        if not key:
            raise HTTPException(status_code=400, detail="API key cannot be empty.")
        credentials.set_api_key(key)
        return {"ok": True, "message": "API key saved to OS credential store."}
    return {"ok": True, "message": "No changes made."}


@app.post("/api/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest) -> ChatResponse:
    api_key = credentials.get_api_key()
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key not configured. Open Settings to add your Anthropic API key.",
        )
    result = claude_client.chat(
        messages=body.messages,
        api_key=api_key,
        game_context=body.game_context,
        model=body.model,
    )
    return ChatResponse(**result)


# ─── Static file serving ─────────────────────────────────────────────────────
# FileResponse (async streaming) deadlocks on Windows with SelectorEventLoop.
# These routes run in FastAPI's sync thread pool; synchronous read_bytes() is
# the correct approach here and avoids all async file-I/O issues.

@app.get("/")
def serve_index() -> Response:
    if _UI_DIR is None:
        raise HTTPException(status_code=503, detail="UI not configured")
    path = _UI_DIR / "index.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return Response(content=path.read_bytes(), media_type="text/html; charset=utf-8")


@app.get("/{path:path}")
def serve_static(path: str) -> Response:
    if _UI_DIR is None:
        raise HTTPException(status_code=503, detail="UI not configured")
    target = _UI_DIR / path
    if target.exists() and target.is_file():
        media_type, _ = mimetypes.guess_type(str(target))
        return Response(
            content=target.read_bytes(),
            media_type=media_type or "application/octet-stream",
        )
    raise HTTPException(status_code=404, detail="Not found")
