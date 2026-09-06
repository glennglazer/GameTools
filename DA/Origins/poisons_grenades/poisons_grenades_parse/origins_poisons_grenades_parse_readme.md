# origins_poisons_grenades_parse — DAO Poisons & Grenades Scraper

## Purpose

Scrapes raw poison-making and grenade recipe data from the Dragon Age Fandom wiki
and saves it as a single JSON file for the parser to consume.

## Output

`poisons_grenades_raw.json` — one JSON object with three keys:
- `recipes`: list of `{title, wikitext}` for each recipe page (25 recipes)
- `grenade_results`: list of Tier Two grenade result names extracted from the Grenades section (used by parser to assign `type`)
- `locations_wikitext`: raw wikitext of the "Locations for unlimited supplies" section

## Usage

```bash
python3 DA/Origins/poisons_grenades/poisons_grenades_parse/origins_scrape_poisons_grenades.py \
    /abs/path/to/poisons_grenades_raw.json
```

## Source

- **Recipe pages**: All pages in `Category:Dragon Age: Origins Poison-Making recipes` that end with "Recipe" (excludes the "Poison-Making recipes" navigation page)
  - Fetched via `action=query&list=categorymembers` then `action=parse&prop=wikitext` per page
- **Grenades section**: `Poison-Making` page, section 4 — "Tier Two" table rows identify which results are grenades (Tier Four are Awakening-only and excluded)
- **Locations section**: `Poison-Making` page, section 2 (`action=parse&section=2&prop=wikitext`)

## Wiki API

Uses the MediaWiki JSON API at `https://dragonage.fandom.com/api.php` with:
- `User-Agent: GameTools-Scraper/1.0`
- 0.3 second rate limiting between recipe page requests

## Notes

- Poisons and grenades share the `Dragon Age: Origins Poison-Making recipes` wiki category
- The 5 Tier Two grenades are: Acid Flask, Fire Bomb, Freeze Bomb, Shock Bomb, Soulrot Bomb
- All 5 grenades require Poison-Making Rank 2; Tier Four grenades (Awakening DLC) are not scraped here
- Type classification (poison vs grenade) is done by the parser using `grenade_results`
