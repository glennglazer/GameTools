# awakening_trap_making_parse

Scrapes DAO:A Trap-Making plan data from the Dragon Age Fandom wiki.

## Script

`awakening_scrape_trap_making.py <output_raw_json>`

## Source

- **Category**: `Category:Dragon Age: Origins - Awakening Trap-Making plans`
  — yields 4 plan pages ending in "Plans" (capital P)
- **Plan pages**: full wikitext via `action=parse&prop=wikitext` (RecipeTransformer blocks)
- **Traps section**: section 3 of the `Trap-Making` page — contains both the DAO
  Tier 1–4 traps daotable and the Awakening-only "Tier Four Traps (Awakening)" daotable

## Output

`trap_making_raw.json` — two keys:
```json
{
  "plans": [{"title": "...", "wikitext": "..."}],
  "traps_wikitext": "..."
}
```

No `locations_wikitext` key — Awakening has no unlimited supply vendors for trap
ingredients (supply table is always empty).

## Pages scraped (4 plans)

| Title | Result |
|-------|--------|
| Dispel Trap Plans | Dispel Trap |
| Elemental Trap Plans | Elemental Trap |
| Gravity Trap Plans | Gravity Trap |
| Misdirection Cloud Trap Plans | Misdirection Cloud Trap |

## Notes

- Sleeps 0.3 s between plan-page fetches to be polite to the wiki API.
- Missing plan pages are logged as warnings and skipped (pipeline continues).
