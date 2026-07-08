# Purpose and Action

The script in this directory incrementally updates all Morrowind enchanting tables in the shared
SQLite database. It reads diff files produced by the sibling `enchant_json/` script rather than
reloading the full dataset on every run.

## Script

- `create_or_update_morrowind_enchant_tables.py` — manages all seven enchanting tables:
  `morrowind_enchant_armor`, `morrowind_enchant_books`, `morrowind_enchant_clothing`,
  `morrowind_enchant_weapons`, `morrowind_enchant_soul_gems`, `morrowind_enchant_magic_effects`,
  `morrowind_enchant_magic_schools`

## How it works

The script takes a JSON directory and looks for diff file pairs for each table prefix:

- `<prefix>.upsert.json` — rows to insert or replace (keyed on `ID`)
- `<prefix>.delete.json` — rows to remove by `ID`

If neither diff file exists for a prefix that table is skipped. If no diff files exist for any
prefix the script exits without touching the database.

On first run (when a table does not yet exist), the upsert file is used to create and populate
it. On subsequent runs only the changed rows are applied: deletes first, then upserts.

After all tables succeed the diff files are removed (`git rm` if tracked, `os.remove` otherwise).
On any exception the script logs the error, the last SQL statement, and a stack trace to stderr,
then exits with code 1.

## Default paths

Sources default to the sibling `enchant_json/` directory. The database defaults to
`../../../database/gametools.sqlite3` (the repo-level shared database).

## Running

```bash
# Use defaults (reads from enchant_json/, writes to database/gametools.sqlite3)
python3 create_or_update_morrowind_enchant_tables.py

# Override paths explicitly
python3 create_or_update_morrowind_enchant_tables.py \
    /abs/path/to/enchant_json/ \
    /abs/path/to/gametools.sqlite3
```
