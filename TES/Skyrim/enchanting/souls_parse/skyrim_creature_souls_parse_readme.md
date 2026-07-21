# Purpose and Action

This directory holds two scrapers: the original soul gem types scraper (for `skyrim_enchant_soulgems`) and a newer creature souls scraper (for `skyrim_enchant_souls`).

## Scripts

### `skyrim_scrape_souls.py` (original)

Fetches `Soul_Gem_(Skyrim)` and `Races_(Skyrim)` from the Fandom wiki and writes:
- `skyrim_soul_gem_types_raw.txt` — gem types (weight, value, capacity, trappable souls)
- `skyrim_creature_souls_raw.txt` — legacy pipe-delimited creature souls (superseded)

### `skyrim_scrape_creature_souls.py` (current)

Fetches `Skyrim:Souls` (full page) from the UESP MediaWiki API and writes `skyrim_creature_souls_uesp_raw.json`. This is the source used by the current `creature_souls_json/` parser.

**Output format:**
```json
{"page": "Skyrim:Souls", "html": "..."}
```

The pre-fetched `skyrim_creature_souls_uesp_raw.json` is checked in.

## Usage

```bash
python3 TES/Skyrim/enchanting/souls_parse/skyrim_scrape_creature_souls.py
```
