# Purpose and Action

This directory holds the script that generates the CC tempering materials JSON.
Unlike other parsers, the data here is hardcoded rather than scraped — the
tempering material for each CC smithing category was read directly from the CC
armor wiki pages.

## Script

### `skyrim_cc_materials.py`

Writes `cc_tempering_materials.json` with 7 new smithing category entries for
`skyrim_tempering_materials`.

**New categories:**

| Smithing category | Tempering material |
|---|---|
| Amber | Refined Amber |
| Dark | Quicksilver Ingot |
| Golden | Gold Ingot |
| Madness | Madness Ingot |
| Silver | Silver Ingot |
| Chitin | Chitin Plate |
| Vigil | Steel Ingot |

**JSON record format:**
```json
{"smithing_category": "Amber", "crafting_material": "Refined Amber"}
```

## Usage

```bash
python3 TES/Skyrim/creation_club/cc_materials_json/skyrim_cc_materials.py \
  /abs/path/to/TES/Skyrim/creation_club/cc_materials_json/cc_tempering_materials.json
```

The output file is already checked in; this script only needs to be re-run if
new CC smithing categories are added.
