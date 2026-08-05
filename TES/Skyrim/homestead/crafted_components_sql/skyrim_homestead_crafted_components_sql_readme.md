# skyrim_homestead_crafted_components_sql

Loads `skyrim_homestead_crafted_components` from `crafted_components_records.json`
into SQLite.

## Table schema

`skyrim_homestead_crafted_components` — unique index on `name`

| Column | Type | Description |
|---|---|---|
| `name` | TEXT | Lowercase component name (nails / hinge / iron fittings / lock) |
| `batch_size` | INTEGER | Units produced per forge action |
| `iron_ingot` | INTEGER | Iron ingots required per forge action |
| `corundum_ingot` | INTEGER | Corundum ingots required per forge action |

## Usage

```bash
python3 TES/Skyrim/homestead/crafted_components_sql/create_or_update_skyrim_homestead_crafted_components.py \
  /abs/path/to/crafted_components_records.json \
  /abs/path/to/database/gametools.sqlite3
```

Full-replace on every run (DELETE all rows, re-insert).

## Path computation

`_FAMILY_ROOT` = 3 `.parent` calls up from this script:
`crafted_components_sql/` → `homestead/` → `Skyrim/` → `TES/`
