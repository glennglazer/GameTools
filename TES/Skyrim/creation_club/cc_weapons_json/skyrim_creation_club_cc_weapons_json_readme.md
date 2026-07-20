# Purpose and Action

This directory holds the parser that converts CC weapons raw HTML sections into
JSON records compatible with the `skyrim_smithing_weapons` table.

## Script

### `skyrim_parse_cc_weapons.py`

Reads `*_raw.json` files from the sibling `cc_parse/` directory and outputs
`cc_weapons_records.json` containing 40 records (4 crossbows + 36 weapons).

**Sections parsed:**

| Page key | Section | Smithing perk | Notes |
|---|---|---|---|
| elven | 6 | Elven Smithing | crossbows only |
| daedric | 7 | Daedric Smithing | crossbows only |
| amber | 4 | Glass Smithing | all weapons |
| dark | 3 | Daedric Smithing | all weapons |
| madness\_ore | 4 | Ebony Smithing | all weapons |
| golden | 3 | Daedric Smithing | all weapons |

The Elven and Daedric pages also contain vanilla weapons; the `crossbow_only`
flag filters to rows where "crossbow" appears in the piece name.

Madness and Golden weapon tables use a split format (Name and ID in separate
columns) rather than the combined name+ID cell used by other pages; the parser
detects and handles both formats automatically.

**JSON record format:**
```json
{
  "piece": "Amber Sword",
  "id": "FExxx901",
  "smithing_perk": "Glass Smithing",
  "weight": 10.0,
  "value": 345,
  "damage": 10,
  "speed": 1.0,
  "reach": 1.0,
  "stagger": 0.75,
  "refined_amber": 2,
  "firewood": 1,
  ...
}
```

## Usage

```bash
python3 TES/Skyrim/creation_club/cc_weapons_json/skyrim_parse_cc_weapons.py \
  /abs/path/to/TES/Skyrim/creation_club/cc_parse \
  /abs/path/to/TES/Skyrim/creation_club/cc_weapons_json/cc_weapons_records.json
```
