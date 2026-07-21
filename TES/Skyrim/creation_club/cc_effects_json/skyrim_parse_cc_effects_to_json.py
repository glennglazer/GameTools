#!/usr/bin/python3

"""
Transform cc_effects_raw.json (scraped from UESP individual CC effect pages)
into cc_effects_records.json — a list of records ready for the SQL loader.

Input (cc_effects_raw.json):
  {"Fortify Persuasion": {"base_cost": 0.5, "base_mag": 1, "base_dur": 30}, ...}

Output (cc_effects_records.json):
  [{"effect": "Fortify Persuasion", "base_magnitude": 1}, ...]

Only base_magnitude is kept because the SQL loader performs a targeted UPDATE
on skyrim_alchemy_effects rather than a full insert.
"""

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR  = Path(__file__).parent.resolve()
_CC_PARSE    = _SCRIPT_DIR.parent / 'cc_parse'
_DEFAULT_IN  = str(_CC_PARSE / 'cc_effects_raw.json')
_DEFAULT_OUT = str(_SCRIPT_DIR / 'cc_effects_records.json')


def parse(raw: dict) -> list[dict]:
    """Convert the raw dict to a list of {effect, base_magnitude} records."""
    records = []
    for effect_name, stats in raw.items():
        if 'base_mag' not in stats:
            print(f"Warning: 'base_mag' missing for '{effect_name}' — skipping", file=sys.stderr)
            continue
        records.append({'effect': effect_name, 'base_magnitude': int(stats['base_mag'])})
    return records


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Parse CC alchemy effects raw JSON into SQL-ready records.',
    )
    ap.add_argument('infile',  nargs='?', default=_DEFAULT_IN,
                    help=f'input raw JSON (default: {_DEFAULT_IN})')
    ap.add_argument('outfile', nargs='?', default=_DEFAULT_OUT,
                    help=f'output records JSON (default: {_DEFAULT_OUT})')
    args = ap.parse_args()

    if not Path(args.infile).exists():
        print(f"Input file not found: {args.infile}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.infile) as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Failed to read {args.infile}: {e}", file=sys.stderr)
        sys.exit(1)

    records = parse(raw)
    if not records:
        print("No records produced — nothing to write", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.outfile, 'w') as f:
            json.dump(records, f, indent=2)
    except OSError as e:
        print(f"Failed to write {args.outfile}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"{len(records)} CC effect records → {args.outfile}")
