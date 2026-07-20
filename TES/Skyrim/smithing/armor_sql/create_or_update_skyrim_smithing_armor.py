#!/usr/bin/python3
"""
Create or incrementally update the skyrim_smithing_armor table.

Table schema: skyrim_smithing_armor
  piece           TEXT (unique key)
  material_perk   TEXT
  armor_rating    INTEGER
  weight          REAL
  value           INTEGER
  id              TEXT
  bone_meal       INTEGER
  chitin_plate    INTEGER
  corundum_ingot  INTEGER
  daedra_heart    INTEGER
  dragon_bone     INTEGER
  dragon_scales   INTEGER
  dwarven_metal_ingot INTEGER
  ebony_ingot     INTEGER
  iron_ingot      INTEGER
  leather         INTEGER
  leather_strips  INTEGER
  netch_jelly     INTEGER
  netch_leather   INTEGER
  orichalcum_ingot INTEGER
  quicksilver_ingot INTEGER
  refined_malachite INTEGER
  refined_moonstone INTEGER
  stalhrim        INTEGER
  steel_ingot     INTEGER
  void_salts      INTEGER
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

TABLE_NAME = 'skyrim_smithing_armor'
KEY_COL = 'piece'
INDEX_NAME = 's_sa_piece'
GAME_LABEL = 'Skyrim smithing armor'

_SCRIPT_DIR = Path(__file__).parent.resolve()
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent
_JSON_DIR = _SCRIPT_DIR.parent / 'armor_json'
_DEFAULT_JSON_FILE = str(_JSON_DIR / 'skyrim_smithing_armor.json')
_DEFAULT_DB = str(_FAMILY_ROOT / 'database' / 'gametools.sqlite3')


def load_json_file(path: str) -> list:
    with open(path) as f:
        data = json.load(f)
    return [] if isinstance(data, dict) else data


def load_diff_file(path: str) -> tuple:
    if not op.exists(path):
        return [], False
    return load_json_file(path), True


def apply_deletes(cur, table_name: str, delete_data: list, key_col: str = 'piece') -> None:
    cur.executemany(
        f'DELETE FROM {table_name} WHERE {key_col} = ?',
        [(r[key_col],) for r in delete_data],
    )


def apply_upserts(conn, table_name: str, upsert_data: list, key_col: str = 'piece') -> None:
    cur = conn.cursor()
    cur.executemany(
        f'DELETE FROM {table_name} WHERE {key_col} = ?',
        [(r[key_col],) for r in upsert_data],
    )
    conn.commit()
    pd.DataFrame(upsert_data).to_sql(
        table_name, conn, if_exists='append', method='multi', index=False
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
    print(f'Starting database update for {GAME_LABEL}')

    parser = argparse.ArgumentParser()
    parser.add_argument('json_file', nargs='?', default=_DEFAULT_JSON_FILE)
    parser.add_argument('db', nargs='?', default=_DEFAULT_DB)
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    json_path = Path(args.json_file)
    stem = json_path.stem
    json_dir = json_path.parent

    upsert_path = str(json_dir / f'{stem}.upsert.json')
    delete_path = str(json_dir / f'{stem}.delete.json')

    upsert_data, upsert_found = load_diff_file(upsert_path)
    delete_data, delete_found = load_diff_file(delete_path)

    if not upsert_found and not delete_found:
        print(f'No diff files found for {TABLE_NAME}. No database changes to apply.')
        sys.exit(0)

    current_sql = '(none)'
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    try:
        current_sql = f"SELECT name FROM sqlite_master WHERE name='{TABLE_NAME}'"
        table_exists = cur.execute(current_sql).fetchone()

        if table_exists is None:
            if not upsert_data:
                print(f'No upsert data and table {TABLE_NAME} does not exist. Nothing to do.')
                sys.exit(0)
            current_sql = f'(pandas to_sql CREATE {TABLE_NAME})'
            pd.DataFrame(upsert_data).to_sql(
                TABLE_NAME, conn, if_exists='append', method='multi', index=False
            )
            current_sql = f'CREATE UNIQUE INDEX {INDEX_NAME} ON {TABLE_NAME} ({KEY_COL})'
            cur.execute(current_sql)
            conn.commit()
            if args.verbose:
                print(f'Created {TABLE_NAME} with {len(upsert_data)} rows.')
        else:
            if delete_data:
                apply_deletes(cur, TABLE_NAME, delete_data, KEY_COL)
                conn.commit()
                if args.verbose:
                    print(f'Deleted {len(delete_data)} rows from {TABLE_NAME}.')
            if upsert_data:
                apply_upserts(conn, TABLE_NAME, upsert_data, KEY_COL)
                if args.verbose:
                    print(f'Upserted {len(upsert_data)} rows into {TABLE_NAME}.')

    except Exception as e:
        print(f'Database error updating {TABLE_NAME}: {e}', file=sys.stderr)
        print(f'Last SQL: {current_sql}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    for path in [upsert_path, delete_path]:
        if op.exists(path):
            try:
                remove_diff_file(path, _FAMILY_ROOT)
            except Exception as e:
                print(f'Warning: could not remove {path}: {e}', file=sys.stderr)

    print(f'Database update complete for {GAME_LABEL}.')
