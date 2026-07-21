# Purpose and Action

Loads `morrowind_enchant_souls` from JSON into SQLite, creating the table on first run.

## Script

### `create_or_update_morrowind_enchant_souls.py`

Reads `morrowind_souls_records.json` from the sibling `souls_json/` directory and upserts 148 records into `morrowind_enchant_souls`.

**What it does:**
1. On first run (table absent): creates the table via `df.to_sql` and adds a unique index on `(name, soul_size)`
2. On subsequent runs: deletes all rows and re-inserts (full-replace)

**Target table:** `morrowind_enchant_souls`

| Column | Type | Notes |
|---|---|---|
| `name` | TEXT | Creature or NPC name |
| `soul_size` | INTEGER | Soul strength value (e.g. 5, 10, 100, 1000) |

The composite unique key `(name, soul_size)` allows creatures that appear at multiple soul sizes (e.g. Scamp at 10 and 100) to have separate rows.

## Usage

```bash
python3 TES/Morrowind/enchanting/souls_sql/create_or_update_morrowind_enchant_souls.py
```
