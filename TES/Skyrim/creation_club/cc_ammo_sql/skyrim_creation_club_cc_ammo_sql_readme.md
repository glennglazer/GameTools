# Purpose and Action

This directory holds the SQL loader that upserts CC ammo records into the
`skyrim_smithing_ammo` table, creating it on first run.

## Script

### `create_or_update_skyrim_cc_ammo.py`

Reads `cc_ammo_records.json` from the sibling `cc_ammo_json/` directory and
upserts its 12 records into `skyrim_smithing_ammo`.

**What it does:**
1. On first run (table absent): creates the table via `df.to_sql` and adds a
   unique index on `piece`
2. On subsequent runs: deletes rows whose `piece` matches, then re-inserts

**Target table:** `skyrim_smithing_ammo`

| Column | Type | Notes |
|---|---|---|
| `piece` | TEXT | Unique ammo name |
| `id` | TEXT | Form ID (e.g. `FExxxA01`) |
| `ammo_type` | TEXT | `arrow` or `bolt` |
| `smithing_perk` | TEXT | Smithing perk required (NULL if none) |
| `weight` | REAL | Item weight |
| `value` | INTEGER | Base value in gold |
| `damage` | INTEGER | Base damage |
| `batch_size` | INTEGER | How many are crafted per recipe (NULL if unknown) |
| `firewood` | INTEGER | Quantity of Firewood required |
| `void_salts` | INTEGER | — |
| `fire_salts` | INTEGER | — |
| `frost_salts` | INTEGER | — |
| `soul_gem_arrowhead` | INTEGER | — |
| `dragon_bone` | INTEGER | — |
| `corkbulb_root` | INTEGER | — |
| `bonemeal` | INTEGER | — |

## Usage

Run with defaults (reads from `cc_ammo_json/`, writes to shared DB):

```bash
python3 TES/Skyrim/creation_club/cc_ammo_sql/create_or_update_skyrim_cc_ammo.py
```

Or with explicit paths:

```bash
python3 TES/Skyrim/creation_club/cc_ammo_sql/create_or_update_skyrim_cc_ammo.py \
  /abs/path/to/cc_ammo_records.json \
  /abs/path/to/database/gametools.sqlite3
```
