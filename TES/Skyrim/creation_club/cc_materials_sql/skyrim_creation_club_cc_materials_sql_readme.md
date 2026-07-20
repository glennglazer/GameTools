# Purpose and Action

This directory holds the SQL loader that upserts CC tempering material entries
into the shared `skyrim_tempering_materials` table.

## Script

### `create_or_update_skyrim_cc_materials.py`

Reads `cc_tempering_materials.json` from the sibling `cc_materials_json/`
directory and upserts its 7 records into `skyrim_tempering_materials`.

**What it does:**
1. On first run (table absent): creates the table via `df.to_sql` and adds a
   unique index on `(smithing_category, crafting_material)`
2. On subsequent runs: deletes rows whose composite key matches, then
   re-inserts

**Target table:** `skyrim_tempering_materials`

The table schema is the same as for vanilla tempering data; see
`TES/Skyrim/smithing/materials_sql/` for the full schema description.  After
this loader runs the table contains 47 rows: 40 vanilla + 7 CC.

## Usage

Run with defaults (reads from `cc_materials_json/`, writes to shared DB):

```bash
python3 TES/Skyrim/creation_club/cc_materials_sql/create_or_update_skyrim_cc_materials.py
```

Or with explicit paths:

```bash
python3 TES/Skyrim/creation_club/cc_materials_sql/create_or_update_skyrim_cc_materials.py \
  /abs/path/to/cc_tempering_materials.json \
  /abs/path/to/database/gametools.sqlite3
```
