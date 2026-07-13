# Purpose and Action

This directory holds the script that loads Oblivion enchanting data into the shared SQLite
database.  Oblivion (2006) is a finished game, so the source data is static CSV maintained
in the sibling `enchant_parse/` directory.

## Script

### `create_or_update_oblivion_enchant_tables.py`

Reads `soul_gems.csv` directly from `../enchant_parse/` — no intermediate JSON step.

**What it does:**
1. Parses `soul_gems.csv` (columns: Type, Mod Name, ObjectIndex, Editor ID, Weight, Value)
2. Compares against the current contents of `oblivion_enchant_soul_gems` in the database
3. If the data matches, exits cleanly with a "no changes" log message
4. If there are differences (or the table does not yet exist), replaces all rows and
   recreates the unique index on `ID`

**Target table:** `oblivion_enchant_soul_gems`
| Column | Type | Notes |
|---|---|---|
| `ID` | TEXT | Editor ID — unique key (e.g. `AzurasStar`) |
| `object_index` | TEXT | Form ID (e.g. `0x000193`) |
| `weight` | REAL | Item weight |
| `value` | INTEGER | Base gold value |

## Usage

Run with defaults (reads from `enchant_parse/soul_gems.csv`, writes to shared DB):

```bash
python3 TES/Oblivion/enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py
```

Or with explicit paths:

```bash
python3 TES/Oblivion/enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py \
  /abs/path/to/soul_gems.csv \
  /abs/path/to/database/gametools.sqlite3
```

All paths must be absolute when supplied.
