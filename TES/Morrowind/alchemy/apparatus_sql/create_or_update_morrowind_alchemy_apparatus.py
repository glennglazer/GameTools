"""Upsert Morrowind alchemy apparatus records into morrowind_alchemy_apparatus."""
import argparse
import json
import sqlite3
import sys
import traceback
from pathlib import Path

import pandas as pd

TABLE_NAME = "morrowind_alchemy_apparatus"
INDEX_NAME = "idx_morrowind_alchemy_apparatus_id"
GAME_LABEL = "Morrowind alchemy apparatus"

_SCRIPT_DIR = Path(__file__).parent.resolve()
_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
_JSON_DIR = _SCRIPT_DIR.parent / "apparatus_json"
_DEFAULT_JSON = str(_JSON_DIR / "morrowind_apparatus_records.json")
_DEFAULT_DB = str(_REPO_ROOT / "database" / "gametools.sqlite3")


def main():
    ap = argparse.ArgumentParser(
        description=f"Upsert {GAME_LABEL} into {TABLE_NAME}")
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
    ids = [(r["id"],) for r in records]

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'"
        )
        table_exists = cur.fetchone() is not None

        if table_exists:
            cur.executemany(f"DELETE FROM {TABLE_NAME} WHERE id = ?", ids)
            conn.commit()
        df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)

        if not table_exists:
            cur.execute(
                f"CREATE UNIQUE INDEX {INDEX_NAME} ON {TABLE_NAME} (id)"
            )
            conn.commit()

    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    print(f"Upserted {len(records)} apparatus records into {TABLE_NAME}.")
    print(f"Database update complete for {GAME_LABEL}.")


if __name__ == "__main__":
    main()
