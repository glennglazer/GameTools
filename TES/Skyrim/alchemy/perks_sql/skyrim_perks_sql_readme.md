# Purpose and Action

This directory holds the script that loads Skyrim alchemy perk data into the
shared SQLite database.

## Script

### `create_or_update_skyrim_alchemy_perks.py`

Reads diff files written by `skyrim_parse_perks_to_json.py` from the sibling
`perks_json/` directory and applies them to `skyrim_alchemy_perks`.

**What it does:**
1. Looks for `skyrim_alchemy_perks.upsert.json` and `skyrim_alchemy_perks.delete.json`
2. If neither file exists, exits cleanly (no-op)
3. On first run (table absent): creates the table from upsert data and adds a
   unique index on `name`
4. On subsequent runs: deletes named rows, then inserts/replaces upserted rows
5. Removes both diff files after a successful apply

**Target table:** `skyrim_alchemy_perks`

| Column | Type | Notes |
|---|---|---|
| `name` | TEXT | Unique perk name, e.g. `Alchemist (1/5)` |
| `skill_level` | INTEGER | Alchemy skill required to unlock |
| `prerequisite` | TEXT | `None` or comma-separated prerequisite names |
| `description` | TEXT | In-game effect description |

## Usage

Run with defaults (reads from `perks_json/`, writes to shared DB):

```bash
python3 TES/Skyrim/alchemy/perks_sql/create_or_update_skyrim_alchemy_perks.py
```

Or with explicit paths:

```bash
python3 TES/Skyrim/alchemy/perks_sql/create_or_update_skyrim_alchemy_perks.py \
  /abs/path/to/skyrim_alchemy_perks.json \
  /abs/path/to/database/gametools.sqlite3
```
