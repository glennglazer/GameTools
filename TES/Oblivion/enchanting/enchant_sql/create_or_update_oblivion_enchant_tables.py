#!/usr/bin/python3

"""
File: create_or_update_oblivion_enchant_tables.py
Author: Glenn Glazer

Create or update the oblivion_enchant_soul_gems table by reading directly
from soul_gems.csv in the sibling enchant_parse/ directory.

No intermediate JSON step: Oblivion (2006) is a finished game and the CSV
is the authoritative source.  Exits cleanly with a "no changes" message if
the database already matches the CSV content.  Halts with a non-zero exit
code on any error.

CSV column layout (no header row):
  Type, Mod Name, ObjectIndex, Editor ID, Weight, Value

Database table: oblivion_enchant_soul_gems
  ID TEXT (Editor ID, unique key), object_index TEXT, weight REAL, value INTEGER
"""

import argparse
import csv
import sqlite3
import sys
import traceback
from pathlib import Path

import pandas as pd

TABLE_NAME = 'oblivion_enchant_soul_gems'
INDEX_NAME = 'ob_sg_id'
KEY_COL = 'ID'
GAME_LABEL = 'Oblivion enchanting soul gems'
CSV_FIELDNAMES = ['Type', 'Mod Name', 'ObjectIndex', 'Editor ID', 'Weight', 'Value']

_SCRIPT_DIR = Path(__file__).parent.resolve()
_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
_PARSE_DIR = _SCRIPT_DIR.parent / 'enchant_parse'
_DEFAULT_CSV = str(_PARSE_DIR / 'soul_gems.csv')
_DEFAULT_DB = str(_REPO_ROOT / 'database' / 'gametools.sqlite3')


def read_csv(path: str) -> list:
    """Read soul_gems.csv; return list of row dicts with DB-column names."""
    rows = []
    try:
        with open(path, newline='') as f:
            reader = csv.DictReader(f, fieldnames=CSV_FIELDNAMES)
            try:
                for row in reader:
                    rows.append({
                        'ID': row['Editor ID'],
                        'object_index': row['ObjectIndex'],
                        'weight': float(row['Weight']),
                        'value': int(row['Value']),
                    })
            except (csv.Error, ValueError, KeyError) as e:
                print(f"CSV parse error in {path}: {e}")
                raise
    except OSError as e:
        print(f"Failed to open {path}: {e}")
        raise
    return rows


def read_db_rows(conn: sqlite3.Connection) -> list | None:
    """Return current table rows sorted by ID, or None if the table does not exist."""
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,)
    ).fetchone()
    if exists is None:
        return None
    rows = cur.execute(
        f"SELECT ID, object_index, weight, value FROM {TABLE_NAME} ORDER BY ID"
    ).fetchall()
    return [{'ID': r[0], 'object_index': r[1], 'weight': r[2], 'value': r[3]} for r in rows]


def rows_match(csv_rows: list, db_rows: list) -> bool:
    """Return True if CSV content matches DB content (order-independent)."""
    return sorted(csv_rows, key=lambda r: r['ID']) == db_rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create or update oblivion_enchant_soul_gems from soul_gems.csv.'
    )
    parser.add_argument('csv_file', nargs='?', default=_DEFAULT_CSV,
                        help=f'path to soul_gems.csv (default: {_DEFAULT_CSV})')
    parser.add_argument('db', nargs='?', default=_DEFAULT_DB,
                        help=f'path to SQLite database (default: {_DEFAULT_DB})')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    if not Path(args.csv_file).exists():
        print(f"CSV file not found: {args.csv_file}")
        sys.exit(1)

    try:
        csv_rows = read_csv(args.csv_file)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    if not csv_rows:
        print(f"No rows read from {args.csv_file} — aborting.")
        sys.exit(1)

    current_sql = ''
    try:
        conn = sqlite3.connect(args.db)
        db_rows = read_db_rows(conn)
    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    if db_rows is not None and rows_match(csv_rows, db_rows):
        print(f"No changes in {GAME_LABEL} — database is up to date.", file=sys.stderr)
        conn.close()
        sys.exit(0)

    if args.verbose:
        if db_rows is None:
            print(f"Table {TABLE_NAME} not found — creating.")
        else:
            print(f"Changes detected in {GAME_LABEL} — updating.")

    try:
        cur = conn.cursor()
        if db_rows is not None:
            current_sql = f"DELETE FROM {TABLE_NAME}"
            cur.execute(current_sql)
            conn.commit()

        df = pd.DataFrame(csv_rows)
        current_sql = f"(pandas to_sql {TABLE_NAME})"
        df.to_sql(TABLE_NAME, conn, if_exists='append', method='multi', index=False)

        if db_rows is None:
            current_sql = f"CREATE UNIQUE INDEX {INDEX_NAME} ON {TABLE_NAME} ({KEY_COL})"
            cur.execute(current_sql)
            conn.commit()

    except Exception as e:
        print(f"Database error updating {TABLE_NAME}: {e}", file=sys.stderr)
        print(f"Last SQL: {current_sql}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()
    print(f"Database update complete for {GAME_LABEL} ({len(csv_rows)} rows).")
