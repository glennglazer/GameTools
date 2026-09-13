# awakening_runecrafting_sql_readme.md

SQL loader for Dragon Age: Origins – Awakening runecrafting data.

## Script

`create_or_update_awakening_runecrafting.py` — loads all six runecrafting JSON files
into the DAO:A SQLite database (`DA/Awakening/database/gametools.sqlite3`).

## DB path calculation

`_SCRIPT_DIR.parent.parent / "database" / "gametools.sqlite3"`

`runecrafting_sql/` → `runecrafting/` → `Awakening/` → `database/`  (2 `.parent` calls)

## Tables populated

| Table | Unique index | Rows |
|-------|-------------|------|
| `awakening_runecrafting_skill` | `level` | 4 |
| `awakening_runecrafting_tracing_acquisition` | `tracing` | 13 |
| `awakening_runecrafting_hybrid_tracing_acquisition` | `tracing` | 8 |
| `awakening_runecrafting_armor_runes` | `(name, level)` | 39 |
| `awakening_runecrafting_weapon_runes` | `(name, level)` | 67 |
| `awakening_runecrafting_costs` | `name` | 16 |

## Upsert pattern

All six tables use **full-replace**: `DELETE FROM <table>` (if the table exists) then
`df.to_sql(..., if_exists='append')`. This is appropriate because all data is static
wiki content and the row counts are small.

Unique indexes are created with `IF NOT EXISTS` so they survive re-runs without error.

## PRAGMA settings

`synchronous=OFF` and `journal_mode=MEMORY` are set at connection time to speed up the
small-batch loads (no durability requirement during pipeline runs).

## Usage

```bash
# With explicit paths:
python3 DA/Awakening/runecrafting/runecrafting_sql/create_or_update_awakening_runecrafting.py \
    /abs/path/to/awakening_runecrafting_skill.json \
    /abs/path/to/awakening_runecrafting_tracing_acquisition.json \
    /abs/path/to/awakening_runecrafting_hybrid_tracing_acquisition.json \
    /abs/path/to/awakening_runecrafting_armor_runes.json \
    /abs/path/to/awakening_runecrafting_weapon_runes.json \
    /abs/path/to/awakening_runecrafting_costs.json \
    /abs/path/to/gametools.sqlite3

# With defaults (sibling runecrafting_json/ + DAO:A DB):
python3 DA/Awakening/runecrafting/runecrafting_sql/create_or_update_awakening_runecrafting.py
```

## Notes

- The `level` column in `awakening_runecrafting_armor_runes` and
  `awakening_runecrafting_weapon_runes` is nullable — hybrid runes store `NULL`.
  The composite index `(name, level)` handles this: SQLite treats two NULL values as
  distinct in unique indexes, but a single hybrid rune row with `level=NULL` is
  effectively the sole row for that name.
- Crafting cost formulas (the binary-tree recurrence for higher-level runes) are
  **not stored in the DB**. They are computational and belong in the RAG doc.
