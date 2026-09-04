# origins_herbalism_json — DAO Herbalism Parser

## Purpose

Parses raw herbalism wikitext (`herbalism_raw.json`) into four structured JSON files ready for the SQL loader.

## Inputs / Outputs

| Argument | File | Description |
|----------|------|-------------|
| `raw_json` | `herbalism_raw.json` | Output of the scraper |
| `recipes_json` | `origins_herbalism_recipes.json` | Wide recipe table (27 rows) |
| `ingredient_recipes_json` | `origins_herbalism_ingredient_recipes.json` | Ingredient → recipe join table |
| `tiers_json` | `origins_herbalism_tiers.json` | Recipe → required tier (1–4) |
| `supply_json` | `origins_herbalism_unlimited_supply.json` | Unlimited supply vendor/location records |

## Usage

```bash
python3 DA/Origins/herbalism/herbalism_json/origins_parse_herbalism.py \
    /abs/path/to/herbalism_raw.json \
    /abs/path/to/origins_herbalism_recipes.json \
    /abs/path/to/origins_herbalism_ingredient_recipes.json \
    /abs/path/to/origins_herbalism_tiers.json \
    /abs/path/to/origins_herbalism_unlimited_supply.json
```

## Output Schemas

### `origins_herbalism_recipes.json`
Wide-format recipe table with 4 nullable ingredient columns:

```json
{
  "name": "Elixir of Grounding",
  "result": "Elixir of Grounding",
  "description": "...",
  "item_id": "gen_im_alc_elx_grounding",
  "tier": 3,
  "ingredient1": "Elfroot",
  "quantity1": 1,
  "ingredient2": "Lifestone",
  "quantity2": 1,
  "ingredient3": "Deep Mushroom",
  "quantity3": 2,
  "ingredient4": null,
  "quantity4": null
}
```

### `origins_herbalism_ingredient_recipes.json`
Normalised ingredient → recipe join table (one row per ingredient per recipe):

```json
{"ingredient": "Elfroot", "recipe": "Elixir of Grounding", "quantity": 1}
```

### `origins_herbalism_tiers.json`
Minimum herbalism tier required per recipe:

```json
{"recipe": "Elixir of Grounding", "tier": 3}
```

### `origins_herbalism_unlimited_supply.json`
Unlimited supply vendor/location (normalized — one row per vendor):

```json
{"ingredient": "Elfroot", "vendor": "Jetta", "location": "Denerim Market District", "note": null}
```

- `vendor` is nullable (some entries only name a location)
- `note` is nullable (e.g., "cheapest", "if you kill him, he still appears as a ghost")

## Parsing Logic

- **RecipeTransformer fields** extracted via regex from the `<onlyinclude>` wikitext block
- **Tier** extracted from `|requires=[[Herbalism#Tiers|Herbalism: Rank N]]` → integer N
- **Wiki links** stripped via `[[Target|Display]]` → "Display"
- **Vendor splitting**: multi-vendor entries (e.g., Flask has 3 vendors) split on " and " and ", " outside parentheses; parenthetical notes extracted before splitting
- **Location parsing**: vendor/location separated by ` in `, ` at the `, or ` at ` (shorter prepositions tried first to handle "Ruck in Ruck's Cave")
