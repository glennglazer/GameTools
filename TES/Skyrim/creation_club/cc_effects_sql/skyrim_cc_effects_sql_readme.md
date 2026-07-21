# cc_effects_sql — Skyrim CC alchemy effects SQL loader

## Purpose

Updates `skyrim_alchemy_effects` with `base_magnitude` values for CC-only alchemy
effects.  CC-only effects (e.g. Fortify Persuasion from Rare Curios / Glassfish)
are absent from the base-game `Skyrim:Alchemy_Effects` UESP page, so the main alchemy
pipeline leaves their `base_magnitude` as `NULL`.  This loader performs a targeted
`UPDATE` to fill in those values.

## Script

`create_or_update_skyrim_cc_effects.py`

### Target table

`skyrim_alchemy_effects` — already created by the main Skyrim alchemy pipeline.

| Column | Type | Description |
|---|---|---|
| `name` | TEXT | Ingredient name |
| `effect` | TEXT | Effect name |
| `base_magnitude` | INTEGER | Base magnitude (NULL → filled in by this loader) |

### Input

`cc_effects_json/cc_effects_records.json`

```json
[
  {"effect": "Fortify Persuasion", "base_magnitude": 1}
]
```

### Behaviour

- Runs `UPDATE skyrim_alchemy_effects SET base_magnitude = ? WHERE LOWER(effect) = LOWER(?)`
  for each record — case-insensitive to guard against any wiki capitalisation differences.
- Does **not** INSERT rows; ingredient-effect rows already exist (inserted by the main pipeline).
- Idempotent: running multiple times produces the same result.
- Always runs; no diff files.
- Exits non-zero if the JSON file is missing or the database directory does not exist.

### Usage

```bash
python3 TES/Skyrim/creation_club/cc_effects_sql/create_or_update_skyrim_cc_effects.py \
  [json_file]  # default: cc_effects_json/cc_effects_records.json
  [db]         # default: TES/database/gametools.sqlite3
```

Both arguments are optional; the defaults assume the standard directory layout.

## Pipeline position

This loader is called by `update_tes.py → update_skyrim_cc()` **before** the static
CC content steps (armor, weapons, etc.), immediately after the CC effects scrape and
JSON parse steps.  The scraper re-fetches from UESP each run (unlike most CC raw JSONs,
which are static and checked in).
