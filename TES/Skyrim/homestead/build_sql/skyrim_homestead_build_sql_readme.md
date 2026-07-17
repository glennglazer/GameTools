# Skyrim Homestead Build SQL Loader

**Script**: `create_or_update_skyrim_homestead_build.py`

Loads `build_records.json` into the `skyrim_homestead_build` table using full-replace (not the diff-based upsert used by other tables in this project).

## Table: `skyrim_homestead_build`

| Column | Type | Notes |
|--------|------|-------|
| section | TEXT | Item/component being built; duplicates enumerated as `_1`, `_2`, etc. |
| location | TEXT | Build context: `Small House`, `Tower`, `Main_Hall_Downstairs_Containers`, `Cellar_Divine_Shrines`, etc. |
| stage | TEXT | Wiki stage label (`Stage 1`–`Stage 7`); NULL for furnishing and cellar items |
| sawn_log … dragon_scales | INTEGER | 47 material columns; 0 = not required for this item |

Index: `idx_skyrim_homestead_build` on `(section, location)`.

160 rows total.

## Update strategy

**Full-replace** on every run: all rows are deleted (`DELETE FROM skyrim_homestead_build`) and re-inserted. This differs from the diff-based upsert used by every other table. The driver does not check for diff files before running this loader.

## Usage

```bash
python3 build_sql/create_or_update_skyrim_homestead_build.py \
  build_json/build_records.json \
  /abs/path/to/database/gametools.sqlite3
```
