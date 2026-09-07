# origins_herbalism_parse — DAO Herbalism Scraper

## Purpose

Scrapes raw herbalism data from the Dragon Age Fandom wiki and saves it as a single JSON file for the parser to consume.

## Output

`herbalism_raw.json` — one JSON object with three keys:
- `recipes`: list of `{title, wikitext}` for each herbalism recipe page (27 recipes)
- `locations_wikitext`: raw wikitext of the "Locations for unlimited supplies" section from the main Herbalism page
- `crafted_items_wikitext`: raw wikitext of the "Dragon Age: Origins" subsection (section 4) of the Herbalism page — the wikitable of all 27 crafted items with their effect descriptions

## Usage

```bash
python3 DA/Origins/herbalism/herbalism_parse/origins_scrape_herbalism.py \
    /abs/path/to/herbalism_raw.json
```

## Source

- **Recipe pages**: All pages in the Fandom wiki category `Category:Dragon_Age:_Origins_Herbalism_recipes`
  - Fetched via `action=query&list=categorymembers` to enumerate pages
  - Wikitext fetched via `action=parse&prop=wikitext`
- **Locations section**: Main `Herbalism` page, section 2 (`action=parse&section=2&prop=wikitext`)
- **Crafted items section**: Main `Herbalism` page, section 4 — "Dragon Age: Origins" subsection under "Herbalism Crafted Items" (`action=parse&section=4&prop=wikitext`)

## Wiki API

Uses the MediaWiki JSON API at `https://dragonage.fandom.com/api.php` with:
- `User-Agent: GameTools-Scraper/1.0`
- 0.3 second rate limiting between recipe page requests
- `urllib.request` only (no third-party HTTP libraries)

## Notes

- The scraper does not require any input arguments beyond the output path.
- Individual recipe pages follow the `RecipeTransformer` template with an `<onlyinclude>` block.
- The parser (`herbalism_json/`) handles all wikitext parsing; the scraper stores raw wikitext unchanged.
