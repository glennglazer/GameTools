# Purpose and Action

This directory holds the scraper that fetches Creation Club content pages from
the UESP wiki and saves raw HTML sections as JSON files for downstream parsers.

## Script

### `skyrim_scrape_cc.py`

Fetches 21 UESP CC pages via the MediaWiki JSON API and writes one
`<page>_raw.json` file per page.

**Pages scraped:**

| Group | Pages |
|---|---|
| Armor | Chitin, Silver, Orcish, Animal Hides, Iron, Dwarven, Dragon Items, Steel, Elven, Ebony, Daedric, Stalhrim, Vigil Armor |
| Armor + Weapons | Amber, Dark, Madness Ore, Golden |
| Ammo | Rare Curios Items, Arcane Archer Pack Items |
| Homestead | Main Hall (Aquarium section) |

**Output format** (`<key>_raw.json`):
```json
{
  "page": "Skyrim:Chitin",
  "sections": {
    "4": {"title": "Chitin Armor", "html": "<div>..."},
    "7": {"title": "Chitin Gauntlets", "html": "<div>..."}
  }
}
```

The `section` keys match those used in `PAGE_CONFIG` and are passed directly to
the downstream parsers.

## Usage

```bash
python3 TES/Skyrim/creation_club/cc_parse/skyrim_scrape_cc.py \
  /abs/path/to/TES/Skyrim/creation_club/cc_parse
```

Scrape a single page only (useful for incremental re-fetches):

```bash
python3 TES/Skyrim/creation_club/cc_parse/skyrim_scrape_cc.py \
  /abs/path/to/TES/Skyrim/creation_club/cc_parse \
  --page Skyrim:Amber
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--delay` | `0.5` | Seconds between API calls |
| `--page` | (all) | Fetch only this UESP page title |

Pre-fetched raw JSON files are already checked in, so this scraper only needs
to be re-run when CC content changes or new pages are added.
