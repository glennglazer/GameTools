# Skyrim Soul Gem Types SQL Loader

**Script**: `create_or_update_skyrim_enchant_soulgems.py`

Creates or incrementally updates the `skyrim_enchant_soulgems` table.

## Table: `skyrim_enchant_soulgems`

| Column | Type | Notes |
|--------|------|-------|
| name | TEXT | unique key |
| weight | REAL | |
| value | INTEGER | |
| capacity | INTEGER | soul charge capacity |
| trappable_souls | TEXT | description of trappable soul types |

Index: `s_esg_name` on `name`.

## Usage

```bash
python3 gem_types_sql/create_or_update_skyrim_enchant_soulgems.py [json_file [db_path]]
```
