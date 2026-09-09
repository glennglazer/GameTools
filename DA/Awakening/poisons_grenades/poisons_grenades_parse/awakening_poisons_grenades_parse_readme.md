# awakening_poisons_grenades_parse — DAO:A Poison-Making Scraper

## Purpose

Scrapes DAO:A Poison-Making recipe pages and effects data from the Fandom wiki into a single
`poisons_grenades_raw.json` file for downstream parsing.

## Source pages

| Page | Purpose |
|------|---------|
| `Category:Dragon Age: Origins - Awakening Poison-Making recipes` | Lists the 4 Awakening recipe pages |
| Each recipe page (e.g. `Dispel Grenade Recipe`) | `{{RecipeTransformer}}` wikitext |
| `Poison-Making` — section 5 ("Dragon Age: Origins - Awakening") | Effects tables + grenade names |

## Output

`poisons_grenades_raw.json` with keys:

| Key | Content |
|-----|---------|
| `recipes` | List of `{title, wikitext}` dicts (4 recipes) |
| `grenade_results` | List of in-game grenade result names extracted from "Tier Four Grenades" table |
| `awakening_effects_wikitext` | Raw wikitext of section 5 (contains Tier Four Poisons + Tier Four Grenades tables) |

There is no Awakening supply section on the wiki; supply is always empty (`[]`).

## Usage

```bash
python3 DA/Awakening/poisons_grenades/poisons_grenades_parse/awakening_scrape_poisons_grenades.py \
    DA/Awakening/poisons_grenades/poisons_grenades_parse/poisons_grenades_raw.json
```
