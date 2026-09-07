# origins_herbalism_sql — DAO Herbalism SQL Loader

## Purpose

Loads the five herbalism JSON files into the GameTools SQLite database (`DA/database/gametools.sqlite3`), creating tables on first run and upserting on subsequent runs.

## Tables Created

| Table | Key | Rows | Description |
|-------|-----|------|-------------|
| `origins_herbalism_recipes` | `name` | 27 | Wide recipe table with 4 nullable ingredient columns |
| `origins_herbalism_ingredient_recipes` | `(ingredient, recipe)` | 91 | Ingredient → recipe reverse-lookup join table |
| `origins_herbalism_tiers` | `recipe` | 27 | Recipe → required herbalism tier (1–4) |
| `origins_herbalism_unlimited_supply` | `(ingredient, vendor, location)` | 12 | Vendor/location for unlimited ingredient supplies |
| `origins_herbalism_potion_effects` | `name` | 27 | Crafted item type/power/verbatim effects; type/power NULL for buffs |

## Usage

All arguments have defaults pointing to the adjacent `herbalism_json/` directory and the DA family database:

```bash
# Default paths (run from any directory)
python3 DA/Origins/herbalism/herbalism_sql/create_or_update_origins_herbalism.py

# Explicit paths
python3 DA/Origins/herbalism/herbalism_sql/create_or_update_origins_herbalism.py \
    /abs/path/to/origins_herbalism_recipes.json \
    /abs/path/to/origins_herbalism_ingredient_recipes.json \
    /abs/path/to/origins_herbalism_tiers.json \
    /abs/path/to/origins_herbalism_unlimited_supply.json \
    /abs/path/to/origins_herbalism_potion_effects.json \
    /abs/path/to/gametools.sqlite3
```

## Upsert Strategy

- **`origins_herbalism_recipes`**: delete by `name`, re-insert
- **`origins_herbalism_ingredient_recipes`**: delete by `recipe`, re-insert all ingredient rows for that recipe
- **`origins_herbalism_tiers`**: delete by `recipe`, re-insert
- **`origins_herbalism_unlimited_supply`**: full DELETE ALL + re-insert (small static table; `vendor` is nullable so a composite key would not be straightforward)
- **`origins_herbalism_potion_effects`**: delete by `name`, re-insert

Unique indexes are created on first run only. The upsert guard pattern checks `sqlite_master` before deleting to avoid errors on initial load.

## DB Path

Computed as 3 `.parent` calls from the script file:
`herbalism_sql/` → `herbalism/` → `Origins/` → `DA/` → `DA/database/gametools.sqlite3`
