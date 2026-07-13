# Skyrim Apparel Enchantments JSON Parser

**Script**: `skyrim_parse_enchant_apparel_to_json.py`

Reads `enchant_parse/skyrim_enchant_apparel_raw.txt` and emits `skyrim_enchant_apparel.json` plus diff files.

Slot values (True/False strings in raw file) are converted to JSON booleans.

## Output

`skyrim_enchant_apparel.json` — list of dicts:
```json
[{"enchantment": "Fortify Alchemy", "head": true, "chest": false,
  "hands": true, "feet": false, "shield": false, "amulet": true, "ring": true}, ...]
```

## Usage

```bash
python3 enchant_apparel_json/skyrim_parse_enchant_apparel_to_json.py [infile [outfile]]
```
