# origins_poisons_grenades_sql — DAO Poisons & Grenades SQL Loader

## Purpose

Loads the four poison-making/grenade JSON files into the GameTools SQLite database,
creating tables on first run and upserting on subsequent runs.

## Tables Created

| Table | Key | Rows | Description |
|-------|-----|------|-------------|
| `origins_poisons_grenades_recipes` | `name` | 25 | Wide recipe table; includes `type` column ("poison"/"grenade") and 4 nullable ingredient columns |
| `origins_poisons_grenades_ingredient_recipes` | `(ingredient, recipe)` | 87 | Ingredient → recipe reverse-lookup join table |
| `origins_poisons_grenades_tiers` | `recipe` | 25 | Recipe → required poison-making tier (1–4) |
| `origins_poisons_grenades_unlimited_supply` | `(ingredient, vendor, location)` | 15 | Vendor/location for unlimited ingredient supplies |

## Usage

All arguments have defaults pointing to the adjacent `poisons_grenades_json/` directory and the DA family database:

```bash
# Default paths
python3 DA/Origins/poisons_grenades/poisons_grenades_sql/create_or_update_origins_poisons_grenades.py

# Explicit paths
python3 DA/Origins/poisons_grenades/poisons_grenades_sql/create_or_update_origins_poisons_grenades.py \
    /abs/path/to/origins_poisons_grenades_recipes.json \
    /abs/path/to/origins_poisons_grenades_ingredient_recipes.json \
    /abs/path/to/origins_poisons_grenades_tiers.json \
    /abs/path/to/origins_poisons_grenades_unlimited_supply.json \
    /abs/path/to/gametools.sqlite3
```

## Filtering by Type

To query only grenades or only poisons:
```sql
SELECT * FROM origins_poisons_grenades_recipes WHERE type = 'grenade';
SELECT * FROM origins_poisons_grenades_recipes WHERE type = 'poison';
```

## DB Path

Computed as 3 `.parent` calls from the script file:
`poisons_grenades_sql/` → `poisons_grenades/` → `Origins/` → `DA/` → `DA/database/gametools.sqlite3`

## Upsert Strategy

- **`origins_poisons_grenades_recipes`**: delete by `name`, re-insert
- **`origins_poisons_grenades_ingredient_recipes`**: delete by `recipe`, re-insert
- **`origins_poisons_grenades_tiers`**: delete by `recipe`, re-insert
- **`origins_poisons_grenades_unlimited_supply`**: full DELETE ALL + re-insert
