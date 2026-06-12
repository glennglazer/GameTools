#!/usr/bin/python3

"""
File: oblivion_parse_enchant_csv_to_json.py
Author: Glenn Glazer

Utility to parse CSV files into JSON files for loading into a db.
Assumes there are four files to be read: armor, books, clothing, weapons
"""

import argparse
import csv
import json
import os.path as op
import sys
from pathlib import Path

FILE_PREFIXES = ['soul_gems']

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN_DIR = str(_SCRIPT_DIR.parent / 'enchant_parse')
_DEFAULT_OUT_DIR = str(_SCRIPT_DIR)


def write_file(parsed: list, outfile: str) -> None:
    with open(outfile, mode='w') as of:
        json.dump(parsed, of)


def check_for_files(in_dir: str) -> bool:
    rv = True
    for prefix in FILE_PREFIXES:
        rv = rv and op.exists(in_dir + '/' + prefix + '.csv')
    return rv


def load_json_safe(path: str) -> list:
    """Return parsed JSON from path, or [] if file missing or invalid."""
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def compute_diff(old_list: list, new_list: list, key_fn) -> tuple:
    """Return (upsert_list, delete_list) comparing old vs new by key_fn.

    upsert_list: rows that are new or changed relative to old
    delete_list: rows present in old but absent from new
    """
    old_map = {key_fn(r): r for r in old_list}
    new_map = {key_fn(r): r for r in new_list}

    upsert = [r for k, r in new_map.items() if old_map.get(k) != r]
    delete = [r for k, r in old_map.items() if k not in new_map]
    return upsert, delete


def write_diff_files(outfile: str, upsert: list, delete: list) -> None:
    """Write <stem>.upsert.json and <stem>.delete.json alongside outfile."""
    stem = Path(outfile).stem
    out_dir = Path(outfile).parent
    with open(out_dir / f'{stem}.upsert.json', 'w') as f:
        json.dump(upsert if upsert else {}, f)
    with open(out_dir / f'{stem}.delete.json', 'w') as f:
        json.dump(delete if delete else {}, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("in_dir", nargs='?', default=_DEFAULT_IN_DIR,
                        help=f"directory to read CSV files from (default: {_DEFAULT_IN_DIR})")
    parser.add_argument("out_dir", nargs='?', default=_DEFAULT_OUT_DIR,
                        help=f"directory to write JSON files to (default: {_DEFAULT_OUT_DIR})")
    args = parser.parse_args()
    in_dir = args.in_dir
    out_dir = args.out_dir

    if not in_dir or not op.exists(in_dir):
        print(f"Read directory not given or does not exist: {in_dir}")
        parser.print_usage()
        sys.exit(1)
    elif not check_for_files(in_dir):
        print(f"One or more of {FILE_PREFIXES} CSV files missing from {in_dir}")

    if not op.exists(out_dir):
        print(f"Output directory does not exist: {out_dir}")
        parser.print_usage()
        sys.exit(1)

    for item_type in FILE_PREFIXES:
        item_read = f"{in_dir}/{item_type}.csv"
        item_write = f"{out_dir}/{item_type}.json"
        item_list = []

        with open(item_read, newline='') as item_file:
            reader = csv.DictReader(item_file, fieldnames=['Type', 'Mod Name', 'ObjectIndex', 'Editor ID', 'Weight', 'Value'])
            try:
                for row in reader:
                    smaller_row = {'Editor ID': row['Editor ID'], 'Weight': row['Weight'], 'Value': row['Value']}
                    item_list.append(smaller_row)
            except csv.Error as e:
                print(f"Error parsing {row} in {item_read}: {e}")
                sys.exit(1)

        old_data = load_json_safe(item_write)
        if old_data == item_list:
            print(f"No changes: {item_type}.json", file=sys.stderr)
            continue

        old_path = Path(item_write)
        if old_path.exists():
            old_path.rename(old_path.with_suffix('.old.json'))

        write_file(item_list, item_write)

        upsert, delete = compute_diff(old_data, item_list, lambda r: r['Editor ID'])
        write_diff_files(item_write, upsert, delete)
        print(f"Updated {item_type}.json: {len(upsert)} upsert, {len(delete)} delete",
              file=sys.stderr)
