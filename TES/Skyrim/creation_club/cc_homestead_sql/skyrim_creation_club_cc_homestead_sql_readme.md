# Purpose and Action

This directory holds the SQL loader that upserts the CC Aquarium furnishings
into the shared `skyrim_homestead_build` table.

## Script

### `create_or_update_skyrim_cc_homestead.py`

Reads `cc_homestead_records.json` from the sibling `cc_homestead_json/`
directory and upserts its 18 records into `skyrim_homestead_build`.

**What it does:**
1. Exits with an error if `skyrim_homestead_build` does not exist — the vanilla
   homestead loader must run first
2. Deletes all rows where `location = 'Main_Hall_Aquarium'`
3. Inserts all 18 records from the JSON

Using a bulk DELETE by location (rather than per-piece) matches the
full-replace pattern used by the vanilla homestead loader.

**Target table:** `skyrim_homestead_build`

The table schema is the same as for vanilla homestead data; see
`TES/Skyrim/homestead/build_sql/` for the full schema description.  CC
Aquarium records add ten material columns (`glass`, `mudcrab_chitin`,
`goat_horns`, etc.) via `ALTER TABLE` before the first CC pipeline run.

## Usage

Run with defaults (reads from `cc_homestead_json/`, writes to shared DB):

```bash
python3 TES/Skyrim/creation_club/cc_homestead_sql/create_or_update_skyrim_cc_homestead.py
```

Or with explicit paths:

```bash
python3 TES/Skyrim/creation_club/cc_homestead_sql/create_or_update_skyrim_cc_homestead.py \
  /abs/path/to/cc_homestead_records.json \
  /abs/path/to/database/gametools.sqlite3
```
