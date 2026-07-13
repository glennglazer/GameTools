# Skyrim Enchanting Perks SQL Loader

**Script**: `create_or_update_skyrim_enchant_perks.py`

Creates or incrementally updates the `skyrim_enchant_perks` table in `gametools.sqlite3`.

Reads diff files from `perks_json/` and exits with code 0 (no-op) if none are present. Removes diff files after a successful update.

## Table: `skyrim_enchant_perks`

| Column | Type | Notes |
|--------|------|-------|
| name | TEXT | unique key |
| skill_level | INTEGER | |
| prerequisite | TEXT | |
| description | TEXT | |

Index: `s_ep_name` on `name`.

## Usage

```bash
python3 perks_sql/create_or_update_skyrim_enchant_perks.py [json_file [db_path]]
```
