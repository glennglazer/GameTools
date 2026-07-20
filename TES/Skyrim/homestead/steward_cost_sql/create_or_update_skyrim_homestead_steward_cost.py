"""Load skyrim_homestead_steward_cost records from JSON into SQLite."""
import argparse
import json
import pandas as pd
import sqlite3
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent

TABLE_NAME = "skyrim_homestead_steward_cost"


def main():
    ap = argparse.ArgumentParser(
        description=f"Load {TABLE_NAME} into SQLite")
    ap.add_argument("input_json", help="Path to steward_cost_records.json")
    ap.add_argument("db",         help="Path to gametools.sqlite3")
    args = ap.parse_args()

    src = Path(args.input_json)
    db_path = Path(args.db)
    for p, label in ((src, "input JSON"), (db_path.parent, "database directory")):
        if not p.exists():
            print(f"ERROR: {label} not found: {p}", file=sys.stderr)
            sys.exit(1)

    with open(src, encoding="utf-8") as f:
        records = json.load(f)

    df = pd.DataFrame(records, columns=["room", "gold_cost"])

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    exists = cur.execute(
        f"SELECT name FROM sqlite_master WHERE name='{TABLE_NAME}'"
    ).fetchone()

    if exists is not None:
        cur.execute(f"DELETE FROM {TABLE_NAME}")
        conn.commit()

    df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)

    if exists is None:
        cur.execute(
            f"CREATE UNIQUE INDEX idx_{TABLE_NAME} ON {TABLE_NAME}(room)"
        )
        conn.commit()

    conn.close()
    action = "updated" if exists else "created"
    print(f"{action} {TABLE_NAME}: {len(df)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
