# Skyrim Soul Gem Scraper

**Script**: `skyrim_scrape_souls.py`

Fetches soul gem data from the Elder Scrolls Wiki via the Fandom MediaWiki JSON API (full Soul_Gem_(Skyrim) page) and the playable races from Races_(Skyrim) section 1.

## Outputs

| File | Format | Description |
|------|--------|-------------|
| `skyrim_soul_gem_types_raw.txt` | `name\|weight\|value\|capacity\|trappable_souls` | One row per soul gem type |
| `skyrim_creature_souls_raw.txt` | `creature\|soul_size` | One row per creature, sized petty/lesser/common/greater/grand/black |

## Usage

```bash
python3 souls_parse/skyrim_scrape_souls.py [--out-dir /path/to/output]
```

Defaults to writing raw files in the script's own directory.
