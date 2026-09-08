# awakening_herbalism_json — DAO:A Herbalism Parser

## Purpose

Parses raw DAO:A herbalism wikitext (`herbalism_raw.json`) into five structured JSON
files for the SQL loader.

## Inputs / Outputs

| Argument | File | Description |
|----------|------|-------------|
| `raw_json` | `herbalism_raw.json` | Output of the Awakening scraper |
| `recipes_json` | `awakening_herbalism_recipes.json` | Wide recipe table (10 rows) |
| `ingredient_recipes_json` | `awakening_herbalism_ingredient_recipes.json` | Ingredient → recipe join table (37 rows) |
| `tiers_json` | `awakening_herbalism_tiers.json` | Recipe → required tier (10 rows; all Tier 4) |
| `supply_json` | `awakening_herbalism_unlimited_supply.json` | Unlimited supply records (0 rows — no Awakening supply section on wiki) |
| `effects_json` | `awakening_herbalism_potion_effects.json` | Potion effects (10 rows) |

## Usage

```bash
python3 DA/Awakening/herbalism/herbalism_json/awakening_parse_herbalism.py \
    /abs/path/to/herbalism_raw.json \
    /abs/path/to/awakening_herbalism_recipes.json \
    /abs/path/to/awakening_herbalism_ingredient_recipes.json \
    /abs/path/to/awakening_herbalism_tiers.json \
    /abs/path/to/awakening_herbalism_unlimited_supply.json \
    /abs/path/to/awakening_herbalism_potion_effects.json
```

## Output Schemas

### `awakening_herbalism_recipes.json`

Wide-format recipe table. `name` = recipe page name, `result` = crafted item name.
All 10 Awakening recipes have 2–4 ingredients. All use `gxa_` item-ID prefix.

```json
{
  "name": "Master Health Poultice Recipe",
  "result": "Master Health Poultice",
  "description": null,
  "item_id": "gxa_im_cft_hrb_405",
  "tier": 4,
  "ingredient1": "Elfroot", "quantity1": 8,
  "ingredient2": "Flask",   "quantity2": 1,
  "ingredient3": "Distillation Agent", "quantity3": 8,
  "ingredient4": "Concentrator Agent", "quantity4": 8
}
```

### `awakening_herbalism_ingredient_recipes.json`

```json
{"ingredient": "Elfroot", "recipe": "Master Health Poultice Recipe", "quantity": 8}
```

### `awakening_herbalism_tiers.json`

All 10 entries have `"tier": 4`.

```json
{"recipe": "Master Health Poultice Recipe", "tier": 4}
```

### `awakening_herbalism_unlimited_supply.json`

Empty list `[]` — no Awakening-specific supply section exists on the wiki.
The supply table is created with the correct schema but zero rows.

### `awakening_herbalism_potion_effects.json`

```json
{"name": "Superb Health Poultice", "type": "Health",  "power": 250.0, "effects": "Instantly restores (50 + SP) * 5 health"}
{"name": "Master Health Poultice", "type": "Health",  "power": 300.0, "effects": "Instantly restores (50 + SP) * 6 health"}
{"name": "Superb Lyrium Potion",   "type": "Mana",    "power": 250.0, "effects": "Instantly restores (50 + SP) * 5 mana"}
{"name": "Master Lyrium Potion",   "type": "Mana",    "power": 300.0, "effects": "Instantly restores (50 + SP) * 6 mana"}
{"name": "Lesser Stamina Draught", "type": "Stamina", "power": 50.0,  "effects": "Instantly restores (50 + SP) stamina"}
```

`type` values: `Health`, `Mana`, `Stamina` (Stamina is new in Awakening; not in DAO Origins).
`power` = `(50 + SP) * N` evaluated at SP=0.  All 10 effects have non-null type and power.

## Parsing Notes

- **RecipeTransformer format**: identical to DAO Origins (`<onlyinclude>` blocks, same field names)
- **Piped wiki links**: `[[Stamina Draught (Awakening)|Stamina Draught]]` → `Stamina Draught`
- **Stamina type**: new in Awakening; `classify_effect` checks for "restores…stamina" after Health/Mana
- **Multiplier handling**: `(50 + SP) * N` → `power = 50 * N`; absent multiplier defaults to N=1
- **Empty supply**: `locations_wikitext` is `""` → `parse_locations` returns `[]`; SQL loader guards
  against the empty-DataFrame/no-columns problem by supplying explicit column names
