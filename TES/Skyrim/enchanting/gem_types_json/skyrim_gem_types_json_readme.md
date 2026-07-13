# Skyrim Soul Gem Types JSON Parser

**Script**: `skyrim_parse_gem_types_to_json.py`

Reads `souls_parse/skyrim_soul_gem_types_raw.txt` and emits `skyrim_enchant_soulgems.json` plus diff files.

## Output

`skyrim_enchant_soulgems.json` — list of dicts:
```json
[{"name": "Petty Soul Gem", "weight": 0.1, "value": 10,
  "capacity": 250, "trappable_souls": "Can hold creature souls below level 4."}, ...]
```

## Usage

```bash
python3 gem_types_json/skyrim_parse_gem_types_to_json.py [infile [outfile]]
```
