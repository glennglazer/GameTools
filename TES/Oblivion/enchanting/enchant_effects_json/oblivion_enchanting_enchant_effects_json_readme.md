# Purpose and Action

Parses all six school wikitables from the raw UESP HTML into a flat list of spell effect records, adding a `school` column that identifies the originating school for each effect.

## Script

### `oblivion_parse_enchant_effects.py`

Reads `oblivion_enchant_effects_raw.json` and produces `oblivion_enchant_effects.json` with 111 records (9 Alteration + 36 Conjuration + 21 Destruction + 13 Illusion + 7 Mysticism + 25 Restoration).

**Output record format:**
```json
{"name": "Burden", "effect_id": "BRDN", "base_cost": 0.21, "barter_factor": 0.0, "school": "Alteration", "description": "Reduce the target's maximum encumbrance."}
```

### Parsing notes

- **Effect Name** (first column in the wiki, rendered as `<th scope="row">`) is captured as the `name` field.
- **base_cost** and **barter_factor** are stored as REAL; some values are fractional (e.g., `base_cost=0.051` for Light, `barter_factor=12.5` for Light).
- **Descriptions** are extracted with `separator=" "` to properly space words that are wrapped in inline links, then trimmed of extra whitespace and spaces before punctuation.

## Usage

```bash
python3 TES/Oblivion/enchanting/enchant_effects_json/oblivion_parse_enchant_effects.py
```
