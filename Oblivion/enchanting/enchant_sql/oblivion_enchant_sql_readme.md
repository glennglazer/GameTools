# Purpose and Action

This directory will hold the script(s) to incrementally update Oblivion enchanting tables in
the shared SQLite database, following the same diff-file pattern used by the other `*_sql`
directories.

## Status

**Stub only — no loader script exists yet.**

The Oblivion enchanting parser (`enchant_json/`) is still in progress. The SQL loader will be
written once the parser output format is finalised.

## Planned script

- `create_or_update_oblivion_enchant_tables.py` — will manage Oblivion enchanting tables,
  reading `<prefix>.upsert.json` / `<prefix>.delete.json` diff files from the sibling
  `enchant_json/` directory.
