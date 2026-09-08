# awakening_herbalism_parse — DAO:A Herbalism Scraper

## Purpose

Scrapes DAO:A herbalism recipe wikitext and crafted-item effects from the Fandom wiki,
saving everything as a single raw JSON file for the parser to consume.

## Source

- **Recipes**: `Category:Dragon Age: Origins - Awakening Herbalism recipes` (10 pages;
  "Herbalism recipes" navigation page excluded)
- **Crafted-item effects**: section 5 ("Dragon Age: Origins - Awakening") of the
  `Herbalism` wiki page
- **Locations**: no Awakening-specific supply section exists on the wiki;
  `locations_wikitext` is saved as `""` and the supply table will have 0 rows

All 10 Awakening herbalism recipes are Tier 4. They use DAO ingredients (Elfroot,
Deep Mushroom, Lyrium Dust, Flask, Distillation Agent, Concentrator Agent).

## Usage

```bash
python3 DA/Awakening/herbalism/herbalism_parse/awakening_scrape_herbalism.py \
    /abs/path/to/herbalism_raw.json
```

## Output: `herbalism_raw.json`

```json
{
  "recipes": [
    {"title": "Master Health Poultice Recipe", "wikitext": "..."},
    ...
  ],
  "crafted_items_wikitext": "=== Dragon Age: Origins - Awakening ===\n...",
  "locations_wikitext": ""
}
```

## Pipeline position

Part of the DAO:A herbalism pipeline, chained after the DAO herbalism pipeline:

1. DAO herbalism pipeline runs (origins scrape → parse → SQL into DAO DB)
2. DAO herbalism SQL loader runs against the DAO:A DB (syncs Origins tables)
3. **This scraper** runs (DAO:A recipes and effects from wiki)
4. `awakening_parse_herbalism.py` parses raw JSON → 5 structured JSON files
5. `create_or_update_awakening_herbalism.py` loads JSON → `DA/Awakening/database/gametools.sqlite3`
