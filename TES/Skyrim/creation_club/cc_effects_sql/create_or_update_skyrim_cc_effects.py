"""Update skyrim_alchemy_effects with base_magnitude values for CC-only effects.

CC-only alchemy effects (e.g. Fortify Persuasion from Rare Curios) are absent
from the UESP base-game Alchemy_Effects page, so their base_magnitude is NULL
after the main alchemy pipeline runs.  This loader performs a targeted UPDATE
to fill in those values.

Unlike other loaders in the CC pipeline, this script runs an UPDATE rather
than INSERT because the ingredient-effect rows already exist in the table
(they were inserted by the main alchemy pipeline).

Always runs; no diff files.  Idempotent: running multiple times produces the
same result.
"""

import argparse
import json
import sqlite3
import sys
import traceback
from pathlib import Path

TABLE_NAME = 'skyrim_alchemy_effects'
GAME_LABEL = 'Skyrim CC alchemy effects'

_SCRIPT_DIR  = Path(__file__).parent.resolve()
_FAMILY_ROOT = _SCRIPT_DIR.parent.parent.parent
_JSON_DIR    = _SCRIPT_DIR.parent / 'cc_effects_json'
_DEFAULT_JSON = str(_JSON_DIR / 'cc_effects_records.json')
_DEFAULT_DB   = str(_FAMILY_ROOT / 'database' / 'gametools.sqlite3')


def apply_updates(conn: sqlite3.Connection, records: list[dict]) -> int:
    """UPDATE base_magnitude for each CC effect.  Returns number of rows touched."""
    cur = conn.cursor()
    total = 0
    for rec in records:
        cur.execute(
            f"UPDATE {TABLE_NAME} SET base_magnitude = ? WHERE LOWER(effect) = LOWER(?)",
            (rec['base_magnitude'], rec['effect']),
        )
        total += cur.rowcount
    conn.commit()
    return total


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description=f'Update {TABLE_NAME} base_magnitude for CC-only effects.',
    )
    ap.add_argument('json_file', nargs='?', default=_DEFAULT_JSON,
                    help=f'CC effects records JSON (default: {_DEFAULT_JSON})')
    ap.add_argument('db', nargs='?', default=_DEFAULT_DB,
                    help=f'SQLite database path (default: {_DEFAULT_DB})')
    args = ap.parse_args()

    print(f"Starting database update for {GAME_LABEL}")

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db)
    if not db_path.parent.exists():
        print(f"ERROR: DB directory not found: {db_path.parent}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(json_path) as f:
            records = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Failed to read {json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not records:
        print("No CC effect records — nothing to update.")
        sys.exit(0)

    try:
        conn = sqlite3.connect(args.db)
        rows_updated = apply_updates(conn, records)
        conn.close()
    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    print(f"Updated base_magnitude for {rows_updated} rows in {TABLE_NAME}.")
    print(f"Database update complete for {GAME_LABEL}.")
