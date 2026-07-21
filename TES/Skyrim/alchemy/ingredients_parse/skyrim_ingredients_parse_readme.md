# Skyrim Alchemy — Ingredients Parse

Raw data and scraper scripts for the Skyrim alchemy ingredients pipeline.

## Scripts

- `skyrim_scrape_wiki.py` — fetches the Skyrim Alchemy ingredient tables from the Fandom Elder
  Scrolls wiki (via the MediaWiki `action=parse` API) and writes
  `skyrim_all_ingredients_raw.txt`, a pipe-delimited text file with one 10-line block per ingredient.

- `skyrim_scrape_alchemy_effects.py` — fetches the Effect List section of the UESP
  `Skyrim:Alchemy_Effects` page and writes `skyrim_effects_raw.json`, a dict mapping each of
  the 60 alchemy effect names to `{base_cost, base_mag, base_dur}`. This file is consumed by
  the parser (`ingredients_json/skyrim_parse_wiki_to_json.py`) to populate the `base_magnitude`
  column in `skyrim_alchemy_effects`.

## Output files

- `skyrim_all_ingredients_raw.txt` — pipe-delimited ingredient data (produced by `skyrim_scrape_wiki.py`)
- `skyrim_effects_raw.json` — per-effect metadata (produced by `skyrim_scrape_alchemy_effects.py`)

## Running

```bash
# Scrape ingredients (Fandom wiki)
python3 skyrim_scrape_wiki.py --out-dir /abs/path/to/this/dir

# Scrape effect metadata (UESP wiki) — run before the JSON parser
python3 skyrim_scrape_alchemy_effects.py /abs/path/to/skyrim_effects_raw.json
```

Both scripts use the UESP/Fandom MediaWiki `action=parse` JSON API.
