# awakening_trap_making_json

Parses `trap_making_raw.json` (from the Awakening scraper) into five structured JSON files.

## Script

```
awakening_parse_trap_making.py <raw_json>
    <recipes_json> <ingredient_recipes_json> <tiers_json> <supply_json> <effects_json>
```

## Output files

| File | Records | Description |
|------|---------|-------------|
| `awakening_trap_making_recipes.json` | 4 | Wide recipe table: plan name, result trap name, item_id, tier, 4×ingredient+quantity slots |
| `awakening_trap_making_ingredient_recipes.json` | 15 | Ingredient → recipe reverse-lookup with quantity |
| `awakening_trap_making_tiers.json` | 4 | Recipe → minimum trap-making tier (all 4) |
| `awakening_trap_making_unlimited_supply.json` | 0 | Always empty — no Awakening supply vendors |
| `awakening_trap_making_effects.json` | 4 | Trap name → damage_type / power / effect |

## Recipe schema

Same as Origins: `name` (plan name), `result` (trap name), `description`, `item_id`,
`tier`, `ingredient1`–`ingredient4`, `quantity1`–`quantity4`.

All 4 Awakening recipes are Tier 4 with `gxa_` item IDs.

## Ingredient disambiguation

The wiki links some ingredients as `[[Blood Lotus (Origins)]]` (no pipe/alias).
`normalize_ingredient_name()` strips the ` (Origins)` suffix so the stored name
("Blood Lotus") matches the Origins ingredient tables.

## Effects schema

`name TEXT, damage_type TEXT (nullable), power INTEGER (nullable), effect TEXT (nullable)`

| Trap | damage_type | power | effect |
|------|-------------|-------|--------|
| Dispel Trap | NULL | NULL | verbatim effect text |
| Elemental Trap | "cold, electricity, fire, nature, spirit" | 200 | NULL |
| Gravity Trap | NULL | NULL | verbatim effect text |
| Misdirection Cloud Trap | NULL | NULL | verbatim effect text |

Elemental Trap's five-element damage is stored as a **sorted, comma-joined string**
with the **total** power (200 = 5 × 40), matching the Elemental Grenade/Coating pattern
from the Awakening poisons/grenades pipeline.

`<br/>` line breaks in effect text are replaced with spaces before storage.

Unlike the Origins effects table (composite key on `(name, power, damage_type)` to
handle Poisoned Caltrop Trap's two rows), the Awakening table is keyed on `name`
alone — no Awakening trap has dual damage types.
