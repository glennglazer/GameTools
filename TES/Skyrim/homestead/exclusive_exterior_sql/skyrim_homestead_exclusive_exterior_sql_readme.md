# Skyrim Homestead Exclusive Exterior SQL Loader

**Script**: `create_or_update_skyrim_homestead_exclusive_exterior.py`

Loads `exclusive_exterior_records.json` into the `skyrim_homestead_exclusive_exterior` table using full-replace.

## Table: `skyrim_homestead_exclusive_exterior`

| Column | Type | Notes |
|--------|------|-------|
| manor | TEXT | unique key: `Lakeview Manor`, `Windstad Manor`, `Heljarchen Hall` |
| exclusive_exterior | TEXT | `Apiary`, `Fish Hatchery`, or `Grain Mill` |

Index: `idx_skyrim_homestead_exclusive_exterior` on `manor`.

3 rows total.

## Update strategy

Full-replace on every run (same as all homestead tables). See `build_sql` readme for rationale.

## Usage

```bash
python3 exclusive_exterior_sql/create_or_update_skyrim_homestead_exclusive_exterior.py \
  exclusive_exterior_json/exclusive_exterior_records.json \
  /abs/path/to/database/gametools.sqlite3
```
