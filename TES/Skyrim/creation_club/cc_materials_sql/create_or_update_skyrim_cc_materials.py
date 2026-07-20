"""Upsert CC tempering materials into skyrim_tempering_materials.

Generates and upserts new smithing category entries added by CC armor/weapon
sets.  The data is hardcoded in cc_materials_json/skyrim_cc_materials.py;
this loader reads the JSON it produces.
"""
import argparse
import json
import sqlite3
import sys
import traceback
from pathlib import Path

import pandas as pd

TABLE_NAME = "skyrim_tempering_materials"
INDEX_NAME = "s_tm_cat_mat"
GAME_LABEL = "Skyrim CC tempering materials"

_SCRIPT_DIR = Path(__file__).parent.resolve()
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent
_JSON_DIR = _SCRIPT_DIR.parent / "cc_materials_json"
_DEFAULT_JSON = str(_JSON_DIR / "cc_tempering_materials.json")
_DEFAULT_DB = str(_FAMILY_ROOT / "database" / "gametools.sqlite3")


def main():
    ap = argparse.ArgumentParser(
        description=f"Upsert CC tempering materials into {TABLE_NAME}")
    ap.add_argument("json_file", nargs="?", default=_DEFAULT_JSON)
    ap.add_argument("db", nargs="?", default=_DEFAULT_DB)
    args = ap.parse_args()

    print(f"Starting database update for {GAME_LABEL}")

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db)
    if not db_path.parent.exists():
        print(f"ERROR: DB directory not found: {db_path.parent}", file=sys.stderr)
        sys.exit(1)

    with open(json_path) as f:
        records = json.load(f)

    if not records:
        print("No records to upsert.")
        return

    df = pd.DataFrame(records)
    keys = [(r["smithing_category"], r["crafting_material"]) for r in records]

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'"
        )
        table_exists = cur.fetchone() is not None

        if table_exists:
            cur.executemany(
                f"DELETE FROM {TABLE_NAME} "
                f"WHERE smithing_category = ? AND crafting_material = ?",
                keys,
            )
            conn.commit()
        df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)

        if not table_exists:
            cur.execute(
                f"CREATE UNIQUE INDEX {INDEX_NAME} ON {TABLE_NAME} "
                f"(smithing_category, crafting_material)"
            )
            conn.commit()

    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    print(f"Upserted {len(records)} CC tempering records into {TABLE_NAME}.")
    print(f"Database update complete for {GAME_LABEL}.")


if __name__ == "__main__":
    main()
