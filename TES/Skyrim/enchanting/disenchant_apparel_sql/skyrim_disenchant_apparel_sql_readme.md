# skyrim_disenchant_apparel_sql

SQL loader: creates and incrementally updates `skyrim_enchant_disenchant_apparel` in `TES/database/gametools.sqlite3`.

## Script

`create_or_update_skyrim_enchant_disenchant_apparel.py`

## Table: `skyrim_enchant_disenchant_apparel`

| Column | Type | Notes |
|---|---|---|
| `effect` | TEXT | Enchantment name, e.g. "Fortify Alchemy" (UESP canonical) |
| `item` | TEXT | Item to disenchant, e.g. "Bracers of Alchemy" |
| `note` | TEXT | Nullable; e.g. "All levels of enchantment", "This is due to a bug." |

Unique index on `(effect, item)`.

## Example queries

```sql
-- What apparel can I disenchant to learn Fortify Smithing?
SELECT item, note FROM skyrim_enchant_disenchant_apparel
WHERE effect = 'Fortify Smithing'
ORDER BY item;

-- Which effects can be learned from boots?
SELECT DISTINCT effect FROM skyrim_enchant_disenchant_apparel
WHERE item LIKE 'Boots%'
ORDER BY effect;
```

## Usage

```bash
python3.11 TES/Skyrim/enchanting/disenchant_apparel_sql/create_or_update_skyrim_enchant_disenchant_apparel.py
```

Reads diff files from `../disenchant_apparel_json/`. Exits silently with code 0 if no diff files exist.
