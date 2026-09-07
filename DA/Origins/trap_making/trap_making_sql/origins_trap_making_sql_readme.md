# origins_trap_making_sql — DAO Trap-Making SQL Loader

## Purpose

Loads the five trap-making JSON files into the GameTools SQLite database,
creating tables on first run and upserting on subsequent runs.

## Tables Created

| Table | Key | Rows | Description |
|-------|-----|------|-------------|
| `origins_trap_making_recipes` | `name` | 25 | Wide recipe table; `name` = plan name, `result` = trap name, 4 nullable ingredient columns |
| `origins_trap_making_ingredient_recipes` | `(ingredient, recipe)` | 65 | Ingredient → recipe reverse-lookup join table |
| `origins_trap_making_tiers` | `recipe` | 25 | Recipe → required trap-making tier (1–4) |
| `origins_trap_making_unlimited_supply` | `(ingredient, vendor)` | 11 | Vendor/location for unlimited ingredient supplies; `location` nullable |
| `origins_trap_making_effects` | `(name, power, damage_type)` | 26 | Trap name → `damage_type`/`power`/`effect`; all three nullable; Poisoned Caltrop Trap has two rows |

## Usage

All arguments have defaults pointing to the adjacent `trap_making_json/` directory and
the DA family database:

```bash
# Default paths
python3 DA/Origins/trap_making/trap_making_sql/create_or_update_origins_trap_making.py

# Explicit paths
python3 DA/Origins/trap_making/trap_making_sql/create_or_update_origins_trap_making.py \
    /abs/path/to/origins_trap_making_recipes.json \
    /abs/path/to/origins_trap_making_ingredient_recipes.json \
    /abs/path/to/origins_trap_making_tiers.json \
    /abs/path/to/origins_trap_making_unlimited_supply.json \
    /abs/path/to/origins_trap_making_effects.json \
    /abs/path/to/gametools.sqlite3
```

## DB Path

Computed as 3 `.parent` calls from the script file:
`trap_making_sql/` → `trap_making/` → `Origins/` → `DA/` → `DA/database/gametools.sqlite3`

## Upsert Strategy

- **`origins_trap_making_recipes`**: delete by `name` (plan name), re-insert
- **`origins_trap_making_ingredient_recipes`**: delete by `recipe`, re-insert
- **`origins_trap_making_tiers`**: delete by `recipe`, re-insert
- **`origins_trap_making_unlimited_supply`**: full DELETE ALL + re-insert (supply index on `(ingredient, vendor)` — `location` can be NULL for bare vendor names like Bodahn Feddic and Ruck)
- **`origins_trap_making_effects`**: delete all rows for each trap name, re-insert; unique index on `(name, power, damage_type)` to allow Poisoned Caltrop Trap's two rows
