# origins_herbalism_json — DAO Herbalism Parser

## Purpose

Parses raw herbalism wikitext (`herbalism_raw.json`) into five structured JSON files ready for the SQL loader.

## Inputs / Outputs

| Argument | File | Description |
|----------|------|-------------|
| `raw_json` | `herbalism_raw.json` | Output of the scraper |
| `recipes_json` | `origins_herbalism_recipes.json` | Wide recipe table (27 rows) |
| `ingredient_recipes_json` | `origins_herbalism_ingredient_recipes.json` | Ingredient → recipe join table |
| `tiers_json` | `origins_herbalism_tiers.json` | Recipe → required tier (1–4) |
| `supply_json` | `origins_herbalism_unlimited_supply.json` | Unlimited supply vendor/location records |
| `effects_json` | `origins_herbalism_potion_effects.json` | Crafted item type/power/verbatim effects (27 rows) |

## Usage

```bash
python3 DA/Origins/herbalism/herbalism_json/origins_parse_herbalism.py \
    /abs/path/to/herbalism_raw.json \
    /abs/path/to/origins_herbalism_recipes.json \
    /abs/path/to/origins_herbalism_ingredient_recipes.json \
    /abs/path/to/origins_herbalism_tiers.json \
    /abs/path/to/origins_herbalism_unlimited_supply.json \
    /abs/path/to/origins_herbalism_potion_effects.json
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

### `origins_herbalism_potion_effects.json`
Crafted item type/power classification with verbatim effects:

```json
{"name": "Lesser Injury Kit", "type": "Injury", "power": 10, "effects": "Instantly regains 10 health and is cured of a single injury"}
{"name": "Lesser Ice Salve", "type": "Cold Resistance", "power": 30, "effects": "+30% cold resistance for 180 seconds"}
{"name": "Incense of Awareness", "type": null, "power": null, "effects": "+10 Defense for 120 seconds, -10 Mental Resistance for 120 seconds"}
```

- `type` values: Health, Mana, Mabari, Injury, Cold Resistance, Nature Resistance, Fire Resistance, Spirit Resistance, Electricity Resistance — or `null` for buffs
- `power` values: formula-based power at SP=0 for Health (50/100/150/200) and Mana (50/100/150/200); injury kit health restored (10/20/40); resistance percentage (30/60); `null` for Mabari and buffs
- `effects`: verbatim wiki description string

## Parsing Logic

- **RecipeTransformer fields** extracted via regex from the `<onlyinclude>` wikitext block
- **Tier** extracted from `|requires=[[Herbalism#Tiers|Herbalism: Rank N]]` → integer N
- **Wiki links** stripped via `[[Target|Display]]` → "Display"
- **Vendor splitting**: multi-vendor entries (e.g., Flask has 3 vendors) split on " and " and ", " outside parentheses; parenthetical notes extracted before splitting
- **Location parsing**: vendor/location separated by ` in `, ` at the `, or ` at ` (shorter prepositions tried first to handle "Ruck in Ruck's Cave")
- **Effect classification** (`classify_effect`): checks description against ordered regex patterns — mabari hound → Mabari (NULL power); "restores … health" → Health (power = base × multiplier at SP=0, e.g., "(50+SP)*3" → 150); "restores … mana" → Mana (power = base constant at SP=0, e.g., "(100+0.5*SP)" → 100); "regains N health" + "injur" → Injury (power=N); "+N% TYPE resistance" → TYPE Resistance; electricity handled with two surface forms ("electricity damage by N%" and "+N% electrical resistance"); no match → buff (NULL/NULL)
- **Crafted items wikitext**: `|[[Name]] || description` row format; header rows starting with `!` are skipped
