# skyrim_disenchant_weapons_json

Parser: reads `disenchant_weapons_raw.json` (from `disenchant_parse/`) and produces the canonical JSON snapshot plus diff files for the SQL loader.

## Script

`skyrim_parse_disenchant_weapons_to_json.py`

## Input

`../disenchant_parse/disenchant_weapons_raw.json` — list of `{effect, item, note}` records produced by the scraper.

## Outputs

| File | Description |
|---|---|
| `disenchant_weapons.json` | Canonical snapshot of all records |
| `disenchant_weapons.upsert.json` | Records that are new or changed since the last run |
| `disenchant_weapons.delete.json` | Records removed since the last run |

## Record format

```json
[
  {"effect": "Absorb Health",  "item": "All weapons of Absorption",   "note": null},
  {"effect": "Absorb Magicka", "item": "Drainspell Bow",              "note": "Has unique version of effect."},
  {"effect": "Turn Undead",    "item": "Blessed weapons",             "note": null},
  ...
]
```

## Usage

```bash
python3 TES/Skyrim/enchanting/disenchant_weapons_json/skyrim_parse_disenchant_weapons_to_json.py
```

## Diff key

`(effect, item)` — composite.
