# Purpose and Action

Loads `skyrim_enchant_souls` from JSON into SQLite. Drops and recreates the table on every run to ensure `soul_size` is stored as INTEGER (the legacy pipeline used TEXT).

## Script

### `create_or_update_skyrim_enchant_souls.py`

Reads `skyrim_enchant_souls.json` from the sibling `creature_souls_json/` directory and loads 105 records into `skyrim_enchant_souls`.

**Target table:** `skyrim_enchant_souls`

| Column | Type | Notes |
|---|---|---|
| `name` | TEXT | Creature or NPC name |
| `soul_size` | INTEGER | Charge capacity: 250/500/1000/2000/3000 |

Unique index on `(name, soul_size)`. Creatures with multiple soul levels appear as multiple rows (e.g. Draugr Deathlord at 1000, 2000, and 3000). The generic "NPC" entry covers all humanoid NPCs (soul_size=3000).

## Usage

```bash
python3 TES/Skyrim/enchanting/creature_souls_sql/create_or_update_skyrim_enchant_souls.py
```
