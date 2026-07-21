# cc_effects_json — Skyrim CC alchemy effects JSON parser

## Purpose

Transforms `cc_parse/cc_effects_raw.json` (scraped from UESP individual CC effect pages)
into `cc_effects_records.json`, a list of records for the SQL loader.

This stage exists because CC-only alchemy effects are absent from the base-game
`Skyrim:Alchemy_Effects` page and therefore have `NULL` `base_magnitude` after the main
alchemy pipeline runs.  The CC effects pipeline fills those NULLs in.

## Script

`skyrim_parse_cc_effects_to_json.py`

### Input

`cc_parse/cc_effects_raw.json` — dict keyed by effect name, values are dicts with
`base_cost`, `base_mag`, `base_dur` (scraped by `skyrim_scrape_cc_effects.py`).

```json
{
  "Fortify Persuasion": {"base_cost": 0.5, "base_mag": 1, "base_dur": 30}
}
```

### Output

`cc_effects_records.json` — list of records, one per CC effect.
Only `base_magnitude` is retained; the SQL loader performs an UPDATE, not an INSERT.

```json
[
  {"effect": "Fortify Persuasion", "base_magnitude": 1}
]
```

### Usage

```bash
python3 TES/Skyrim/creation_club/cc_effects_json/skyrim_parse_cc_effects_to_json.py \
  [infile]  # default: cc_parse/cc_effects_raw.json
  [outfile] # default: cc_effects_json/cc_effects_records.json
```

Both arguments are optional; the defaults assume the standard directory layout.

## Notes

- Effects whose raw JSON entry lacks `base_mag` are skipped with a warning on stderr.
- The `parse()` function can be called directly with a raw dict (used by unit tests).
- `base_magnitude` is cast to `int` to ensure the SQL loader stores `INTEGER`, not `REAL`.
