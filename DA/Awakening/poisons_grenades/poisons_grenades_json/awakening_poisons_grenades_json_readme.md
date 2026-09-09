# awakening_poisons_grenades_json — DAO:A Poison-Making Parser

## Purpose

Parses `poisons_grenades_raw.json` (from the scraper) into five structured JSON files
consumed by the SQL loader.

## Output files

| File | Records | Description |
|------|---------|-------------|
| `awakening_poisons_grenades_recipes.json` | 4 | Wide recipe table: name, **type** ("poison"/"grenade"), result, description, item_id, tier, ingredient1–4, quantity1–4 |
| `awakening_poisons_grenades_ingredient_recipes.json` | ~14 | Ingredient → recipe reverse-lookup |
| `awakening_poisons_grenades_tiers.json` | 4 | Recipe → required tier (all Tier 4) |
| `awakening_poisons_grenades_unlimited_supply.json` | 0 | Empty — no Awakening supply section on wiki |
| `awakening_poisons_grenades_effects.json` | 4 | Crafted item effects (see schema below) |

## Effects schema

`name TEXT` (unique), `damage_type TEXT` (nullable), `power INTEGER` (nullable), `effect TEXT` (nullable)

| Item | damage_type | power | effect |
|------|-------------|-------|--------|
| Elemental Coating | "cold, electricity, fire, nature, spirit" | 10 | NULL |
| Dispel Coating | NULL | NULL | "Dispels magic on hit." |
| Elemental Grenade | "cold, electricity, fire, nature, spirit" | 150 | NULL |
| Dispel Grenade | NULL | NULL | "Dispels magic in affected area." |

Multi-element damage types are stored as a **sorted** comma-joined string.
`power` is the **total** damage across all types (Elemental Coating: 2 × 5 types = 10).

## Grenade classification

The scraper extracts Tier Four grenade result names from the "Tier Four Grenades" table in
section 5 of the Poison-Making wiki page. The parser uses this set to assign `type = "grenade"`
vs `type = "poison"` in the recipes table.

## Usage

```bash
python3 DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_parse_poisons_grenades.py \
    DA/Awakening/poisons_grenades/poisons_grenades_parse/poisons_grenades_raw.json \
    DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_poisons_grenades_recipes.json \
    DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_poisons_grenades_ingredient_recipes.json \
    DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_poisons_grenades_tiers.json \
    DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_poisons_grenades_unlimited_supply.json \
    DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_poisons_grenades_effects.json
```
