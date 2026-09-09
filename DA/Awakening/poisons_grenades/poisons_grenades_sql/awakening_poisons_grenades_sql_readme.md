# awakening_poisons_grenades_sql — DAO:A Poison-Making SQL Loader

## Purpose

Loads the five Awakening poison-making JSON files into the DAO:A GameTools SQLite database
(`DA/Awakening/database/gametools.sqlite3`), creating tables on first run and upserting on
subsequent runs.

The DAO:A database already contains all Origins tables (synced by the chained pipeline in
`update_da.py`). The five Awakening tables are added alongside them under the `awakening_` prefix.

## Tables Created

| Table | Key | Rows | Description |
|-------|-----|------|-------------|
| `awakening_poisons_grenades_recipes` | `name` | 4 | Wide recipe table; **type** = "poison"/"grenade"; all Tier 4; `gxa_` item IDs |
| `awakening_poisons_grenades_ingredient_recipes` | `(ingredient, recipe)` | ~14 | Ingredient → recipe reverse-lookup join table |
| `awakening_poisons_grenades_tiers` | `recipe` | 4 | Recipe → required poison-making tier (all 4) |
| `awakening_poisons_grenades_unlimited_supply` | `(ingredient, vendor, location)` | 0 | Empty — no Awakening supply section on wiki |
| `awakening_poisons_grenades_effects` | `name` | 4 | Crafted item damage_type/power/effect |

## DB Path

Computed as 2 `.parent` calls from the script file:
`poisons_grenades_sql/` → `poisons_grenades/` → `Awakening/` → `DA/Awakening/database/gametools.sqlite3`

## Usage

```bash
# Default paths
python3 DA/Awakening/poisons_grenades/poisons_grenades_sql/create_or_update_awakening_poisons_grenades.py

# Explicit paths
python3 DA/Awakening/poisons_grenades/poisons_grenades_sql/create_or_update_awakening_poisons_grenades.py \
    /abs/path/to/awakening_poisons_grenades_recipes.json \
    /abs/path/to/awakening_poisons_grenades_ingredient_recipes.json \
    /abs/path/to/awakening_poisons_grenades_tiers.json \
    /abs/path/to/awakening_poisons_grenades_unlimited_supply.json \
    /abs/path/to/awakening_poisons_grenades_effects.json \
    /abs/path/to/DA/Awakening/database/gametools.sqlite3
```

## Upsert Strategy

- **`awakening_poisons_grenades_recipes`**: delete by `name`, re-insert
- **`awakening_poisons_grenades_ingredient_recipes`**: delete by `recipe`, re-insert
- **`awakening_poisons_grenades_tiers`**: delete by `recipe`, re-insert
- **`awakening_poisons_grenades_unlimited_supply`**: full DELETE ALL + re-insert; empty supply
  creates the table with correct schema (explicit column names) and 0 rows
- **`awakening_poisons_grenades_effects`**: delete by `name`, re-insert
