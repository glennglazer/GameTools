#!/usr/bin/python3
"""
Parse smelting_raw.json into skyrim_smelting records and write diff files.

Input  (smelting_raw.json):
  {recipes, material_stats, ingot_stats}

Output (skyrim_smelting.json):
  [{Source_Name, Source_Weight, Source_Value, Source_To_Ingot,
    Ingot_Name, Ingots_Produced, Ingot_Weight, Ingot_Value, Note}, ...]

Special cases handled here:
  - Steel Ingot  → 2 rows (Iron Ore row + Corundum Ore row, each with a Note)
  - Stalhrim     → 1 NULL row with a Note (no smelting required)
  - CC items     → Amber → Refined Amber; Madness Ore → Madness Ingot
"""

import argparse
import json
import os.path as op
import sys
from pathlib import Path

_SCRIPT_DIR  = Path(__file__).parent.resolve()
_PARSE_DIR   = _SCRIPT_DIR.parent / 'smelting_parse'
_DEFAULT_IN  = str(_PARSE_DIR / 'smelting_raw.json')
_DEFAULT_OUT = str(_SCRIPT_DIR / 'skyrim_smelting.json')

# Steel Ingot wiki row lists two sources ("Iron Ore, Corundum Ore") — split here.
STEEL_ROWS = [
    {'Source_Name': 'Iron Ore',     'Source_To_Ingot': 1,
     'Ingot_Name': 'Steel Ingot',  'Ingots_Produced': 1,
     'Note': 'Also requires 1 Corundum Ore'},
    {'Source_Name': 'Corundum Ore', 'Source_To_Ingot': 1,
     'Ingot_Name': 'Steel Ingot',  'Ingots_Produced': 1,
     'Note': 'Also requires 1 Iron Ore'},
]

# CC items not on the main Smelting page; recipe rules from individual wiki pages.
CC_RECIPES = [
    {'Source_Name': 'Amber',       'Source_To_Ingot': 2,
     'Ingot_Name': 'Refined Amber',  'Ingots_Produced': 1,
     'Note': 'Saints & Seducers Creation Club content'},
    {'Source_Name': 'Madness Ore', 'Source_To_Ingot': 2,
     'Ingot_Name': 'Madness Ingot',  'Ingots_Produced': 1,
     'Note': 'Saints & Seducers Creation Club content'},
]

# Stalhrim note: appears as a placeholder row (all numeric fields NULL).
STALHRIM_ROW = {
    'Source_Name':     'Stalhrim',
    'Source_Weight':   None,
    'Source_Value':    None,
    'Source_To_Ingot': None,
    'Ingot_Name':      None,
    'Ingots_Produced': None,
    'Ingot_Weight':    None,
    'Ingot_Value':     None,
    'Note': 'Stalhrim does not require smelting; it is found as ore and used directly in smithing.',
}


def load_raw(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except OSError as e:
        print(f'Failed to read {path}: {e}', file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f'Invalid JSON in {path}: {e}', file=sys.stderr)
        raise


def build_record(source_name: str, source_to_ingot: int,
                 ingot_name: str, ingots_produced: int,
                 material_stats: dict, ingot_stats: dict,
                 note=None) -> dict:
    src  = material_stats.get(source_name, {})
    ing  = ingot_stats.get(ingot_name, {})
    return {
        'Source_Name':     source_name,
        'Source_Weight':   src.get('weight'),
        'Source_Value':    src.get('value'),
        'Source_To_Ingot': source_to_ingot,
        'Ingot_Name':      ingot_name,
        'Ingots_Produced': ingots_produced,
        'Ingot_Weight':    ing.get('weight'),
        'Ingot_Value':     ing.get('value'),
        'Note':            note,
    }


def parse(raw: dict) -> list:
    material_stats = raw.get('material_stats', {})
    ingot_stats    = raw.get('ingot_stats', {})
    base_recipes   = raw.get('recipes', [])

    records = []

    for r in base_recipes:
        rec = build_record(
            r['source'], r['source_to_ingot'],
            r['ingot'], r['ingots_produced'],
            material_stats, ingot_stats,
        )
        records.append(rec)

    # Steel Ingot: two rows with cross-notes
    for sr in STEEL_ROWS:
        rec = build_record(
            sr['Source_Name'], sr['Source_To_Ingot'],
            sr['Ingot_Name'], sr['Ingots_Produced'],
            material_stats, ingot_stats,
            note=sr['Note'],
        )
        records.append(rec)

    # CC items
    for cr in CC_RECIPES:
        rec = build_record(
            cr['Source_Name'], cr['Source_To_Ingot'],
            cr['Ingot_Name'], cr['Ingots_Produced'],
            material_stats, ingot_stats,
            note=cr['Note'],
        )
        records.append(rec)

    # Stalhrim placeholder
    records.append(STALHRIM_ROW.copy())

    return records


def load_json_safe(path: str) -> list:
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def record_key(r: dict) -> tuple:
    return (r['Source_Name'], r['Ingot_Name'])


def compute_diff(old_list: list, new_list: list) -> tuple:
    old_map = {record_key(r): r for r in old_list}
    new_map = {record_key(r): r for r in new_list}
    upsert = [r for k, r in new_map.items() if old_map.get(k) != r]
    delete = [r for k, r in old_map.items() if k not in new_map]
    return upsert, delete


def write_file(data: list, path: str) -> None:
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        print(f'Failed to write {path}: {e}', file=sys.stderr)
        raise


def write_diff_files(outfile: str, upsert: list, delete: list) -> None:
    stem    = Path(outfile).stem
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
    ap = argparse.ArgumentParser(description='Parse Skyrim smelting raw JSON into records.')
    ap.add_argument('infile',  nargs='?', default=_DEFAULT_IN)
    ap.add_argument('outfile', nargs='?', default=_DEFAULT_OUT)
    args = ap.parse_args()

    if not op.exists(args.infile):
        print(f'Input file not found: {args.infile}', file=sys.stderr)
        sys.exit(1)

    try:
        raw = load_raw(args.infile)
    except (OSError, json.JSONDecodeError):
        sys.exit(1)

    try:
        new_data = parse(raw)
    except Exception as e:
        print(f'Parse error: {e}', file=sys.stderr)
        sys.exit(1)

    if not new_data:
        print('No records parsed — check smelting_raw.json.', file=sys.stderr)
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

    print(f'Updated {Path(args.outfile).name}: {len(upsert)} upsert, {len(delete)} delete',
          file=sys.stderr)
