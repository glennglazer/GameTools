# Purpose and Action

Parses Skyrim creature souls from the UESP `Skyrim:Souls` page into JSON records for `skyrim_enchant_souls`.

## Script

### `skyrim_parse_creature_souls_to_json.py`

Reads `skyrim_creature_souls_uesp_raw.json` from the sibling `souls_parse/` directory and outputs `skyrim_enchant_souls.json` with 105 records.

**Source page structure:** The page has three tables:
1. An "incomplete" notice table (skipped)
2. Mapping table: Soul Level | Charge Capacity | Creature Level (Petty=250 … Grand=3000)
3. Creature table: Creature | Soul Level (113 data rows after header)

**Parsing decisions:**
- Leveled souls (containing "Leveled" or "No soul") are skipped
- Parenthetical qualifiers are stripped: "Common (Shaman)" → Common, "Greater (Other)" → Greater
- **Rowspan rows**: creatures with multiple soul levels produce one record per fixed level. Examples: Draugr Deathlord (Common/Greater/Grand = 3 rows), Corrupted Shade (Leveled+Petty → 1 row kept)
- A generic **NPC** entry (soul_size=3000) is added since all humanoid NPCs have Black souls with Grand capacity

**JSON record format:**
```json
{"name": "Chicken", "soul_size": 250}
```

## Usage

```bash
python3 TES/Skyrim/enchanting/creature_souls_json/skyrim_parse_creature_souls_to_json.py
```
