#!/usr/bin/python3

"""
File: oblivion_parse_wiki_to_json.py
Author: Glenn Glazer

Utility to parse wikitables into JSON files for loading into a db.

File is expected to look like this:

|
|Alkanet Flower
|0.1
|1
|Alkanet
|Restore Intelligence,Resist Poison,Light,Damage Fatigue
|0003365C

with wiki/html formatting stripped out. If there are multiple IDs, "foo</br>bar" should be "foo, bar"
for better readability, though the parsing will work either way

Output JSON format for ingredients file:

{"name" : "Alkanet Flower",
 "weight": 0.1,
 "value": 1,
 "ID": "0003365C"
}

Output JSON format for effects file:

{"name" : "Alkanet Flower",
 "effect": "Restore Intelligence",
 "base_cost": 38.0
}

base_cost is NULL when the effect is not found in the effects lookup (e.g. special
DLC effects such as Felldew Effect, Jyggalag's Favor).

"""

import argparse
import json
import os.path as op
import sys
from pathlib import Path
from pprint import pprint

NUMBER_OF_WIKI_LINES = 7
MAX_NUMBER_OF_EFFECTS = 4

_SCRIPT_DIR = Path(__file__).parent.resolve()
_PARSE_DIR = _SCRIPT_DIR.parent / 'ingredients_parse'
_DEFAULT_INFILE = str(_PARSE_DIR / 'oblivion_all_ingredients_raw.txt')
_DEFAULT_ING_FILE = str(_SCRIPT_DIR / 'oblivion_all_ingredients.json')
_DEFAULT_EFF_FILE = str(_SCRIPT_DIR / 'oblivion_all_effects.json')
_DEFAULT_EFFECTS_RAW = str(_PARSE_DIR / 'oblivion_effects_raw.json')

# Attributes and skills used to expand generic UESP effect names ("Restore Attribute")
# into the specific names used on Oblivion alchemy ingredients ("Restore Intelligence").
_ATTRIBUTES = [
    "Strength", "Intelligence", "Willpower", "Agility",
    "Speed", "Endurance", "Personality", "Luck",
]
_SKILLS = [
    "Blade", "Blunt", "Hand to Hand", "Heavy Armor", "Athletics", "Block",
    "Armorer", "Marksman", "Sneak", "Security", "Acrobatics", "Light Armor",
    "Mercantile", "Speechcraft", "Illusion", "Alchemy", "Mysticism",
    "Conjuration", "Destruction", "Alteration", "Restoration", "Enchant",
]


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


def load_effects_raw(path: str = _DEFAULT_EFFECTS_RAW) -> dict:
    """Load oblivion_effects_raw.json and return a case-folded lookup: name → base_cost.

    The raw JSON uses generic UESP names ("Restore Attribute", "Damage Attribute",
    "Shock Damage").  This function expands each generic "X Attribute" or "X Skill"
    entry into all specific variants ("Restore Intelligence", etc.) and adds
    "Lightning Damage" / "Lightning Shield" as aliases for the Shock variants.
    """
    try:
        with open(path) as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    lookup = {}
    for name, data in raw.items():
        cost = data.get('base_cost')
        lookup[name.lower()] = cost
        # Expand generic "X Attribute" → specific per-attribute variants
        for prefix in ("Restore", "Fortify", "Drain", "Absorb", "Damage"):
            if name == f"{prefix} Attribute":
                for attr in _ATTRIBUTES:
                    lookup[f"{prefix} {attr}".lower()] = cost
        # Expand "X Skill" → specific per-skill variants
        for prefix in ("Fortify", "Drain", "Absorb"):
            if name == f"{prefix} Skill":
                for skill in _SKILLS:
                    lookup[f"{prefix} {skill}".lower()] = cost
        # Alias: Lightning = Shock
        if name == "Shock Damage":
            lookup["lightning damage"] = cost
        if name == "Shock Shield":
            lookup["lightning shield"] = cost

    return lookup


