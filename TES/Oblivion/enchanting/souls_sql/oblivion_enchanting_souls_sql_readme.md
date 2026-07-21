# Purpose and Action

Loads `oblivion_enchant_souls` from JSON into SQLite, creating the table on first run.

## Script

### `create_or_update_oblivion_enchant_souls.py`

Reads `oblivion_souls_records.json` and upserts 51 records into `oblivion_enchant_souls`.

**Target table:** `oblivion_enchant_souls`

| Column | Type | Notes |
|---|---|---|
| `name` | TEXT | Creature or NPC name |
| `soul_size` | INTEGER | Soul strength: 150/300/800/1200/1600 |

Black soul entries (Dremora, NPC(any race), Vampire) share soul_size=1600 with Grand souls.

Unique index on `(name, soul_size)`. Full-replace on every run (delete all, re-insert).

## Usage

```bash
python3 TES/Oblivion/enchanting/souls_sql/create_or_update_oblivion_enchant_souls.py
```
