# origins_trap_making_json — DAO Trap-Making Parser

## Purpose

Parses raw trap-making wikitext (`trap_making_raw.json`) into five structured JSON
files for the SQL loader.

## Inputs / Outputs

| Argument | File | Description |
|----------|------|-------------|
| `raw_json` | `trap_making_raw.json` | Output of the scraper |
| `recipes_json` | `origins_trap_making_recipes.json` | Wide recipe table (25 rows) |
| `ingredient_recipes_json` | `origins_trap_making_ingredient_recipes.json` | Ingredient → recipe join table (65 rows) |
| `tiers_json` | `origins_trap_making_tiers.json` | Recipe → required tier (25 rows) |
| `supply_json` | `origins_trap_making_unlimited_supply.json` | Unlimited supply vendor/location records (11 rows) |
| `effects_json` | `origins_trap_making_effects.json` | Trap name → damage_type/power/effect (26 rows; Poisoned Caltrop Trap has 2 rows) |

## Usage

```bash
python3 DA/Origins/trap_making/trap_making_json/origins_parse_trap_making.py \
    /abs/path/to/trap_making_raw.json \
    /abs/path/to/origins_trap_making_recipes.json \
    /abs/path/to/origins_trap_making_ingredient_recipes.json \
    /abs/path/to/origins_trap_making_tiers.json \
    /abs/path/to/origins_trap_making_unlimited_supply.json \
    /abs/path/to/origins_trap_making_effects.json
```

## Output Schemas

### `origins_trap_making_recipes.json`
Wide-format recipe table with `result` (trap name) separate from `name` (plan name):

```json
{
  "name": "Fire Trap Plans",
  "result": "Fire Trap",
  "description": "Directions for building a fire trap.",
  "item_id": "gen_im_cft_trp_208",
  "tier": 3,
  "ingredient1": "Fire Crystal", "quantity1": 1,
  "ingredient2": "Corrupter Agent", "quantity2": 1,
  "ingredient3": "Trap Trigger", "quantity3": 1,
  "ingredient4": null, "quantity4": null
}
```

### `origins_trap_making_ingredient_recipes.json`
Normalised ingredient → recipe join table:

```json
{"ingredient": "Fire Crystal", "recipe": "Fire Trap Plans", "quantity": 1}
```

### `origins_trap_making_tiers.json`
Minimum tier required per recipe:

```json
{"recipe": "Fire Trap Plans", "tier": 3}
```

### `origins_trap_making_unlimited_supply.json`
Unlimited supply records (one row per vendor). Bare vendor names with no location
preposition (Bodahn Feddic, Ruck) produce rows with `location: null`:

```json
{"ingredient": "Concentrator Agent", "vendor": "Bartender", "location": "Gnawed Noble Tavern", "note": null}
{"ingredient": "Concentrator Agent", "vendor": "Bodahn Feddic", "location": null, "note": null}
{"ingredient": "Corrupter Agent", "vendor": "Alimar", "location": "Dust Town", "note": "cheaper"}
```

Lines with two ingredients separated by "and" (e.g., "Deathroot and Toxin Extract")
yield one row per ingredient, both with the same vendor and location.

### `origins_trap_making_effects.json`
Trap effects — nullable damage type/power and nullable side effect description:

```json
{"name": "Small Caltrop Trap", "damage_type": "physical", "power": 8, "effect": "-40% movement speed to creatures in the area"}
{"name": "Fire Trap", "damage_type": "fire", "power": 100, "effect": null}
{"name": "Spring Trap", "damage_type": null, "power": null, "effect": "Trap knocks down the target..."}
{"name": "Poisoned Caltrop Trap", "damage_type": "physical", "power": 8, "effect": "-40% movement speed..."}
{"name": "Poisoned Caltrop Trap", "damage_type": "nature", "power": 8, "effect": "-40% movement speed..."}
```

`damage_type` values: `physical`, `nature`, `fire`, `cold`, `electricity`, `spirit`.
Dual-damage traps (Poisoned Caltrop Trap) produce **two records** — one per damage type.
`power` is the per-hit numeric value; periodic/directional context is in the wiki's
"Damage per hit" column text. Awakening-only traps are excluded via stop-marker truncation.
Records are sorted by `name`; within the same name, order follows parse order (physical first, nature second).

## Parsing Notes

- **Tier**: extracted from `|requires=[[Trap-Making#Tiers|Trap-Making: Rank N]]`
- **Dual damage** (Poisoned Caltrop Trap): `_DUAL_RE` matched before `_SIMPLE_RE`
  to avoid partial match; produces **two records** — `("physical", 8)` and `("nature", 8)` — 
  so the table can be keyed on `(name, power, damage_type)`
- **Negative power** (Acidic Grease Trap: "-4 nature damage"): stored as-is (-4)
- **Bare vendor names** (Bodahn Feddic, Ruck): treated as vendor with `location=null`
- **Dual ingredients**: "[[Deathroot (Origins)|Deathroot]] and [[Toxin Extract]]" line
  yields one supply row each, both sharing the same vendor/location