def parse(infile: str, effects_lookup: dict | None = None, verbose: bool = False) -> dict:
    ingredients = []
    effects = []

    lookup = effects_lookup if effects_lookup is not None else {}

    if not op.exists(infile):
        return {}, {}

    try:
        with open(infile, mode='r') as inf:
            lines = inf.read().splitlines()
    except OSError as e:
        print(f"Failed to read input file {infile}: {e}")
        raise

    entry_num = 0
    try:
        while len(lines) >= NUMBER_OF_WIKI_LINES:
            name = remove_wiki_link(remove_pipe(lines[1])).rstrip()
            weight = float(remove_pipe(lines[2]))
            value = int(remove_pipe(lines[3]))
            ID = remove_pipe(lines[6]).rstrip()

            ingredients_entry = {'name': name, 'weight': weight, 'value': value, 'ID': ID}
            ingredients.append(ingredients_entry)

            effects_string = remove_wiki_link(remove_pipe(lines[5])).rstrip()
            effects_list = effects_string.split(',')
            number_of_effects = len(effects_list)
            for _ in range(0, MAX_NUMBER_OF_EFFECTS - number_of_effects):
                effects_list.append(None)

            for effect in effects_list:
                base_cost = lookup.get(effect.lower()) if effect is not None else None
                effects.append({'name': name, 'effect': effect, 'base_cost': base_cost})

            if verbose:
                print(f"ingredients entry: {ingredients_entry}\n")
                print(f"ingredients so far: {ingredients}\n")
                print(f"effects list: {effects_list}")
                print(f"effects so far: {effects}\n")
            entry_num += 1
            lines = lines[NUMBER_OF_WIKI_LINES:]
    except (ValueError, AttributeError, IndexError) as e:
        print(f"Parse error in {infile} at entry {entry_num + 1}: {e}")
        raise
    return ingredients, effects


def write_file(parsed: list, outfile: str) -> None:
    try:
        with open(outfile, mode='w') as of:
            json.dump(parsed, of)
    except OSError as e:
        print(f"Failed to write {outfile}: {e}")
        raise


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
    try:
        with open(out_dir / f'{stem}.upsert.json', 'w') as f:
            json.dump(upsert if upsert else {}, f)
        with open(out_dir / f'{stem}.delete.json', 'w') as f:
            json.dump(delete if delete else {}, f)
    except OSError as e:
        print(f"Failed to write diff files for {Path(outfile).name}: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", nargs='?', default=_DEFAULT_INFILE,
                        help=f"path to wiki raw text file (default: {_DEFAULT_INFILE})")
    parser.add_argument("ingredient_file", nargs='?', default=_DEFAULT_ING_FILE,
                        help=f"path to write ingredient JSON (default: {_DEFAULT_ING_FILE})")
    parser.add_argument("effects_file", nargs='?', default=_DEFAULT_EFF_FILE,
                        help=f"path to write effects JSON (default: {_DEFAULT_EFF_FILE})")
    parser.add_argument("--effects-raw", default=_DEFAULT_EFFECTS_RAW,
                        help=f"path to effects raw JSON (default: {_DEFAULT_EFFECTS_RAW})")
    parser.add_argument("-v", "--verbose", help="debug output", action="store_true")
    args = parser.parse_args()

    if not op.exists(args.infile):
        print(f"Input file not found: {args.infile}")
        sys.exit(1)

    effects_lookup = load_effects_raw(args.effects_raw)
    parsed_ingredients, parsed_effects = parse(args.infile, effects_lookup, args.verbose)
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
            try:
                old_path.rename(old_path.with_suffix('.old.json'))
            except OSError as e:
                print(f"Failed to rename {old_path.name}: {e}")
                raise

        write_file(new_data, outfile)

        upsert, delete = compute_diff(old_data, new_data, key_fn)
        write_diff_files(outfile, upsert, delete)
        print(f"Updated {Path(outfile).name}: {len(upsert)} upsert, {len(delete)} delete",
              file=sys.stderr)
