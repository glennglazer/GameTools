# skyrim smelting — smelting_sql

Loads smelting records into the `skyrim_smelting` table in `gametools.sqlite3`.

## Script

`create_or_update_skyrim_smelting.py`

## Input

`smelting_json/skyrim_smelting.upsert.json` and `skyrim_smelting.delete.json`

## Table: `skyrim_smelting`

Unique index on `(Source_Name, Ingot_Name)`.  
NULL values in `Ingot_Name` (Stalhrim row) are handled with `IS NULL` in DELETE statements.

## Record count

20 rows:
- 9 standard ore → ingot recipes (Corundum, Ebony, Gold, Iron, Malachite, Moonstone, Orichalcum, Quicksilver, Silver)
- 6 Dwemer scrap → Dwarven Metal Ingot recipes
- 2 Steel Ingot rows (Iron Ore + Corundum Ore, each with a Note)
- 2 CC rows (Amber → Refined Amber; Madness Ore → Madness Ingot)
- 1 Stalhrim NULL row

## Usage

```bash
python3 create_or_update_skyrim_smelting.py [json_file [db]]
```

Default paths resolve to `smelting_json/skyrim_smelting.json` and `TES/database/gametools.sqlite3`.
