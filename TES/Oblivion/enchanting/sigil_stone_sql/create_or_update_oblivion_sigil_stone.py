"""Load oblivion sigil stone records from JSON into SQLite (three tables)."""
import argparse
import json
import sqlite3
import sys
import pandas as pd
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent  # sigil_stone_sql → enchanting → Oblivion → TES
_JSON_DIR = _SCRIPT_DIR.parent / "sigil_stone_json"
_DEFAULT_IN_STONES  = str(_JSON_DIR / "sigil_stone_records.json")
_DEFAULT_IN_WEAPONS = str(_JSON_DIR / "sigil_stone_weapon_magnitudes.json")
_DEFAULT_IN_ARMOR   = str(_JSON_DIR / "sigil_stone_armor_magnitudes.json")
_DEFAULT_DB = str(_FAMILY_ROOT / "database" / "gametools.sqlite3")

STONES_TABLE  = "oblivion_sigil_stone"
WEAPONS_TABLE = "oblivion_sigil_stone_weapon_magnitudes"
ARMOR_TABLE   = "oblivion_sigil_stone_armor_magnitudes"


def _upsert_table(conn, table_name, index_name, records, index_sql):
    """Full-replace upsert: delete all rows if table exists, insert fresh, create index if new."""
    cur = conn.cursor()
    df = pd.DataFrame(records)

    exists = cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    ).fetchone()

    if exists is not None:
        cur.execute(f"DELETE FROM {table_name}")
        conn.commit()

    df.to_sql(table_name, conn, if_exists="append", method="multi", index=False)
    conn.commit()

    if exists is None:
        cur.execute(index_sql)
        conn.commit()

    return len(records)


def main():
    ap = argparse.ArgumentParser(description="Upsert Oblivion sigil stone tables into SQLite.")
    ap.add_argument("--in-stones",  default=_DEFAULT_IN_STONES)
    ap.add_argument("--in-weapons", default=_DEFAULT_IN_WEAPONS)
    ap.add_argument("--in-armor",   default=_DEFAULT_IN_ARMOR)
    ap.add_argument("db", nargs="?", default=_DEFAULT_DB)
    args = ap.parse_args()

    for path in (args.in_stones, args.in_weapons, args.in_armor):
        if not Path(path).is_file():
            print(f"ERROR: input file not found: {path}", file=sys.stderr)
            sys.exit(1)

    with open(args.in_stones,  encoding="utf-8") as f:
        stones = json.load(f)
    with open(args.in_weapons, encoding="utf-8") as f:
        weapon_mags = json.load(f)
    with open(args.in_armor,   encoding="utf-8") as f:
        armor_mags = json.load(f)

    conn = sqlite3.connect(args.db)

    n = _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", stones,
                      f"CREATE UNIQUE INDEX idx_{STONES_TABLE} ON {STONES_TABLE} (form_id)")
    print(f"Upserted {n} rows into {STONES_TABLE}.", file=sys.stderr)

    n = _upsert_table(conn, WEAPONS_TABLE, f"idx_{WEAPONS_TABLE}", weapon_mags,
                      f"CREATE UNIQUE INDEX idx_{WEAPONS_TABLE} ON {WEAPONS_TABLE} (form_id)")
    print(f"Upserted {n} rows into {WEAPONS_TABLE}.", file=sys.stderr)

    n = _upsert_table(conn, ARMOR_TABLE, f"idx_{ARMOR_TABLE}", armor_mags,
                      f"CREATE UNIQUE INDEX idx_{ARMOR_TABLE} ON {ARMOR_TABLE} (form_id)")
    print(f"Upserted {n} rows into {ARMOR_TABLE}.", file=sys.stderr)

    conn.close()


if __name__ == "__main__":
    main()
