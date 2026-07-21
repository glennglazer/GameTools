"""TES GameTools MCP server — Morrowind, Oblivion, and Skyrim."""
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

_SCRIPT_DIR = Path(__file__).parent
_DB = (_SCRIPT_DIR.parent / 'database' / 'gametools.sqlite3').resolve()

# Read-only engine: the creator opens the file via SQLite URI mode=ro so no
# tool can accidentally mutate the database.
_engine = create_engine(
    "sqlite+pysqlite://",
    creator=lambda: sqlite3.connect(f"file:{_DB}?mode=ro", uri=True),
    poolclass=NullPool,
)

mcp = FastMCP("TES GameTools")


def _query(sql: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only SQL query and return rows as plain dicts."""
    with _engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


# ─── utility ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_tables() -> list[str]:
    """List all tables in the TES GameTools database."""
    rows = _query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r['name'] for r in rows]


# ─── Skyrim alchemy ─────────────────────────────────────────────────────────


# ─── Oblivion alchemy ───────────────────────────────────────────────────────


# ─── Morrowind alchemy ──────────────────────────────────────────────────────


# ─── Morrowind enchanting ───────────────────────────────────────────────────


# ─── Oblivion enchanting ────────────────────────────────────────────────────


# ─── Skyrim enchanting ──────────────────────────────────────────────────────


# ─── Skyrim smithing ────────────────────────────────────────────────────────


# ─── Skyrim homestead ───────────────────────────────────────────────────────


if __name__ == '__main__':
    mcp.run()
