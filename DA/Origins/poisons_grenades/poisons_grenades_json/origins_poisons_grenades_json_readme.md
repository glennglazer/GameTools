# origins_poisons_grenades_json — DAO Poisons & Grenades Parser

## Purpose

Parses raw poison-making wikitext (`poisons_grenades_raw.json`) into four structured JSON files
for the SQL loader.

## Inputs / Outputs

| Argument | File | Description |
|----------|------|-------------|
| `raw_json` | `poisons_grenades_raw.json` | Output of the scraper |
| `recipes_json` | `origins_poisons_grenades_recipes.json` | Wide recipe table with `type` column (25 rows) |
| `ingredient_recipes_json` | `origins_poisons_grenades_ingredient_recipes.json` | Ingredient → recipe join table (87 rows) |
| `tiers_json` | `origins_poisons_grenades_tiers.json` | Recipe → required tier (25 rows) |
| `supply_json` | `origins_poisons_grenades_unlimited_supply.json` | Unlimited supply vendor/location records (15 rows) |

## Usage

```bash
python3 DA/Origins/poisons_grenades/poisons_grenades_json/origins_parse_poisons_grenades.py \
    /abs/path/to/poisons_grenades_raw.json \
    /abs/path/to/origins_poisons_grenades_recipes.json \
    /abs/path/to/origins_poisons_grenades_ingredient_recipes.json \
    /abs/path/to/origins_poisons_grenades_tiers.json \
    /abs/path/to/origins_poisons_grenades_unlimited_supply.json
```

## Output Schemas

### `origins_poisons_grenades_recipes.json`
Wide-format recipe table with `type` column and 4 nullable ingredient columns:

```json
{
  "name": "Fire Bomb Recipe",
  "type": "grenade",
  "result": "Fire Bomb",
  "description": "Recipe for fire bombs.",
  "item_id": "gen_im_cft_psn_206",
  "tier": 2,
  "ingredient1": "Fire Crystal",
  "quantity1": 1,
  "ingredient2": "Flask",
  "quantity2": 1,
  "ingredient3": "Corrupter Agent",
  "quantity3": 1,
  "ingredient4": null,
  "quantity4": null
}
```

`type` is an enumeration: `"poison"` or `"grenade"`. All 5 DAO grenades are tier 2.

### `origins_poisons_grenades_ingredient_recipes.json`
Normalised ingredient → recipe join table:

```json
{"ingredient": "Fire Crystal", "recipe": "Fire Bomb Recipe", "quantity": 1}
```

### `origins_poisons_grenades_tiers.json`
Minimum tier required per recipe:

```json
{"recipe": "Fire Bomb Recipe", "tier": 2}
```

### `origins_poisons_grenades_unlimited_supply.json`
Unlimited supply records (one row per vendor):

```json
{"ingredient": "Flask", "vendor": "Figor", "location": "Figor's Imports in Orzammar", "note": "you must scare off the Carta thugs first"}
```

## Parsing Notes

- **Type classification**: result name looked up in `grenade_results` set from raw JSON; match → `"grenade"`, no match → `"poison"`
- **Tier**: extracted from `|requires=[[Poison-Making#...|Poison-Making: Rank N]]` — handles both `#Tiers` and bare `#` anchor variants
- **"your " prefix**: location strings beginning with "your " (e.g. "your Party Camp") are stripped to "Party Camp"
- **Trailing period on notes**: regex handles `(note text).` pattern — the period after `)` is consumed, not included in the location
- **Vendor splitting**: same depth-counter logic as herbalism parser; handles 4-vendor Flask entry correctly
