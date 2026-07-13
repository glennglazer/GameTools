# Skyrim Creature Souls SQL Loader

**Script**: `create_or_update_skyrim_enchant_souls.py`

Creates or incrementally updates the `skyrim_enchant_souls` table. Uses a composite unique key on `(creature, soul_size)`.

## Table: `skyrim_enchant_souls`

| Column | Type | Notes |
|--------|------|-------|
| creature | TEXT | creature or race name |
| soul_size | TEXT | petty/lesser/common/greater/grand/black |

Index: `s_es_creature_size` on `(creature, soul_size)`.

## Usage

```bash
python3 creature_souls_sql/create_or_update_skyrim_enchant_souls.py [json_file [db_path]]
```
