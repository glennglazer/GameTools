# Purpose and Action

This directory holds the SQL loader that upserts Morrowind alchemy apparatus
records into `morrowind_alchemy_apparatus`, creating it on first run.

## Script

### `create_or_update_morrowind_alchemy_apparatus.py`

Reads `morrowind_apparatus_records.json` from the sibling `apparatus_json/`
directory and upserts its 22 records into `morrowind_alchemy_apparatus`.

**What it does:**
1. On first run (table absent): creates the table via `df.to_sql` and adds a
   unique index on `id`
2. On subsequent runs: deletes rows whose `id` matches, then re-inserts

**Target table:** `morrowind_alchemy_apparatus`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT | Unique item ID (e.g. `apparatus_a_mortar_01`) |
| `name` | TEXT | Item name as it appears in-game |
| `weight` | REAL | Item weight |
| `value` | INTEGER | Base value in gold |
| `quality` | REAL | Apparatus quality (0.5 – 2.0); higher = better potions |

## Usage

Run with defaults (reads from `apparatus_json/`, writes to shared DB):

```bash
python3 TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py
```

Or with explicit paths:

```bash
python3 TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py \
  /abs/path/to/morrowind_apparatus_records.json \
  /abs/path/to/database/gametools.sqlite3
```
