#!/usr/bin/env python3
"""
create_or_update_awakening_runecrafting.py
Loads DAO:A Runecrafting JSON records into the DAO:A SQLite database.

Usage:
    python3 create_or_update_awakening_runecrafting.py \\
        <skill_json> <tracing_json> <hybrid_tracing_json> \\
        <armor_runes_json> <weapon_runes_json> <costs_json> \\
        [<db_path>]

All arguments have sensible defaults pointing to sibling JSON files and
DA/Awakening/database/gametools.sqlite3.
"""

import argparse
import json
import pandas as pd
import sqlite3
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
# runecrafting_sql/ → runecrafting/ → Awakening/ → database/
_DEFAULT_DB = _SCRIPT_DIR.parent.parent / "database" / "gametools.sqlite3"
_JSON_DIR = _SCRIPT_DIR.parent / "runecrafting_json"

_DEFAULT_SKILL      = _JSON_DIR / "awakening_runecrafting_skill.json"
_DEFAULT_TRACING    = _JSON_DIR / "awakening_runecrafting_tracing_acquisition.json"
_DEFAULT_HYBRID     = _JSON_DIR / "awakening_runecrafting_hybrid_tracing_acquisition.json"
_DEFAULT_ARMOR      = _JSON_DIR / "awakening_runecrafting_armor_runes.json"
_DEFAULT_WEAPON     = _JSON_DIR / "awakening_runecrafting_weapon_runes.json"
_DEFAULT_COSTS      = _JSON_DIR / "awakening_runecrafting_costs.json"

# All six tables use full-replace (static wiki data, small row counts)
_TABLES = [
    "awakening_runecrafting_skill",
    "awakening_runecrafting_tracing_acquisition",
    "awakening_runecrafting_hybrid_tracing_acquisition",
    "awakening_runecrafting_armor_runes",
    "awakening_runecrafting_weapon_runes",
    "awakening_runecrafting_costs",
]


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def full_replace(df: pd.DataFrame, table: str, conn: sqlite3.Connection) -> None:
    """Delete all rows in table (if it exists) then insert new rows.

    Creates the table and its unique index on first run.
    """
    cur = conn.cursor()
    exists = cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
    ).fetchone()
    if exists is not None:
        cur.execute(f"DELETE FROM {table}")
        conn.commit()
    df.to_sql(table, conn, if_exists="append", method="multi", index=False)
    print(f"    Upserted {len(df)} rows → {table}")


def create_unique_indexes(conn: sqlite3.Connection) -> None:
    """Create unique indexes on first run (idempotent via IF NOT EXISTS)."""
    cur = conn.cursor()
    indexes = [
        ("idx_awrc_skill",      "awakening_runecrafting_skill",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_awrc_skill "
         "ON awakening_runecrafting_skill (level)"),
        ("idx_awrc_tracing",    "awakening_runecrafting_tracing_acquisition",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_awrc_tracing "
         "ON awakening_runecrafting_tracing_acquisition (tracing)"),
        ("idx_awrc_hybrid",     "awakening_runecrafting_hybrid_tracing_acquisition",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_awrc_hybrid "
         "ON awakening_runecrafting_hybrid_tracing_acquisition (tracing)"),
        ("idx_awrc_armor",      "awakening_runecrafting_armor_runes",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_awrc_armor "
         "ON awakening_runecrafting_armor_runes (name, level)"),
        ("idx_awrc_weapon",     "awakening_runecrafting_weapon_runes",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_awrc_weapon "
         "ON awakening_runecrafting_weapon_runes (name, level)"),
        ("idx_awrc_costs",      "awakening_runecrafting_costs",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_awrc_costs "
         "ON awakening_runecrafting_costs (name)"),
    ]
    for idx_name, table, ddl in indexes:
        # Only create if the table was just made (check by verifying index absence)
        existing = cur.execute(
            f"SELECT name FROM sqlite_master WHERE type='index' AND name='{idx_name}'"
        ).fetchone()
        if existing is None:
            cur.execute(ddl)
    conn.commit()


def run_loader(
    skill_path: Path,
    tracing_path: Path,
    hybrid_path: Path,
    armor_path: Path,
    weapon_path: Path,
    costs_path: Path,
    db_path: Path,
) -> None:
    print("Starting database update for DAO:A Runecrafting")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")

    # ── skill tiers ───────────────────────────────────────────────────────
    df_skill = pd.DataFrame(load_json(skill_path))
    full_replace(df_skill, "awakening_runecrafting_skill", conn)

    # ── tracing acquisition ───────────────────────────────────────────────
    df_tracing = pd.DataFrame(load_json(tracing_path))
    full_replace(df_tracing, "awakening_runecrafting_tracing_acquisition", conn)

    # ── hybrid tracing ────────────────────────────────────────────────────
    df_hybrid = pd.DataFrame(load_json(hybrid_path))
    full_replace(df_hybrid, "awakening_runecrafting_hybrid_tracing_acquisition", conn)

    # ── armor runes ───────────────────────────────────────────────────────
    df_armor = pd.DataFrame(load_json(armor_path))
    full_replace(df_armor, "awakening_runecrafting_armor_runes", conn)

    # ── weapon runes ──────────────────────────────────────────────────────
    df_weapon = pd.DataFrame(load_json(weapon_path))
    full_replace(df_weapon, "awakening_runecrafting_weapon_runes", conn)

    # ── costs ─────────────────────────────────────────────────────────────
    df_costs = pd.DataFrame(load_json(costs_path))
    full_replace(df_costs, "awakening_runecrafting_costs", conn)

    # ── indexes ───────────────────────────────────────────────────────────
    create_unique_indexes(conn)

    conn.close()
    print("Database update complete for DAO:A Runecrafting (6 tables).")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Load DAO:A Runecrafting JSON records into SQLite"
    )
    ap.add_argument("skill_json",   nargs="?", default=str(_DEFAULT_SKILL))
    ap.add_argument("tracing_json", nargs="?", default=str(_DEFAULT_TRACING))
    ap.add_argument("hybrid_json",  nargs="?", default=str(_DEFAULT_HYBRID))
    ap.add_argument("armor_json",   nargs="?", default=str(_DEFAULT_ARMOR))
    ap.add_argument("weapon_json",  nargs="?", default=str(_DEFAULT_WEAPON))
    ap.add_argument("costs_json",   nargs="?", default=str(_DEFAULT_COSTS))
    ap.add_argument("db",           nargs="?", default=str(_DEFAULT_DB))
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    run_loader(
        Path(args.skill_json),
        Path(args.tracing_json),
        Path(args.hybrid_json),
        Path(args.armor_json),
        Path(args.weapon_json),
        Path(args.costs_json),
        db_path,
    )


if __name__ == "__main__":
    main()
