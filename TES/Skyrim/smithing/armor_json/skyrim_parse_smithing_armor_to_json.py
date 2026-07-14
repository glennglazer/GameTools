#!/usr/bin/python3
"""
Parse the pipe-delimited smithing armor raw text file into JSON,
and write diff files for the SQL loader.

Input format (26 pipe-delimited fields, one row per armor piece):
  piece|material_perk|armor_rating|weight|value|id|
  bone_meal|chitin_plate|corundum_ingot|daedra_heart|dragon_bone|
  dragon_scales|dwarven_metal_ingot|ebony_ingot|iron_ingot|leather|
  leather_strips|netch_jelly|netch_leather|orichalcum_ingot|
  quicksilver_ingot|refined_malachite|refined_moonstone|stalhrim|
  steel_ingot|void_salts
"""

import argparse
import json
import os.path as op
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
_PARSE_DIR = _SCRIPT_DIR.parent / 'armor_parse'
_DEFAULT_INFILE = str(_PARSE_DIR / 'skyrim_smithing_armor_raw.txt')
_DEFAULT_OUTFILE = str(_SCRIPT_DIR / 'skyrim_smithing_armor.json')

ARMOR_MATERIAL_COLS = [
    'bone_meal', 'chitin_plate', 'corundum_ingot', 'daedra_heart',
    'dragon_bone', 'dragon_scales', 'dwarven_metal_ingot', 'ebony_ingot',
    'iron_ingot', 'leather', 'leather_strips', 'netch_jelly', 'netch_leather',
    'orichalcum_ingot', 'quicksilver_ingot', 'refined_malachite',
    'refined_moonstone', 'stalhrim', 'steel_ingot', 'void_salts',
]

FIXED_FIELDS = ['piece', 'material_perk', 'armor_rating', 'weight', 'value', 'id']
ALL_FIELDS = FIXED_FIELDS + ARMOR_MATERIAL_COLS
EXPECTED_FIELDS = len(ALL_FIELDS)


def parse(infile: str) -> list:
    try:
        with open(infile) as f:
            lines = [l.rstrip('\n') for l in f if l.strip()]
    except OSError as e:
        print(f'Failed to read {infile}: {e}', file=sys.stderr)
        raise

    rows = []
    for lineno, line in enumerate(lines, 1):
        parts = line.split('|')
        if len(parts) != EXPECTED_FIELDS:
            raise ValueError(
                f'Line {lineno}: expected {EXPECTED_FIELDS} pipe-separated fields, '
                f'got {len(parts)}: {line!r}'
            )
        rec = {}
        for field, val in zip(ALL_FIELDS, parts):
            val = val.strip()
            if field == 'weight':
                try:
                    rec[field] = float(val)
                except ValueError:
                    raise ValueError(f'Line {lineno}: weight is not a float: {val!r}')
            elif field in ('armor_rating', 'value') or field in ARMOR_MATERIAL_COLS:
                try:
                    rec[field] = int(val)
                except ValueError:
                    raise ValueError(
                        f'Line {lineno}: {field} is not an integer: {val!r}')
            else:
                rec[field] = val
        rows.append(rec)
    return rows


def load_json_safe(path: str) -> list:
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def compute_diff(old_list: list, new_list: list, key_fn) -> tuple:
    old_map = {key_fn(r): r for r in old_list}
    new_map = {key_fn(r): r for r in new_list}
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
        description='Parse Skyrim smithing armor raw text into JSON.')
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
        print('No armor rows parsed — check raw file.', file=sys.stderr)
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
        upsert, delete = compute_diff(old_data, new_data, lambda r: r['piece'])
        write_diff_files(args.outfile, upsert, delete)
    except OSError:
        sys.exit(1)

    print(f'Updated {Path(args.outfile).name}: {len(upsert)} upsert, {len(delete)} delete',
          file=sys.stderr)
