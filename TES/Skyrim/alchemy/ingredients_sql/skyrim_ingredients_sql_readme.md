# Skyrim Alchemy — Ingredients SQL

Scripts to incrementally update the Skyrim alchemy tables in the shared SQLite database.
They read diff files produced by the sibling `ingredients_json/` scripts rather than
reloading the full dataset on every run.

## Scripts

- `create_or_update_skyrim_alchemy_ingredients.py` — manages the `skyrim_alchemy_ingredients` table
- `create_or_update_skyrim_alchemy_effects.py` — manages the `skyrim_alchemy_effects` table

## How it works

Each script expects a main JSON file (e.g. `skyrim_all_ingredients.json`) and looks for two
diff files alongside it:

- `<stem>.upsert.json` — rows to insert or replace
- `<stem>.delete.json` — rows to remove by key

If neither diff file exists the script prints a message and exits without touching the database.
This is the normal state after a run with no data changes.

On first run (when the table does not yet exist), the upsert file is used to create and populate
the table. On subsequent runs only the changed rows are applied: deletes first, then upserts.

After all SQL succeeds the diff files are removed (`git rm` if tracked, `os.remove` otherwise).
On any exception the script logs the error, the last SQL statement, and a stack trace to stderr,
then exits with code 1.

## Schema

### skyrim_alchemy_ingredients

| column | type | notes |
|--------|------|-------|
| index  | INTEGER | row index from parser |
| name   | TEXT (unique) | ingredient name |
| weight | REAL | |
| value  | INTEGER | |
| ID     | TEXT | form ID |

### skyrim_alchemy_effects

| column | type | notes |
|--------|------|-------|
| name   | TEXT | ingredient name (foreign key to ingredients.name) |
| effect | TEXT | effect name |
| base_magnitude | INTEGER | base magnitude from UESP Skyrim:Alchemy_Effects; NULL if the effects scraper has not been run |

Unique index on `(name, effect)`.

**Schema migration**: if the table exists without a `base_magnitude` column (pre-pipeline-upgrade
state), the loader drops and recreates it automatically. The upsert diff file will contain all
rows with the new column populated, so the table is fully repopulated on that run.

## Default paths

Sources default to the sibling `ingredients_json/` directory. The database defaults to
`../../../database/gametools.sqlite3` (the TES family database).

## Running

```bash
# Use defaults (reads from ingredients_json/, writes to TES/database/gametools.sqlite3)
python3 create_or_update_skyrim_alchemy_ingredients.py
python3 create_or_update_skyrim_alchemy_effects.py

# Override paths explicitly
python3 create_or_update_skyrim_alchemy_ingredients.py \
    /abs/path/to/skyrim_all_ingredients.json \
    /abs/path/to/gametools.sqlite3
```
