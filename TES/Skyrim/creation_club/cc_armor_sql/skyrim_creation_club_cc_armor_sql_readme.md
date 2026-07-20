# Purpose and Action

This directory holds the SQL loader that upserts CC armor records into the
shared `skyrim_smithing_armor` table alongside vanilla Skyrim armor.

## Script

### `create_or_update_skyrim_cc_armor.py`

Reads `cc_armor_records.json` from the sibling `cc_armor_json/` directory and
upserts its 105 records into `skyrim_smithing_armor`.

**What it does:**
1. Exits with an error if `skyrim_smithing_armor` does not exist — the vanilla
   smithing loader must run first
2. Deletes any existing rows whose `piece` matches a record in the JSON
3. Inserts all records from the JSON

**Target table:** `skyrim_smithing_armor`

The table schema and column set are the same as for vanilla armor; see
`TES/Skyrim/smithing/armor_sql/` for the full schema description.  CC armor
adds 24 material columns (`refined_amber`, `madness_ingot`, `gold_ingot`,
`silver_ingot`) beyond the vanilla set that were added via `ALTER TABLE`
before the first CC pipeline run.

## Usage

Run with defaults (reads from `cc_armor_json/`, writes to shared DB):

```bash
python3 TES/Skyrim/creation_club/cc_armor_sql/create_or_update_skyrim_cc_armor.py
```

Or with explicit paths:

```bash
python3 TES/Skyrim/creation_club/cc_armor_sql/create_or_update_skyrim_cc_armor.py \
  /abs/path/to/cc_armor_records.json \
  /abs/path/to/database/gametools.sqlite3
```
