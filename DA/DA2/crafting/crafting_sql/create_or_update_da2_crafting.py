#!/usr/bin/env python3
"""
create_or_update_da2_crafting.py
Loads DA2 crafting JSON records into the DA family SQLite database.

Usage:
    python3 create_or_update_da2_crafting.py \\
        <locations_json> <resources_json> <recipes_json> <effects_json> \\
        [<db_path>]

All arguments have sensible defaults pointing to sibling JSON files and
DA/database/gametools.sqlite3.
"""

import argparse
import json
import pandas as pd
import sqlite3
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
# crafting_sql/ → crafting/ → DA2/ → DA/
_DEFAULT_DB = _SCRIPT_DIR.parent.parent.parent / "database" / "gametools.sqlite3"
_JSON_DIR = _SCRIPT_DIR.parent / "crafting_json"

_DEFAULT_LOCATIONS = _JSON_DIR / "da2_crafting_recipe_locations.json"
_DEFAULT_RESOURCES = _JSON_DIR / "da2_crafting_resources.json"
_DEFAULT_RECIPES   = _JSON_DIR / "da2_crafting_recipes.json"
_DEFAULT_EFFECTS   = _JSON_DIR / "da2_crafting_item_effects.json"

# Column order for the sparse ingredients table
_INGREDIENT_COLS = [
    "Ambrosia", "Deathroot", "Deep Mushroom", "Dragon's Blood",
    "Elfroot", "Embrium", "Felandaris", "Glitterdust",
    "Lyrium", "Orichalcum", "Silverite", "Spindleweed",
]


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def full_replace(df: pd.DataFrame, table: str, conn: sqlite3.Connection) -> None:
    """Delete all rows (if table exists) then insert new rows."""
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
    """Create unique indexes idempotently (IF NOT EXISTS)."""
    statements = [
        ("idx_da2_crl_name",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_da2_crl_name "
         "ON da2_crafting_recipe_locations (name)"),
        ("idx_da2_cr_pk",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_da2_cr_pk "
         "ON da2_crafting_resources (name, location, description, act)"),
        ("idx_da2_crec_name",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_da2_crec_name "
         "ON da2_crafting_recipes (name)"),
        ("idx_da2_cie_name",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_da2_cie_name "
         "ON da2_crafting_item_effects (name)"),
    ]
    cur = conn.cursor()
    for idx_name, ddl in statements:
        existing = cur.execute(
            f"SELECT name FROM sqlite_master WHERE type='index' AND name='{idx_name}'"
        ).fetchone()
        if existing is None:
            cur.execute(ddl)
    conn.commit()


def run_loader(
    locations_path: Path,
    resources_path: Path,
    recipes_path: Path,
    effects_path: Path,
    db_path: Path,
) -> None:
    print("Starting database update for DA2 Crafting")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")

    # ── recipe locations ──────────────────────────────────────────────────
    df_locs = pd.DataFrame(load_json(locations_path))
    full_replace(df_locs, "da2_crafting_recipe_locations", conn)

    # ── crafting resources ────────────────────────────────────────────────
    df_res = pd.DataFrame(load_json(resources_path))
    full_replace(df_res, "da2_crafting_resources", conn)

    # ── crafting recipes (sparse ingredient table) ────────────────────────
    recipes_data = load_json(recipes_path)
    if recipes_data:
        df_rec = pd.DataFrame(recipes_data)
        # Ensure all ingredient columns are present with 0 as default
        for col in _INGREDIENT_COLS:
            if col not in df_rec.columns:
                df_rec[col] = 0
        col_order = ["name"] + _INGREDIENT_COLS + ["Gold", "Silver", "Bronze"]
        df_rec = df_rec[col_order]
    else:
        df_rec = pd.DataFrame(columns=["name"] + _INGREDIENT_COLS + ["Gold", "Silver", "Bronze"])
    full_replace(df_rec, "da2_crafting_recipes", conn)

    # ── item effects ──────────────────────────────────────────────────────
    df_eff = pd.DataFrame(load_json(effects_path))
    full_replace(df_eff, "da2_crafting_item_effects", conn)

    # ── indexes ───────────────────────────────────────────────────────────
    create_unique_indexes(conn)

    conn.close()
    print("Database update complete for DA2 Crafting (4 tables).")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Load DA2 Crafting JSON records into the DA family SQLite DB"
    )
    ap.add_argument("locations_json", nargs="?", default=str(_DEFAULT_LOCATIONS))
    ap.add_argument("resources_json", nargs="?", default=str(_DEFAULT_RESOURCES))
    ap.add_argument("recipes_json",   nargs="?", default=str(_DEFAULT_RECIPES))
    ap.add_argument("effects_json",   nargs="?", default=str(_DEFAULT_EFFECTS))
    ap.add_argument("db",             nargs="?", default=str(_DEFAULT_DB))
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    run_loader(
        Path(args.locations_json),
        Path(args.resources_json),
        Path(args.recipes_json),
        Path(args.effects_json),
        db_path,
    )


if __name__ == "__main__":
    main()
