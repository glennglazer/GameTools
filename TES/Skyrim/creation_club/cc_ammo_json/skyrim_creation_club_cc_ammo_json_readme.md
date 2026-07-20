# Purpose and Action

This directory holds the parser that converts CC ammo raw HTML sections into
JSON records for the `skyrim_smithing_ammo` table.

## Script

### `skyrim_parse_cc_ammo.py`

Reads `*_raw.json` files from the sibling `cc_parse/` directory and outputs
`cc_ammo_records.json` containing 12 records.

**Sources:**

| Source | Sections | Records |
|---|---|---|
| Rare Curios Items | 2 (arrows), 3 (bolts) | 6 (1 arrow + 5 bolts) |
| Arcane Archer Pack Items | 1 | 6 arrows (Bound Arrow excluded) |

**Rare Curios records:** The wiki table lists stats only; crafting quantities are
not specified there.  All material columns are stored as `0`.  The smithing perk
is parsed from the Notes column text.

**Arcane Archer records:** Standard material table with an `Other` column that
encodes extra materials as pipe-separated `qty mat_name` entries (e.g.
`1|Soul Gem Arrowheads`).  The `Makes N arrows` note is parsed as `batch_size`.
Bound Arrow is excluded because it is summoned via a spell, not crafted.

**JSON record format:**
```json
{
  "piece": "Hunting Arrow",
  "id": "FExxxA01",
  "ammo_type": "arrow",
  "smithing_perk": null,
  "weight": 0.0,
  "value": 3,
  "damage": 8,
  "batch_size": 24,
  "firewood": 1,
  "void_salts": 0,
  "fire_salts": 0,
  "frost_salts": 0,
  "soul_gem_arrowhead": 0,
  "dragon_bone": 0,
  "corkbulb_root": 0,
  "bonemeal": 0
}
```

## Usage

```bash
python3 TES/Skyrim/creation_club/cc_ammo_json/skyrim_parse_cc_ammo.py \
  /abs/path/to/TES/Skyrim/creation_club/cc_parse \
  /abs/path/to/TES/Skyrim/creation_club/cc_ammo_json/cc_ammo_records.json
```
