# skyrim_disenchant_weapons_sql

SQL loader: creates and incrementally updates `skyrim_enchant_disenchant_weapons` in `TES/database/gametools.sqlite3`.

## Script

`create_or_update_skyrim_enchant_disenchant_weapons.py`

## Table: `skyrim_enchant_disenchant_weapons`

| Column | Type | Notes |
|---|---|---|
| `effect` | TEXT | Enchantment name, e.g. "Absorb Health" |
| `item` | TEXT | Item to disenchant, e.g. "All weapons of Absorption" |
| `note` | TEXT | Nullable; e.g. "Has unique version of effect." |

Unique index on `(effect, item)`.

Generic magic weapon entries use the "All weapons of X" form (e.g. "All weapons of Absorption") — these represent any weapon with that enchantment suffix. Unique named items appear by their specific name.

## Example queries

```sql
-- What weapons can I disenchant to learn Frost Damage?
SELECT item, note FROM skyrim_enchant_disenchant_weapons
WHERE effect = 'Frost Damage'
ORDER BY item;

-- Which weapon effects can I learn from the Notched Pickaxe?
SELECT effect FROM skyrim_enchant_disenchant_weapons
WHERE item = 'Notched Pickaxe';
```

## Usage

```bash
python3.11 TES/Skyrim/enchanting/disenchant_weapons_sql/create_or_update_skyrim_enchant_disenchant_weapons.py
```

Reads diff files from `../disenchant_weapons_json/`. Exits silently with code 0 if no diff files exist.
