# Skyrim Enchantment Effects SQL Loader

**Script**: `create_or_update_skyrim_enchant_effects.py`

Creates or incrementally updates the `skyrim_enchant_effects` table.

## Table: `skyrim_enchant_effects`

| Column | Type | Notes |
|--------|------|-------|
| name | TEXT | unique key; weapon enchantment name |
| school | TEXT | magic school (Destruction, Conjuration, etc.) |

Index: `s_ee_name` on `name`.

## Usage

```bash
python3 enchant_effects_sql/create_or_update_skyrim_enchant_effects.py [json_file [db_path]]
```
