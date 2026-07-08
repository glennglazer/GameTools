#!/usr/bin/python3

"""
File: create_or_update_morrowind_enchant_tables.py
Author: Glenn Glazer

Create or incrementally update all Morrowind enchanting tables.

For each prefix in FILE_PREFIXES (armor, books, clothing, weapons,
soul_gems, magic_effects, magic_schools), looks for:
  <json_dir>/<prefix>.upsert.json  — rows to insert or replace
  <json_dir>/<prefix>.delete.json  — rows to remove by ID

If neither diff file exists for a prefix, that table is skipped.
After all tables succeed, diff files are git rm'd (falls back to os.remove).
On any exception: logs error + last SQL + stack trace to stderr; exits 1.
"""

import argparse
import json
import os
import os.path as op
import sqlite3
import subprocess
import sys
import traceback
from pathlib import Path

import pandas as pd

FILE_PREFIXES = ['armor', 'books', 'clothing', 'weapons', 'soul_gems', 'magic_effects', 'magic_schools']
KEY_COL = 'ID'
GAME_LABEL = 'Morrowind enchanting'

_SCRIPT_DIR = Path(__file__).parent.resolve()
_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
_JSON_DIR = _SCRIPT_DIR.parent / 'enchant_json'
_DEFAULT_JSON_DIR = str(_JSON_DIR)
_DEFAULT_DB = str(_REPO_ROOT / 'database' / 'gametools.sqlite3')


def check_for_files(json_dir: str) -> bool:
    return all(op.exists(f"{json_dir}/{p}.json") for p in FILE_PREFIXES)


def load_json_file(path: str) -> list:
    with open(path) as f:
        data = json.load(f)
    return [] if isinstance(data, dict) else data


def load_diff_file(path: str) -> tuple:
    if not op.exists(path):
        return [], False
    return load_json_file(path), True


def apply_deletes(cur, table_name: str, delete_data: list, key_col: str = 'ID') -> str:
    sql = f"DELETE FROM {table_name} WHERE {key_col} = ?"
    cur.executemany(sql, [(r[key_col],) for r in delete_data])
    return sql


def apply_upserts_ingredients(conn, table_name: str, upsert_data: list,
                               key_col: str = 'ID') -> None:
    """Delete-then-reinsert via pandas to_sql."""
    cur = conn.cursor()
    cur.executemany(
        f"DELETE FROM {table_name} WHERE {key_col} = ?",
        [(r[key_col],) for r in upsert_data],
    )
    conn.commit()
    pd.DataFrame(upsert_data).to_sql(
        table_name, conn, if_exists='append', method='multi', index=True
    )


def remove_diff_file(path: str, repo_root: str) -> None:
    try:
        result = subprocess.run(
            ['git', 'rm', '-f', '--quiet', os.path.abspath(path)],
            capture_output=True,
            cwd=str(repo_root),
        )
        if result.returncode != 0:
            os.remove(path)
    except FileNotFoundError:
        os.remove(path)


if __name__ == '__main__':
    print(f"Starting database update for {GAME_LABEL}")

    parser = argparse.ArgumentParser()
    parser.add_argument('json_dir', nargs='?', default=_DEFAULT_JSON_DIR,
                        help=f"directory containing enchanting JSON files (default: {_DEFAULT_JSON_DIR})")
    parser.add_argument('db', nargs='?', default=_DEFAULT_DB,
                        help=f"SQLite database path (default: {_DEFAULT_DB})")
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    json_dir = args.json_dir

    if not json_dir or not op.exists(json_dir):
        print(f"JSON directory not found: {json_dir}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    diff_files_to_remove = []
    current_sql = '(none)'

    try:
        for item_type in FILE_PREFIXES:
            table_name = f"morrowind_enchant_{item_type}"
            index_name = f"m_e_{item_type}"
            upsert_path = op.join(json_dir, f'{item_type}.upsert.json')
            delete_path = op.join(json_dir, f'{item_type}.delete.json')

            upsert_data, upsert_found = load_diff_file(upsert_path)
            delete_data, delete_found = load_diff_file(delete_path)

            if not upsert_found and not delete_found:
                print(f"  No diff files for {table_name}. Skipping.")
                continue

            current_sql = f"SELECT name FROM sqlite_master WHERE name='{table_name}'"
            table_exists = cur.execute(current_sql).fetchone()

            if table_exists is None:
                if not upsert_data:
                    print(f"  No upsert data and {table_name} does not exist. Skipping.")
                    continue
                current_sql = f"(pandas to_sql CREATE {table_name})"
                pd.DataFrame(upsert_data).to_sql(
                    table_name, conn, if_exists='append', method='multi', index=True
                )
                current_sql = f"CREATE UNIQUE INDEX {index_name} ON {table_name} ({KEY_COL})"
                cur.execute(current_sql)
                conn.commit()
                if args.verbose:
                    print(f"  Created {table_name} with {len(upsert_data)} rows.")
            else:
                if delete_data:
                    current_sql = f"DELETE FROM {table_name} WHERE {KEY_COL} = ?"
                    apply_deletes(cur, table_name, delete_data, KEY_COL)
                    conn.commit()
                    if args.verbose:
                        print(f"  Deleted {len(delete_data)} rows from {table_name}.")
                if upsert_data:
                    current_sql = f"DELETE+INSERT {table_name} WHERE {KEY_COL} = ?"
                    apply_upserts_ingredients(conn, table_name, upsert_data, KEY_COL)
                    if args.verbose:
                        print(f"  Upserted {len(upsert_data)} rows into {table_name}.")

            for path in [upsert_path, delete_path]:
                if op.exists(path):
                    diff_files_to_remove.append(path)

    except Exception as e:
        print(f"Database error updating {GAME_LABEL}: {e}", file=sys.stderr)
        print(f"Last SQL: {current_sql}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    for path in diff_files_to_remove:
        try:
            remove_diff_file(path, _REPO_ROOT)
        except Exception as e:
            print(f"Warning: could not remove {path}: {e}", file=sys.stderr)

    print(f"Database update complete for {GAME_LABEL}.")
