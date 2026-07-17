# Skyrim Cellar Scraper

**Script**: `skyrim_scrape_cellar.py`

Fetches 17 sections from the `Cellar` wiki page via the Fandom MediaWiki JSON API and saves the raw HTML as a JSON file for downstream parsing.

Sections fetched:
- 3–10 — Cellar furnishing tables (Containers, Furniture, Weapon Racks, Shelves, Blacksmith Items, Taxidermy, Miscellaneous, Divine Shrines base table)
- 12–20 — Individual shrine sections (Akatosh, Arkay, Dibella, Julianos, Kynareth, Mara, Stendarr, Talos, Zenithar)

Section 11 ("Per Shrine") contains no buildable data and is skipped. Section 21 ("All Shrines") is a totals summary and is skipped.

The individual shrine sections (12–20) use `<ul><li>N x Item</li>` bullet lists rather than wikitables; these are parsed by `parse_shrine_bullet` in the build parser.

## Output

`cellar_raw.json` — dict keyed by section index string, each value is the raw HTML string for that section.

## Usage

```bash
python3 cellar_parse/skyrim_scrape_cellar.py /abs/path/to/cellar_raw.json
```
