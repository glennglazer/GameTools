# Skyrim Homestead Build JSON Parser

**Script**: `skyrim_parse_homestead_build.py`

Reads raw HTML from three scraper outputs and produces a single flat list of build records, one per buildable item.

## Inputs

| Argument | File | Source |
|----------|------|--------|
| `homestead_json` | `homestead_parse/homestead_raw.json` | Homestead_(Hearthfire) wiki page |
| `main_hall_json` | `main_hall_parse/main_hall_raw.json` | Main_Hall wiki page |
| `cellar_json` | `cellar_parse/cellar_raw.json` | Cellar wiki page |

## Output

`build_records.json` — list of dicts, one per buildable item (160 records):

```json
[
  {"section": "House, Foundation", "location": "Small House", "stage": "Stage 1",
   "sawn_log": 1, "quarried_stone": 10, "nails": 0, ...},
  {"section": "Barrel_1", "location": "Cellar_Containers", "stage": null,
   "sawn_log": 1, "nails": 1, "iron_ingot": 1, ...},
  ...
]
```

Fields: `section`, `location`, `stage` (null for furnishing/cellar items), then 47 material columns (integer, 0 if not used).

## Three parse modes

| Mode | Function | Used for |
|------|----------|----------|
| `construction` | `parse_construction_table` | Stage-by-stage tables with Stage/Section/material columns; tracks `rowspan` and empty `<th>` for continuing stage |
| `item_table` | `parse_item_table` | Furnishing tables with Item/material columns; handles `<th>` or `<td>` value cells |
| `shrine_bullet` | `parse_shrine_bullet` | Individual shrine sections using `<ul><li>N x Item</li>` lists |

## Duplicate enumeration

Items that appear as multiple distinct rows within the same location are suffixed `_1`, `_2`, etc. (e.g., four Barrels → `Barrel_1` through `Barrel_4`). Query with `LIKE 'Barrel%'` to match all instances.

## Usage

```bash
python3 build_json/skyrim_parse_homestead_build.py \
  homestead_parse/homestead_raw.json \
  main_hall_parse/main_hall_raw.json \
  cellar_parse/cellar_raw.json \
  build_json/build_records.json
```
