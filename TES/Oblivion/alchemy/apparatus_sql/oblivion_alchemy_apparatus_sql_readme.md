# Purpose and Action

This directory holds the SQL loader that upserts Oblivion alchemy apparatus
records into `oblivion_alchemy_apparatus`, creating it on first run.

## Script

### `create_or_update_oblivion_alchemy_apparatus.py`

Reads `oblivion_apparatus_records.json` from the sibling `apparatus_json/`
directory and upserts its 21 records into `oblivion_alchemy_apparatus`.

**What it does:**
1. On first run (table absent): creates the table via `df.to_sql` and adds a
   unique index on `id`
2. On subsequent runs: deletes rows whose `id` matches, then re-inserts

**Target table:** `oblivion_alchemy_apparatus`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT | Unique 8-hex form ID (e.g. `00010604`) |
| `name` | TEXT | Apparatus type (e.g. `Alembic`) |
| `grade` | TEXT | Quality grade: Novice / Apprentice / Journeyman / Expert / Master |
| `weight` | REAL | Item weight |
| `cost` | INTEGER | Base value in gold |
| `strength` | REAL | Apparatus strength (0.1 – 1.0); higher = better potions |

The two Novice Mortar & Pestle entries (tutorial + regular) have different IDs
and are stored as separate rows; `id` is the unique key.

## Usage

Run with defaults (reads from `apparatus_json/`, writes to shared DB):

```bash
python3 TES/Oblivion/alchemy/apparatus_sql/create_or_update_oblivion_alchemy_apparatus.py
```

Or with explicit paths:

```bash
python3 TES/Oblivion/alchemy/apparatus_sql/create_or_update_oblivion_alchemy_apparatus.py \
  /abs/path/to/oblivion_apparatus_records.json \
  /abs/path/to/database/gametools.sqlite3
```
