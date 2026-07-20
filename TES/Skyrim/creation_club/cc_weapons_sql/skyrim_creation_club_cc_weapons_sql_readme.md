# Purpose and Action

This directory holds the SQL loader that upserts CC weapons records into the
shared `skyrim_smithing_weapons` table alongside vanilla Skyrim weapons.

## Script

### `create_or_update_skyrim_cc_weapons.py`

Reads `cc_weapons_records.json` from the sibling `cc_weapons_json/` directory
and upserts its 40 records into `skyrim_smithing_weapons`.

**What it does:**
1. Exits with an error if `skyrim_smithing_weapons` does not exist — the vanilla
   smithing loader must run first
2. Deletes any existing rows whose `piece` matches a record in the JSON
3. Inserts all records from the JSON

**Target table:** `skyrim_smithing_weapons`

The table schema and column set are the same as for vanilla weapons; see
`TES/Skyrim/smithing/weapons_sql/` for the full schema description.  CC
weapons add a `firewood` column and new material columns (`refined_amber`,
`madness_ingot`, `gold_ingot`, `silver_ingot`) beyond the vanilla set that
were added via `ALTER TABLE` before the first CC pipeline run.

## Usage

Run with defaults (reads from `cc_weapons_json/`, writes to shared DB):

```bash
python3 TES/Skyrim/creation_club/cc_weapons_sql/create_or_update_skyrim_cc_weapons.py
```

Or with explicit paths:

```bash
python3 TES/Skyrim/creation_club/cc_weapons_sql/create_or_update_skyrim_cc_weapons.py \
  /abs/path/to/cc_weapons_records.json \
  /abs/path/to/database/gametools.sqlite3
```
