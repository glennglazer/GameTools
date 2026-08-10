"""FastAPI server for the GameTools TES chat interface.

Serves the browser UI and provides REST endpoints for:
  POST /api/chat          — send a message, get a response
  GET/POST /api/settings  — manage API key and preferences
  GET /api/status         — health check / configuration status
"""
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import claude_client
import credentials
import tools as _tools

app = FastAPI(title="GameTools TES", docs_url=None, redoc_url=None)

_UI_DIR: Path | None = None

VALID_CONTEXTS = ["All Games", "Morrowind", "Oblivion", "Skyrim"]


def configure(ui_dir: Path, db_path: Path, rag_dir: Path) -> None:
    """Called by main.py before starting uvicorn."""
    global _UI_DIR
    _UI_DIR = ui_dir
    _tools.DB_PATH = db_path
    claude_client.set_rag_dir(rag_dir)


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


# ─── Static file serving ────────────────────────────────────────────────────

@app.get("/")
def serve_index() -> FileResponse:
    if _UI_DIR is None:
        raise HTTPException(status_code=503, detail="UI not configured")
    return FileResponse(_UI_DIR / "index.html")


@app.get("/{path:path}")
def serve_static(path: str) -> FileResponse:
    if _UI_DIR is None:
        raise HTTPException(status_code=503, detail="UI not configured")
    target = _UI_DIR / path
    if target.exists() and target.is_file():
        return FileResponse(target)
    raise HTTPException(status_code=404, detail="Not found")
