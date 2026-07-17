# Skyrim Main Hall Scraper

**Script**: `skyrim_scrape_main_hall.py`

Fetches 20 sections from the `Main_Hall` wiki page via the Fandom MediaWiki JSON API and saves the raw HTML as a JSON file for downstream parsing.

Sections fetched:
- 5 — Structure (stage-by-stage Main Hall construction table)
- 7–13 — Downstairs furnishing sub-sections (Containers, Furniture, Weapon Racks, Shelves, Magical Workstations, Illumination, Taxidermy)
- 16–21 — Upstairs furnishing sub-sections (Containers, Furniture, Weapon Racks, Shelves, Illumination, Taxidermy)
- 23–28 — Back Room furnishing sub-sections (Containers, Furniture, Weapon Racks, Shelves, Miscellaneous, + section 23 umbrella skipped by parser)

Section 23 is an umbrella heading; the parser uses sections 24–28 directly for the individual Back Room sub-tables.

## Output

`main_hall_raw.json` — dict keyed by section index string, each value is the raw HTML string for that section.

## Usage

```bash
python3 main_hall_parse/skyrim_scrape_main_hall.py /abs/path/to/main_hall_raw.json
```
