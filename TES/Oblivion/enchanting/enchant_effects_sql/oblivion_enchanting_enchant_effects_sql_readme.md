# Purpose and Action

Loads `oblivion_enchant_effects.json` into SQLite as the `oblivion_enchant_effects` table using a full-replace upsert pattern.

## Script

### `create_or_update_oblivion_enchant_effects.py`

Reads `oblivion_enchant_effects.json` and upserts into `oblivion_enchant_effects` (all rows deleted then re-inserted on each run). Creates a unique index on `effect_id` on first run.

**Table:** `oblivion_enchant_effects`

| Column | Type | Notes |
|--------|------|-------|
| `effect_id` | TEXT (PK) | 4-letter Construction Set code (e.g., `BRDN`) |
| `base_cost` | REAL | Effective base cost used in potion value/enchantment formulas; values are fractional |
| `barter_factor` | REAL | Barter markup factor; mostly integers but some are fractional (e.g., 12.5 for Light) |
| `school` | TEXT | Magic school: Alteration, Conjuration, Destruction, Illusion, Mysticism, Restoration |
| `description` | TEXT | Plain-text effect description |

111 total records. Special Spell Effects (cut/disabled effects) are excluded.

## Usage

```bash
python3 TES/Oblivion/enchanting/enchant_effects_sql/create_or_update_oblivion_enchant_effects.py \
  TES/database/gametools.sqlite3
```
