# Skyrim Enchanting Perks JSON Parser

**Script**: `skyrim_parse_enchant_perks_to_json.py`

Reads `enchant_parse/skyrim_enchant_perks_raw.txt` and emits `skyrim_enchant_perks.json` plus diff files for the SQL loader.

## Output

`skyrim_enchant_perks.json` — list of dicts:
```json
[{"name": "Enchanter (1/5)", "skill_level": 0, "prerequisite": "None",
  "description": "New enchantments are 20% stronger."}, ...]
```

Also writes `skyrim_enchant_perks.upsert.json` and `skyrim_enchant_perks.delete.json` (sentinel `{}` when empty).

## Usage

```bash
python3 perks_json/skyrim_parse_enchant_perks_to_json.py [infile [outfile]]
```
