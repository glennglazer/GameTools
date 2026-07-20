"""Upsert CC Aquarium furnishing records into skyrim_homestead_build.

Adds Aquarium items (location='Main_Hall_Aquarium') to the existing table.
Uses delete-then-insert by (section, location) to be idempotent.
"""
import argparse
import json
import sqlite3
import sys
import traceback
from pathlib import Path

import pandas as pd

TABLE_NAME = "skyrim_homestead_build"
GAME_LABEL = "Skyrim CC homestead (Aquarium)"
CC_LOCATION = "Main_Hall_Aquarium"

_SCRIPT_DIR = Path(__file__).parent.resolve()
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent
_JSON_DIR = _SCRIPT_DIR.parent / "cc_homestead_json"
_DEFAULT_JSON = str(_JSON_DIR / "cc_homestead_records.json")
_DEFAULT_DB = str(_FAMILY_ROOT / "database" / "gametools.sqlite3")


def main():
    ap = argparse.ArgumentParser(
        description=f"Upsert CC Aquarium furnishings into {TABLE_NAME}")
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
    keys = [(r["section"], CC_LOCATION) for r in records]

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'"
        )
        if cur.fetchone() is None:
            print(f"ERROR: table {TABLE_NAME} does not exist — run homestead loader first",
                  file=sys.stderr)
            conn.close()
            sys.exit(1)

        # Delete existing CC Aquarium rows, then reinsert
        cur.execute(
            f"DELETE FROM {TABLE_NAME} WHERE location = ?", (CC_LOCATION,)
        )
        conn.commit()
        df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)

    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    print(f"Upserted {len(records)} Aquarium furnishing records into {TABLE_NAME}.")
    print(f"Database update complete for {GAME_LABEL}.")


if __name__ == "__main__":
    main()
