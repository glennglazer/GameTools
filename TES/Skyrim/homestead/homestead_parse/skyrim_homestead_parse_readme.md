# Skyrim Homestead Scraper

**Script**: `skyrim_scrape_homestead.py`

Fetches 7 sections from the `Homestead_(Hearthfire)` wiki page via the Fandom MediaWiki JSON API and saves the raw HTML as a JSON file for downstream parsing.

Sections fetched:
- 6 — Stage 3: Small House construction table
- 24 — Stage 5: Tower wing construction table
- 25 — Stage 5: Room with Outdoor Patio wing construction table
- 26 — Stage 5: Downstairs Room wing construction table
- 35 — Stage 6: Standard exterior totals table
- 36 — Stage 6: Exclusive exteriors table
- 41 — Trivia (steward costs bullet list)

## Output

`homestead_raw.json` — dict keyed by section index string, each value is the raw HTML string for that section.

## Usage

```bash
python3 homestead_parse/skyrim_scrape_homestead.py /abs/path/to/homestead_raw.json
```
