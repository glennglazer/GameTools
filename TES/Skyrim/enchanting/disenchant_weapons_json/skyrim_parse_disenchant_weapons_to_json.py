#!/usr/bin/python3
"""
Parse disenchant_weapons_raw.json (produced by skyrim_scrape_disenchant.py) into
the canonical output JSON and diff files consumed by the SQL loader.

Input:  disenchant_weapons_raw.json  — list of {effect, item, note} records
Output: disenchant_weapons.json      — same list (canonical snapshot)
        disenchant_weapons.upsert.json / .delete.json  — diff for SQL loader
"""

import argparse
import json
import os.path as op
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
_PARSE_DIR = _SCRIPT_DIR.parent / 'disenchant_parse'
_DEFAULT_INFILE = str(_PARSE_DIR / 'disenchant_weapons_raw.json')
_DEFAULT_OUTFILE = str(_SCRIPT_DIR / 'disenchant_weapons.json')

REQUIRED_KEYS = ('effect', 'item', 'note')


def parse(infile: str) -> list:
    """Load and validate disenchant weapon records from raw JSON."""
    try:
        with open(infile) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f'Failed to read {infile}: {e}', file=sys.stderr)
        raise

    if not isinstance(data, list):
        raise ValueError(f'Expected a JSON list, got {type(data).__name__}')

    for i, rec in enumerate(data):
        for key in REQUIRED_KEYS:
            if key not in rec:
                raise ValueError(f'Record {i}: missing required key {key!r}')
        for key in ('effect', 'item'):
            if not isinstance(rec[key], str) or not rec[key].strip():
                raise ValueError(f'Record {i}: {key!r} must be a non-empty string')

    return data


def load_json_safe(path: str) -> list:
    """Return parsed JSON list from path, or [] if file is missing/unreadable."""
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def compute_diff(old_list: list, new_list: list) -> tuple:
    """Return (upsert_list, delete_list) keyed on (effect, item) pairs."""
    key = lambda r: (r['effect'], r['item'])
    old_map = {key(r): r for r in old_list}
    new_map = {key(r): r for r in new_list}
    upsert = [r for k, r in new_map.items() if old_map.get(k) != r]
    delete = [r for k, r in old_map.items() if k not in new_map]
    return upsert, delete


def write_file(data: list, outfile: str) -> None:
    try:
        with open(outfile, 'w') as f:
            json.dump(data, f)
    except OSError as e:
        print(f'Failed to write {outfile}: {e}', file=sys.stderr)
        raise


def write_diff_files(outfile: str, upsert: list, delete: list) -> None:
    stem = Path(outfile).stem
    out_dir = Path(outfile).parent
    try:
        with open(out_dir / f'{stem}.upsert.json', 'w') as f:
            json.dump(upsert if upsert else {}, f)
        with open(out_dir / f'{stem}.delete.json', 'w') as f:
            json.dump(delete if delete else {}, f)
    except OSError as e:
        print(f'Failed to write diff files: {e}', file=sys.stderr)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Parse Skyrim disenchant weapons raw JSON into output JSON.'
    )
    parser.add_argument('infile', nargs='?', default=_DEFAULT_INFILE)
    parser.add_argument('outfile', nargs='?', default=_DEFAULT_OUTFILE)
    args = parser.parse_args()

    if not op.exists(args.infile):
        print(f'Input file not found: {args.infile}', file=sys.stderr)
        sys.exit(1)

    try:
        new_data = parse(args.infile)
    except (OSError, ValueError) as e:
        print(f'Parse error: {e}', file=sys.stderr)
        sys.exit(1)

    if not new_data:
        print('No records parsed — check raw file.', file=sys.stderr)
        sys.exit(1)

    old_data = load_json_safe(args.outfile)

    if old_data == new_data:
        print(f'No changes: {Path(args.outfile).name}', file=sys.stderr)
        sys.exit(0)

    old_path = Path(args.outfile)
    if old_path.exists():
        try:
            old_path.rename(old_path.with_suffix('.old.json'))
        except OSError as e:
            print(f'Failed to rename {old_path.name}: {e}', file=sys.stderr)
            sys.exit(1)

    try:
        write_file(new_data, args.outfile)
        upsert, delete = compute_diff(old_data, new_data)
        write_diff_files(args.outfile, upsert, delete)
    except OSError:
        sys.exit(1)

    print(
        f'Updated {Path(args.outfile).name}: {len(upsert)} upsert, {len(delete)} delete',
        file=sys.stderr,
    )
