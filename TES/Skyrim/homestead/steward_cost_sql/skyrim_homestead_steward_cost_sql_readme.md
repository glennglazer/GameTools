# Skyrim Homestead Steward Cost SQL Loader

**Script**: `create_or_update_skyrim_homestead_steward_cost.py`

Loads `steward_cost_records.json` into the `skyrim_homestead_steward_cost` table using full-replace.

## Table: `skyrim_homestead_steward_cost`

| Column | Type | Notes |
|--------|------|-------|
| room | TEXT | unique key: room name as it appears in-game |
| gold_cost | INTEGER | gold cost for the steward to furnish this room |

Index: `idx_skyrim_homestead_steward_cost` on `room`.

12 rows (Small House, Entry Room Upgrade, Main Hall, Library, Trophy Room, Bedrooms, Greenhouse, Enchanter's Tower, Alchemy Laboratory, Armory, Storage Room, Kitchen). The Cellar is not included — the steward cannot furnish it.

## Update strategy

Full-replace on every run (same as all homestead tables). See `build_sql` readme for rationale.

## Usage

```bash
python3 steward_cost_sql/create_or_update_skyrim_homestead_steward_cost.py \
  steward_cost_json/steward_cost_records.json \
  /abs/path/to/database/gametools.sqlite3
```
