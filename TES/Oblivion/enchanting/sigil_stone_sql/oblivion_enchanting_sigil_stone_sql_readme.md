# Purpose and Action

Loads the three sigil stone JSON files into SQLite as three related tables, all keyed on `form_id`.

## Script

### `create_or_update_oblivion_sigil_stone.py`

Reads `sigil_stone_records.json`, `sigil_stone_weapon_magnitudes.json`, and `sigil_stone_armor_magnitudes.json` and upserts all three tables using a full-replace pattern (all rows deleted then re-inserted on each run).

**Tables created/updated:**
- `oblivion_sigil_stone` — Form ID (PK), weapon effect, armor effect; 150 rows
- `oblivion_sigil_stone_weapon_magnitudes` — Form ID (PK), 10 nullable int columns (magnitude + charges for each of 5 levels); 150 rows
- `oblivion_sigil_stone_armor_magnitudes` — Form ID (PK), 5 nullable int columns (magnitude for each of 5 levels); 150 rows

A unique index on `form_id` is created on first run for each table.

## Usage

```bash
python3 TES/Oblivion/enchanting/sigil_stone_sql/create_or_update_oblivion_sigil_stone.py \
  TES/database/gametools.sqlite3
```
