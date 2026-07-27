# Purpose and Action

Scrapes the Morrowind, Tribunal, and Bloodmoon creature souls pages from UESP and saves the raw HTML as JSON.

## Script

### `morrowind_scrape_souls.py`

Fetches `Morrowind:Souls`, `Tribunal:Souls`, and `Bloodmoon:Souls` (section 0 of each) from the UESP MediaWiki API and writes `morrowind_souls_raw.json`.

**Output format:**
```json
{"pages": [
  {"page": "Morrowind:Souls", "section": "0", "html": "..."},
  {"page": "Tribunal:Souls",  "section": "0", "html": "..."},
  {"page": "Bloodmoon:Souls", "section": "0", "html": "..."}
]}
```

The pre-fetched `morrowind_souls_raw.json` is checked in, so this scraper only needs to be re-run if either UESP page changes.

## Usage

```bash
python3 TES/Morrowind/enchanting/souls_parse/morrowind_scrape_souls.py
```
