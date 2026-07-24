# skyrim_disenchant_apparel_json

Parser: reads `disenchant_apparel_raw.json` (from `disenchant_parse/`) and produces the canonical JSON snapshot plus diff files for the SQL loader.

## Script

`skyrim_parse_disenchant_apparel_to_json.py`

## Input

`../disenchant_parse/disenchant_apparel_raw.json` — list of `{effect, item, note}` records produced by the scraper.

## Outputs

| File | Description |
|---|---|
| `disenchant_apparel.json` | Canonical snapshot of all records |
| `disenchant_apparel.upsert.json` | Records that are new or changed since the last run |
| `disenchant_apparel.delete.json` | Records removed since the last run |

Diff files are consumed and removed by the SQL loader on the next run.

## Record format

```json
[
  {"effect": "Fortify Alchemy", "item": "Bracers of Alchemy", "note": "All levels of enchantment"},
  {"effect": "Fortify Alchemy", "item": "Muiri's Ring",        "note": null},
  ...
]
```

`note` is `null` when no context annotation applies.

## Usage

```bash
python3 TES/Skyrim/enchanting/disenchant_apparel_json/skyrim_parse_disenchant_apparel_to_json.py
```

## Diff key

`(effect, item)` — composite.  Effect names are canonical UESP names (e.g. "Regenerate Health", not the Fandom wiki alias "Fortify Healing Rate").
