# awakening_trap_making_sql

Loads Awakening trap-making JSON records into the DAO:A SQLite database
(`DA/Awakening/database/gametools.sqlite3`).

## Script

```
create_or_update_awakening_trap_making.py
    <recipes_json> <ingredient_recipes_json> <tiers_json> <supply_json> <effects_json> <db>
```

All arguments have sensible defaults pointing to sibling JSON files and the
DAO:A database (`_SCRIPT_DIR.parent.parent / "database" / "gametools.sqlite3"`).

## Tables created

| Table | Key | Rows | Method |
|-------|-----|------|--------|
| `awakening_trap_making_recipes` | `name` | 4 | `upsert_by_key` |
| `awakening_trap_making_ingredient_recipes` | `(ingredient, recipe)` | 15 | `upsert_ingredient_recipes` |
| `awakening_trap_making_tiers` | `recipe` | 4 | `upsert_by_key` |
| `awakening_trap_making_unlimited_supply` | `(ingredient, vendor, location)` | 0 | `full_replace` |
| `awakening_trap_making_effects` | `name` | 4 | `upsert_by_key` |

## DB path

`_SCRIPT_DIR.parent.parent` → `trap_making_sql/ → trap_making/ → Awakening/`
→ `DA/Awakening/database/gametools.sqlite3`

## Upsert behaviour

- **recipes / tiers / effects**: delete existing rows by key, then re-insert.
- **ingredient_recipes**: delete all rows for each recipe name present in the new
  data, then re-insert.
- **supply**: full DELETE + re-insert (idempotent; always empty for Awakening).

## Schema differences from Origins

The Awakening `effects` table uses a unique index on `name` alone (not the composite
`(name, power, damage_type)` index used by Origins). No Awakening trap has dual
damage types, so the simple key suffices.

## Invoked by

`DA/update_da.py` → `update_awakening_trap_making()` step 4.
