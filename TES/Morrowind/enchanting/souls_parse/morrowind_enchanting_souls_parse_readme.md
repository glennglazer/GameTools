# Purpose and Action

Scrapes the Morrowind creature souls page from UESP and saves the raw HTML as JSON.

## Script

### `morrowind_scrape_souls.py`

Fetches `Morrowind:Souls` (section 0, full page) from the UESP MediaWiki API and writes `morrowind_souls_raw.json`.

**Output format:**
```json
{"page": "Morrowind:Souls", "section": "0", "html": "..."}
```

The pre-fetched `morrowind_souls_raw.json` is checked in, so this scraper only needs to be re-run if the UESP page changes.

## Usage

```bash
python3 TES/Morrowind/enchanting/souls_parse/morrowind_scrape_souls.py
```
