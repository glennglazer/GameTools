"""Load oblivion_enchant_souls records from JSON into SQLite."""
import argparse
import json
import sqlite3
import sys
import pandas as pd
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent  # souls_sql → enchanting → Oblivion → TES
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "souls_json" / "oblivion_souls_records.json")
_DEFAULT_DB = str(_FAMILY_ROOT / "database" / "gametools.sqlite3")

TABLE_NAME = "oblivion_enchant_souls"
INDEX_NAME = "idx_oblivion_enchant_souls"


def main():
    ap = argparse.ArgumentParser(description="Upsert oblivion_enchant_souls into SQLite.")
    ap.add_argument("infile", nargs="?", default=_DEFAULT_IN)
    ap.add_argument("db", nargs="?", default=_DEFAULT_DB)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        records = json.load(f)

    df = pd.DataFrame(records)
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    exists = cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'"
    ).fetchone()

    if exists is not None:
        cur.execute(f"DELETE FROM {TABLE_NAME}")
        conn.commit()

    df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)

    if exists is None:
        cur.execute(f"CREATE UNIQUE INDEX {INDEX_NAME} ON {TABLE_NAME} (name, soul_size)")
        conn.commit()

    conn.close()
    print(f"Upserted {len(records)} souls into {TABLE_NAME}.", file=sys.stderr)


if __name__ == "__main__":
    main()
