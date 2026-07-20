# Purpose and Action

This directory holds the parser that converts the CC Aquarium section of the
UESP Main Hall page into JSON records for the `skyrim_homestead_build` table.

## Script

### `skyrim_parse_cc_homestead.py`

Reads `main_hall_raw.json` from the sibling `cc_parse/` directory (section 9,
the Aquarium) and outputs `cc_homestead_records.json` containing 18 records
with `location = "Main_Hall_Aquarium"`.

**Table format note:** The Aquarium section uses a non-standard wiki table
structure (Type | Options | Materials | Notes) rather than the standard
homestead format.  Rows have 3–5 cells due to rowspan on the Type icon column.
The parser reads cells right-to-left: last cell = Notes, second-to-last =
Materials, third-to-last = Name.  Material quantities are free-text comma-
separated (e.g. `2 Sawn Log, 4 Nails, Iron Fittings`).

Duplicate section names (e.g. `Fish Plaques (3)` appears three times) are
de-duplicated by appending `_1`, `_2`, `_3` suffixes, matching the `Barrel_1`
/ `Barrel_2` pattern used throughout `skyrim_homestead_build`.

**JSON record format:**
```json
{
  "section": "Aquarium",
  "location": "Main_Hall_Aquarium",
  "stage": null,
  "item": "Fish Plaque_1",
  "sawn_log": 0,
  "quarried_stone": 0,
  "nails": 4,
  "clay": 0,
  "iron_fittings": 0,
  "iron_ingot": 0,
  "glass": 2,
  "leather_strips": 0,
  "mudcrab_chitin": 0,
  "goat_horns": 0,
  ...
}
```

## Usage

```bash
python3 TES/Skyrim/creation_club/cc_homestead_json/skyrim_parse_cc_homestead.py \
  /abs/path/to/TES/Skyrim/creation_club/cc_parse \
  /abs/path/to/TES/Skyrim/creation_club/cc_homestead_json/cc_homestead_records.json
```
