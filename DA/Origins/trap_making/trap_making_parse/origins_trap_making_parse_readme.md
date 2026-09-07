# origins_trap_making_parse — DAO Trap-Making Scraper

## Purpose

Scrapes raw trap-making plan data from the Dragon Age Fandom wiki and saves it as
a single JSON file for the parser to consume.

## Output

`trap_making_raw.json` — one JSON object with three keys:
- `plans`: list of `{title, wikitext}` for each plan page (25 plans)
- `traps_wikitext`: raw wikitext of the "Traps" section (section 3) — contains the
  tier-grouped trap damage/effect table used to build the effects table; Awakening
  traps are in a separate second wikitable that the parser excludes
- `locations_wikitext`: raw wikitext of the "Locations for unlimited supplies" section (section 2)

## Usage

```bash
python3 DA/Origins/trap_making/trap_making_parse/origins_scrape_trap_making.py \
    /abs/path/to/trap_making_raw.json
```

## Source

- **Plan pages**: All pages in `Category:Dragon Age: Origins Trap-Making plans` ending
  with "Plans" (capital P); excludes the "Trap-Making plans" nav page (lowercase p)
  - Fetched via `action=query&list=categorymembers` then `action=parse&prop=wikitext` per page
- **Traps section**: `Trap-Making` page, section 3 — two daotables:
  - DAO Tier 1–4 traps (included)
  - Awakening Tier 4 traps under "Tier Four Traps (Awakening)" header (excluded by parser)
- **Locations section**: `Trap-Making` page, section 2

## Wiki API

Uses the MediaWiki JSON API at `https://dragonage.fandom.com/api.php` with:
- `User-Agent: GameTools-Scraper/1.0`
- 0.3 second rate limiting between plan page requests

## Notes

- All 25 DAO trap plans are in the category; 4 Awakening-only traps (Dispel Trap,
  Elemental Trap, Gravity Trap, Misdirection Cloud Trap) are NOT in the category
  and are excluded from the Traps wikitable by the parser's stop-marker
- The plan page title ends in "Plans" (e.g., "Fire Trap Plans") while the crafted
  trap result name does not (e.g., "Fire Trap"); both are stored in the recipes table
