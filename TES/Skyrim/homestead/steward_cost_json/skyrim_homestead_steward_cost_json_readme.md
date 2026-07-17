# Skyrim Homestead Steward Cost JSON Parser

**Script**: `skyrim_parse_homestead_steward_cost.py`

Parses the steward cost bullet list from the Trivia section of `homestead_raw.json` and emits a list of room→gold cost records.

The steward can furnish 12 rooms; the Cellar is excluded (must be built manually by the player).

## Input

`homestead_parse/homestead_raw.json` (section 41, Trivia).

## Output

`steward_cost_records.json` — list of 12 dicts:

```json
[
  {"room": "Small House",     "gold_cost": 1000},
  {"room": "Main Hall",       "gold_cost": 3500},
  ...
]
```

## Usage

```bash
python3 steward_cost_json/skyrim_parse_homestead_steward_cost.py \
  homestead_parse/homestead_raw.json \
  steward_cost_json/steward_cost_records.json
```
