# Purpose and Action

Loads `oblivion_enchant_effects.json` into SQLite as the `oblivion_enchant_effects` table using a full-replace upsert pattern.

## Script

### `create_or_update_oblivion_enchant_effects.py`

Reads `oblivion_enchant_effects.json` and loads into `oblivion_enchant_effects` using `if_exists='replace'` (table is dropped and recreated on every run). Unique index on `effect_id` is always recreated via `CREATE UNIQUE INDEX IF NOT EXISTS`.

**Table:** `oblivion_enchant_effects`

| Column | Type | Notes |
|--------|------|-------|
| `name` | TEXT | Human-readable effect name (e.g., `Paralyze`, `Fortify Strength`) |
| `effect_id` | TEXT (unique) | 4-letter Construction Set code (e.g., `BRDN`) |
| `base_cost` | REAL | Effective base cost used in enchantment formulas; values are fractional |
| `barter_factor` | REAL | Barter markup factor; mostly integers but some are fractional (e.g., 12.5 for Light) |
| `school` | TEXT | Magic school: Alteration, Conjuration, Destruction, Illusion, Mysticism, Restoration |
| `description` | TEXT | Plain-text effect description |

111 total records. Special Spell Effects (cut/disabled effects) are excluded.

## Usage

```bash
python3 TES/Oblivion/enchanting/enchant_effects_sql/create_or_update_oblivion_enchant_effects.py \
  TES/database/gametools.sqlite3
```
