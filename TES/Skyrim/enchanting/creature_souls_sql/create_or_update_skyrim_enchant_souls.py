"""Load skyrim_enchant_souls records from JSON into SQLite.

Full-replace on every run: the table is dropped and recreated to keep the
soul_size column typed as INTEGER (the previous pipeline used TEXT).
"""
import argparse
import json
import sqlite3
import sys
import pandas as pd
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent  # creature_souls_sql → enchanting → Skyrim → TES
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "creature_souls_json" / "skyrim_enchant_souls.json")
_DEFAULT_DB = str(_FAMILY_ROOT / "database" / "gametools.sqlite3")

TABLE_NAME = "skyrim_enchant_souls"
INDEX_NAME = "idx_skyrim_enchant_souls"


def main():
    ap = argparse.ArgumentParser(description="Upsert skyrim_enchant_souls into SQLite.")
    ap.add_argument("infile", nargs="?", default=_DEFAULT_IN)
    ap.add_argument("db", nargs="?", default=_DEFAULT_DB)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        records = json.load(f)

    df = pd.DataFrame(records)
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    # Drop and recreate: ensures soul_size column is INTEGER, not legacy TEXT.
    cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
    cur.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    conn.commit()

    df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)
    cur.execute(f"CREATE UNIQUE INDEX {INDEX_NAME} ON {TABLE_NAME} (name, soul_size)")
    conn.commit()

    conn.close()
    print(f"Upserted {len(records)} souls into {TABLE_NAME}.", file=sys.stderr)


if __name__ == "__main__":
    main()
