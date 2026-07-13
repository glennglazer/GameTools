# Skyrim Apparel Enchantments SQL Loader

**Script**: `create_or_update_skyrim_enchant_apparel.py`

Creates or incrementally updates the `skyrim_enchant_apparel` table.

## Table: `skyrim_enchant_apparel`

| Column | Type | Notes |
|--------|------|-------|
| enchantment | TEXT | unique key |
| head | INTEGER | boolean (0/1) |
| chest | INTEGER | boolean (0/1) |
| hands | INTEGER | boolean (0/1) |
| feet | INTEGER | boolean (0/1) |
| shield | INTEGER | boolean (0/1) |
| amulet | INTEGER | boolean (0/1) |
| ring | INTEGER | boolean (0/1) |

Index: `s_ea_ench` on `enchantment`.

## Usage

```bash
python3 enchant_apparel_sql/create_or_update_skyrim_enchant_apparel.py [json_file [db_path]]
```
