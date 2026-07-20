# Purpose and Action

This directory holds the parser that converts CC armor raw HTML sections into
JSON records compatible with the `skyrim_smithing_armor` table.

## Script

### `skyrim_parse_cc_armor.py`

Reads `*_raw.json` files from the sibling `cc_parse/` directory and outputs
`cc_armor_records.json` containing 105 records across 24 sections from 17 pages.

**Sections parsed:**

| Page key | Section(s) | Smithing perk |
|---|---|---|
| chitin | 4, 7, 8 | Advanced Armors |
| silver | 4 | Advanced Armors |
| orcish | 5, 6 | Orcish Smithing |
| animal\_hides | 8 | (none) |
| iron | 5 | (none) |
| dwarven | 5, 6 | Dwarven Smithing |
| dragon\_items | 3, 6 | Dragon Smithing |
| steel | 6, 10 | Steel Smithing |
| elven | 5 | Elven Smithing |
| ebony | 6 | Ebony Smithing |
| daedric | 4, 6 | Daedric Smithing |
| stalhrim | 6 | Ebony Smithing |
| vigil\_armor | 0 | Steel Smithing |
| amber | 3 | Glass Smithing |
| dark | 2 | Daedric Smithing |
| madness\_ore | 3 | Ebony Smithing |
| golden | 2 | Daedric Smithing |

**JSON record format:**
```json
{
  "piece": "Chitin Armor",
  "id": "FExxx801",
  "smithing_perk": "Advanced Armors",
  "weight": 20.0,
  "value": 225,
  "armor_rating": 25,
  "iron_ingot": 0,
  "chitin_plate": 2,
  "leather_strips": 3,
  ...
}
```

Fixed columns: `piece`, `id`, `smithing_perk`, `weight`, `value`, `armor_rating`.
Material columns: 24 columns (all zero when that material is not used).

## Usage

```bash
python3 TES/Skyrim/creation_club/cc_armor_json/skyrim_parse_cc_armor.py \
  /abs/path/to/TES/Skyrim/creation_club/cc_parse \
  /abs/path/to/TES/Skyrim/creation_club/cc_armor_json/cc_armor_records.json
```
