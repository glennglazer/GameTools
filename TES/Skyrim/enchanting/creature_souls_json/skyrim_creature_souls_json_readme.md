# Skyrim Creature Souls JSON Parser

**Script**: `skyrim_parse_creature_souls_to_json.py`

Reads `souls_parse/skyrim_creature_souls_raw.txt` and emits `skyrim_enchant_souls.json` plus diff files.

Key is composite: `(creature, soul_size)`.

## Output

`skyrim_enchant_souls.json` — list of dicts:
```json
[{"creature": "Chicken", "soul_size": "petty"},
 {"creature": "Nord", "soul_size": "black"}, ...]
```

Valid soul sizes: petty, lesser, common, greater, grand, black.

## Usage

```bash
python3 creature_souls_json/skyrim_parse_creature_souls_to_json.py [infile [outfile]]
```
