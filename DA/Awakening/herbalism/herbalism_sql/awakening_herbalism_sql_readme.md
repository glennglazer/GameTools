# awakening_herbalism_sql — DAO:A Herbalism SQL Loader

## Purpose

Loads the five Awakening herbalism JSON files into the DAO:A GameTools SQLite database
(`DA/Awakening/database/gametools.sqlite3`), creating tables on first run and upserting
on subsequent runs.

The DAO:A database already contains the Origins tables (copied from `DA/database/gametools.sqlite3`
and kept in sync by the chained pipeline in `update_da.py`). The five Awakening tables are
added alongside them under the `awakening_` prefix.

## Tables Created

| Table | Key | Rows | Description |
|-------|-----|------|-------------|
| `awakening_herbalism_recipes` | `name` | 10 | Wide recipe table; `name` = recipe page name, `result` = crafted item name; all Tier 4; `gxa_` item IDs |
| `awakening_herbalism_ingredient_recipes` | `(ingredient, recipe)` | 37 | Ingredient → recipe reverse-lookup join table |
| `awakening_herbalism_tiers` | `recipe` | 10 | Recipe → required herbalism tier (all 4) |
| `awakening_herbalism_unlimited_supply` | `(ingredient, vendor, location)` | 0 | Empty initially — no Awakening supply section on wiki |
| `awakening_herbalism_potion_effects` | `name` | 10 | Crafted item type/power/effects; types: Health/Mana/Stamina |

## DB Path

Computed as 2 `.parent` calls from the script file:
`herbalism_sql/` → `herbalism/` → `Awakening/` → `DA/Awakening/database/gametools.sqlite3`

## Usage

All arguments have defaults pointing to the adjacent `herbalism_json/` directory and
the DAO:A family database:

```bash
# Default paths
python3 DA/Awakening/herbalism/herbalism_sql/create_or_update_awakening_herbalism.py

# Explicit paths
python3 DA/Awakening/herbalism/herbalism_sql/create_or_update_awakening_herbalism.py \
    /abs/path/to/awakening_herbalism_recipes.json \
    /abs/path/to/awakening_herbalism_ingredient_recipes.json \
    /abs/path/to/awakening_herbalism_tiers.json \
    /abs/path/to/awakening_herbalism_unlimited_supply.json \
    /abs/path/to/awakening_herbalism_potion_effects.json \
    /abs/path/to/DA/Awakening/database/gametools.sqlite3
```

## Upsert Strategy

- **`awakening_herbalism_recipes`**: delete by `name`, re-insert
- **`awakening_herbalism_ingredient_recipes`**: delete by `recipe`, re-insert
- **`awakening_herbalism_tiers`**: delete by `recipe`, re-insert
- **`awakening_herbalism_unlimited_supply`**: full DELETE ALL + re-insert; when supply is empty (`[]`)
  the loader creates the table with correct schema (explicit column names) and 0 rows
- **`awakening_herbalism_potion_effects`**: delete by `name`, re-insert

## Empty Supply Handling

The supply JSON is `[]` on initial runs (no Awakening supply section exists on the wiki).
The loader guards against the empty-DataFrame/no-columns problem:

```python
df_supply = pd.DataFrame(supply, columns=_SUPPLY_COLUMNS) if supply else \
            pd.DataFrame(columns=_SUPPLY_COLUMNS)
```

This creates a properly-schemed table with 0 rows rather than a schema-less stub.
