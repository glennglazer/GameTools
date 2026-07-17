# Skyrim Homestead Exclusive Exterior JSON

**Script**: `skyrim_parse_homestead_exclusive_exterior.py`

Emits a hardcoded list of the three manor-to-exclusive-exterior mappings. No wiki scraping required — the mapping is fixed game content that does not change.

## Output

`exclusive_exterior_records.json` — list of 3 dicts:

```json
[
  {"manor": "Lakeview Manor",  "exclusive_exterior": "Apiary"},
  {"manor": "Windstad Manor",  "exclusive_exterior": "Fish Hatchery"},
  {"manor": "Heljarchen Hall", "exclusive_exterior": "Grain Mill"}
]
```

Note: the three exclusive exteriors also appear as rows in `skyrim_homestead_build` with `location = 'Exterior'` (same as all other Stage 6 exterior items). This table is a separate lookup for the manor→exclusive mapping only.

## Usage

```bash
python3 exclusive_exterior_json/skyrim_parse_homestead_exclusive_exterior.py \
  exclusive_exterior_json/exclusive_exterior_records.json
```
