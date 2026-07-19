# Skyrim Enchantment Effects JSON Parser

**Script**: `skyrim_parse_enchant_effects_to_json.py`

Reads `enchant_parse/skyrim_enchant_effects_raw.txt` and emits `skyrim_enchant_weapons.json` plus diff files.

## Output

`skyrim_enchant_weapons.json` — list of dicts:
```json
[{"name": "Absorb Health", "school": "Destruction"},
 {"name": "Banish", "school": "Conjuration"}, ...]
```

## Usage

```bash
python3 enchant_effects_json/skyrim_parse_enchant_effects_to_json.py [infile [outfile]]
```
