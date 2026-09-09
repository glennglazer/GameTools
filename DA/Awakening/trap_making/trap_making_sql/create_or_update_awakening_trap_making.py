"""Load DAO:A Trap-Making JSON records into the DAO:A SQLite database.

Creates or upserts five tables:
  awakening_trap_making_recipes            — wide recipe table (plan name → result trap)
  awakening_trap_making_ingredient_recipes — ingredient → recipe reverse-lookup
  awakening_trap_making_tiers              — recipe → required tier (all 4)
  awakening_trap_making_unlimited_supply   — vendor/location (always empty for Awakening)
  awakening_trap_making_effects            — trap name → damage_type/power/effect

Unlike the Origins trap_making_effects table (which uses a composite key on
(name, power, damage_type) to handle Poisoned Caltrop Trap's two rows),
the Awakening effects table is keyed on name alone — no Awakening trap has
dual damage types.

Usage:
    python3 create_or_update_awakening_trap_making.py \\
        <recipes_json> <ingredient_recipes_json> <tiers_json> <supply_json> \\
        <effects_json> <db>
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

_SCRIPT_DIR = Path(__file__).parent.resolve()
# 2 parent calls: trap_making_sql/ → trap_making/ → Awakening/
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent
_JSON_DIR = _SCRIPT_DIR.parent / "trap_making_json"

_DEFAULT_RECIPES = str(_JSON_DIR / "awakening_trap_making_recipes.json")
_DEFAULT_ING_REC = str(_JSON_DIR / "awakening_trap_making_ingredient_recipes.json")
_DEFAULT_TIERS   = str(_JSON_DIR / "awakening_trap_making_tiers.json")
_DEFAULT_SUPPLY  = str(_JSON_DIR / "awakening_trap_making_unlimited_supply.json")
_DEFAULT_EFFECTS = str(_JSON_DIR / "awakening_trap_making_effects.json")
_DEFAULT_DB      = str(_FAMILY_ROOT / "database" / "gametools.sqlite3")

RECIPES_TABLE = "awakening_trap_making_recipes"
ING_REC_TABLE = "awakening_trap_making_ingredient_recipes"
TIERS_TABLE   = "awakening_trap_making_tiers"
SUPPLY_TABLE  = "awakening_trap_making_unlimited_supply"
EFFECTS_TABLE = "awakening_trap_making_effects"

_SUPPLY_COLUMNS = ["ingredient", "vendor", "location", "note"]


def table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    return cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}'"
    ).fetchone() is not None


def load_json(path: str, label: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        print(f"ERROR: {label} JSON not found: {p}", file=sys.stderr)
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def upsert_by_key(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    df: pd.DataFrame,
    table: str,
    key_col: str,
) -> None:
    """Delete existing rows by key column, then append all rows from df."""
    exists = table_exists(cur, table)
    if exists:
        keys = [(v,) for v in df[key_col].tolist()]
        cur.executemany(f"DELETE FROM {table} WHERE {key_col} = ?", keys)
        conn.commit()
    df.to_sql(table, conn, if_exists="append" if exists else "replace", method="multi", index=False)
    if not exists:
        cur.execute(f"CREATE UNIQUE INDEX idx_{table}_{key_col} ON {table}({key_col})")
        conn.commit()


def upsert_ingredient_recipes(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    df: pd.DataFrame,
) -> None:
    """Upsert ingredient_recipes by deleting per-recipe then re-inserting."""
    table = ING_REC_TABLE
    exists = table_exists(cur, table)
    if exists:
        recipes = [(v,) for v in df["recipe"].unique().tolist()]
        cur.executemany(f"DELETE FROM {table} WHERE recipe = ?", recipes)
        conn.commit()
    df.to_sql(table, conn, if_exists="append" if exists else "replace", method="multi", index=False)
    if not exists:
        cur.execute(
            f"CREATE UNIQUE INDEX idx_{table}_ing_rec "
            f"ON {table}(ingredient, recipe)"
        )
        conn.commit()


def full_replace(
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    df: pd.DataFrame,
    table: str,
) -> None:
    """Delete all rows then insert all rows (supply table; handles empty DataFrame)."""
    exists = table_exists(cur, table)
    if exists:
        cur.execute(f"DELETE FROM {table}")
        conn.commit()
    df.to_sql(table, conn, if_exists="append" if exists else "replace", method="multi", index=False)
    if not exists:
        cur.execute(
            f"CREATE UNIQUE INDEX idx_{table}_key "
            f"ON {table}(ingredient, vendor, location)"
        )
        conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Load DAO:A Trap-Making data into the DAO:A GameTools SQLite database"
    )
    ap.add_argument("recipes_json",           nargs="?", default=_DEFAULT_RECIPES)
    ap.add_argument("ingredient_recipes_json", nargs="?", default=_DEFAULT_ING_REC)
    ap.add_argument("tiers_json",             nargs="?", default=_DEFAULT_TIERS)
    ap.add_argument("supply_json",            nargs="?", default=_DEFAULT_SUPPLY)
    ap.add_argument("effects_json",           nargs="?", default=_DEFAULT_EFFECTS)
    ap.add_argument("db",                     nargs="?", default=_DEFAULT_DB)
    args = ap.parse_args()

    print("Starting database update for DAO:A Trap-Making")

    db_path = Path(args.db)
    if not db_path.parent.exists():
        print(f"ERROR: DB directory not found: {db_path.parent}", file=sys.stderr)
        sys.exit(1)

    recipes  = load_json(args.recipes_json, "recipes")
    ing_recs = load_json(args.ingredient_recipes_json, "ingredient_recipes")
    tiers    = load_json(args.tiers_json, "tiers")
    supply   = load_json(args.supply_json, "unlimited supply")
    effects  = load_json(args.effects_json, "effects")

    df_recipes  = pd.DataFrame(recipes)
    df_ing_recs = pd.DataFrame(ing_recs)
    df_tiers    = pd.DataFrame(tiers)
    # Guard against empty supply → DataFrame with no columns
    df_supply   = (pd.DataFrame(supply, columns=_SUPPLY_COLUMNS) if supply
                   else pd.DataFrame(columns=_SUPPLY_COLUMNS))
    df_effects  = pd.DataFrame(effects)

    conn = sqlite3.connect(str(args.db))
    cur  = conn.cursor()

    try:
        upsert_by_key(conn, cur, df_recipes, RECIPES_TABLE, "name")
        print(f"  Upserted {len(df_recipes)} rows → {RECIPES_TABLE}")

        upsert_ingredient_recipes(conn, cur, df_ing_recs)
        print(f"  Upserted {len(df_ing_recs)} rows → {ING_REC_TABLE}")

        upsert_by_key(conn, cur, df_tiers, TIERS_TABLE, "recipe")
        print(f"  Upserted {len(df_tiers)} rows → {TIERS_TABLE}")

        full_replace(conn, cur, df_supply, SUPPLY_TABLE)
        print(f"  Upserted {len(df_supply)} rows → {SUPPLY_TABLE}")

        # Effects: keyed on name only (no dual-damage traps in Awakening)
        upsert_by_key(conn, cur, df_effects, EFFECTS_TABLE, "name")
        print(f"  Upserted {len(df_effects)} rows → {EFFECTS_TABLE}")

    except Exception as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    print("Database update complete for DAO:A Trap-Making (5 tables).")


if __name__ == "__main__":
    main()
