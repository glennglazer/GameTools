#!/usr/bin/python3

"""
File: morrowind_parse_wiki_to_json.py
Author: Glenn Glazer

Utility to parse wikitables into JSON files for loading into a db.

File is expected to look like this:

|
|Alit Hide
|1.0
|5
|Drain Intelligence
|Resist Poison (Morrowind)|Resist Poison
|Telekinesis (Morrowind)|Telekinesis
|Detect Animal
|ingred_alit_hide_01

with wiki/html formatting stripped out. If there are multiple IDs, "foo</br>bar" should be "foo, bar"
for better readability, though the parsing will work either way

Output JSON format for ingredients file:

{"name" : "Alit Hide",
 "weight": 1.0,
 "value": 5,
 "ID": "ingred_alit_hide_01"
}

Output JSON format for effects file:

{"name" : "Alit Hide",
 "effect": "Drain Intelligence"
}

"""

import argparse
import json
import os.path as op
import sys
from pathlib import Path
from pprint import pprint

NUMBER_OF_WIKI_LINES = 9

_SCRIPT_DIR = Path(__file__).parent.resolve()
_PARSE_DIR = _SCRIPT_DIR.parent / 'ingredients_parse'
_DEFAULT_INFILE = str(_PARSE_DIR / 'morrowind_all_ingredients_raw.txt')
_DEFAULT_ING_FILE = str(_SCRIPT_DIR / 'morrowind_all_ingredients.json')
_DEFAULT_EFF_FILE = str(_SCRIPT_DIR / 'morrowind_all_effects.json')


def remove_pipe(value: str) -> str:
    if value is not None and "|" in value:
        return value.lstrip('|')
    else:
        return value


def remove_wiki_link(value: str) -> str:
    if value is not None and "|" in value:
        return value.split("|")[1]
    else:
        return value


def dash_to_null(entry: str) -> str:
    if '-' in entry:
        return None
    else:
        return entry


def parse(infile: str, verbose: bool = False) -> dict:
    ingredients = []
    effects = []

    if not op.exists(infile):
        return {}, {}

    with open(infile, mode='r') as inf:
        lines = inf.read().splitlines()
        while len(lines) >= NUMBER_OF_WIKI_LINES:
            name = remove_wiki_link(remove_pipe(lines[1])).rstrip()
            weight = float(remove_pipe(lines[2]))
            value = int(remove_pipe(lines[3]))
            first = remove_wiki_link(remove_pipe(dash_to_null(lines[4])))
            second = remove_wiki_link(remove_pipe(dash_to_null(lines[5])))
            third = remove_wiki_link(remove_pipe(dash_to_null(lines[6])))
            fourth = remove_wiki_link(remove_pipe(dash_to_null(lines[7])))
            ID = remove_pipe(lines[8]).rstrip()

            ingredients_entry = {'name': name, 'weight': weight, 'value': value, 'ID': ID}
            ingredients.append(ingredients_entry)

            effects_list = [first, second, third, fourth]

            for effect in effects_list:
                if effect is not None:
                    effect = effect.rstrip()
                effects.append({'name': name, 'effect': effect})

            if verbose:
                print(f"ingredients entry: {ingredients_entry}\n")
                print(f"ingredients so far: {ingredients}\n")
                print(f"effects list: {effects_list}")
                print(f"effects so far: {effects}\n")
            lines = lines[NUMBER_OF_WIKI_LINES:]
        return ingredients, effects


def write_file(parsed: list, outfile: str) -> None:
    with open(outfile, mode='w') as of:
        json.dump(parsed, of)


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
    parser.add_argument("infile", nargs='?', default=_DEFAULT_INFILE,
                        help=f"path to wiki raw text file (default: {_DEFAULT_INFILE})")
    parser.add_argument("ingredient_file", nargs='?', default=_DEFAULT_ING_FILE,
                        help=f"path to write ingredient JSON (default: {_DEFAULT_ING_FILE})")
    parser.add_argument("effects_file", nargs='?', default=_DEFAULT_EFF_FILE,
                        help=f"path to write effects JSON (default: {_DEFAULT_EFF_FILE})")
    parser.add_argument("-v", "--verbose", help="debug output", action="store_true")
    args = parser.parse_args()

    if not op.exists(args.infile):
        print(f"Input file not found: {args.infile}")
        sys.exit(1)

    parsed_ingredients, parsed_effects = parse(args.infile, args.verbose)
    if args.verbose:
        pprint(parsed_ingredients)
        pprint(parsed_effects)

    if parsed_ingredients == {} or parsed_effects == {}:
        print("Error parsing wiki text file, check formatting of entries.")
        sys.exit(1)

    for outfile, new_data, key_fn in [
        (args.ingredient_file, parsed_ingredients, lambda r: r['name']),
        (args.effects_file, parsed_effects, lambda r: (r['name'], r['effect'])),
    ]:
        old_data = load_json_safe(outfile)
        if old_data == new_data:
            print(f"No changes: {Path(outfile).name}", file=sys.stderr)
            continue

        old_path = Path(outfile)
        if old_path.exists():
            old_path.rename(old_path.with_suffix('.old.json'))

        write_file(new_data, outfile)

        upsert, delete = compute_diff(old_data, new_data, key_fn)
        write_diff_files(outfile, upsert, delete)
        print(f"Updated {Path(outfile).name}: {len(upsert)} upsert, {len(delete)} delete",
              file=sys.stderr)
