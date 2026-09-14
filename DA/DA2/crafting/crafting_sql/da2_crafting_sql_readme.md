# DA2 Crafting SQL

Loads the four DA2 crafting JSON files into the DA family SQLite database.

## Script

```
create_or_update_da2_crafting.py [locations_json] [resources_json] [recipes_json] [effects_json] [db]
```

All arguments are optional; defaults point to sibling JSON files and `DA/database/gametools.sqlite3`.

## DB path resolution

```
crafting_sql/         (script location)
  → crafting/
    → DA2/
      → DA/
        → database/gametools.sqlite3
```

Three `.parent` calls from `__file__` reach the DA franchise root.

## Tables created

| Table | Key | Description |
|-------|-----|-------------|
| `da2_crafting_recipe_locations` | `name` | Recipe name → act (JSON) + location text |
| `da2_crafting_resources` | `(name, location, act)` | Crafting resource nodes with act, location, quest, description |
| `da2_crafting_recipes` | `name` | Sparse ingredient table (12 int columns) + Gold/Silver/Bronze crafting fee |
| `da2_crafting_item_effects` | `name` | Crafted item effect text |

## Upsert pattern

All four tables use **full-replace**: DELETE all rows (if the table exists), then `df.to_sql(..., if_exists='append')`. The DA2 crafting data is small and static; the full-replace avoids FK-style tracking of deletes.

## Column ordering (recipes table)

The loader enforces a canonical column order:

```python
["name"] + _INGREDIENT_COLS + ["Gold", "Silver", "Bronze"]
```

Missing ingredient columns are filled with `0` before reordering. This guarantees the column order is stable across re-runs regardless of which ingredients appear in the JSON.

## Indexes

All four indexes are created with `IF NOT EXISTS`:

| Index name | Table | Columns |
|------------|-------|---------|
| `idx_da2_crl_name` | `da2_crafting_recipe_locations` | `name` (unique) |
| `idx_da2_cr_pk` | `da2_crafting_resources` | `(name, location, description, act)` (unique) |
| `idx_da2_crec_name` | `da2_crafting_recipes` | `name` (unique) |
| `idx_da2_cie_name` | `da2_crafting_item_effects` | `name` (unique) |

The `(name, location, description, act)` composite key on `da2_crafting_resources` is needed because the same resource can appear multiple times at the same location in the same act (e.g. two Elfroot nodes at Sundermount Act 1, each with different descriptions). Each distinct node is a separate row since the whole DA2 mechanic hinges on counting distinct nodes found.

## PRAGMA settings

`PRAGMA synchronous=OFF` and `PRAGMA journal_mode=MEMORY` are set at the start of each run for speed. Safe for this use case (static reference data loaded from trusted JSON files).
