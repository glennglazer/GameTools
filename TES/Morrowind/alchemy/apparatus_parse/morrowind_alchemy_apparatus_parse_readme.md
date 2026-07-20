# Purpose and Action

This directory holds the scraper that fetches the Morrowind alchemy apparatus
page from the UESP wiki and saves the raw HTML as JSON for the downstream parser.

## Script

### `morrowind_scrape_apparatus.py`

Fetches `Morrowind:Alchemy_Apparatus` section 0 from the UESP MediaWiki API
and writes `morrowind_apparatus_raw.json`.

**Output format:**
```json
{
  "page": "Morrowind:Alchemy_Apparatus",
  "section": "0",
  "html": "<div class=\"mw-parser-output\">..."
}
```

The pre-fetched `morrowind_apparatus_raw.json` is checked in, so this scraper
only needs to be re-run if the UESP page changes.

## Usage

```bash
python3 TES/Morrowind/alchemy/apparatus_parse/morrowind_scrape_apparatus.py
```

Or with an explicit output path:

```bash
python3 TES/Morrowind/alchemy/apparatus_parse/morrowind_scrape_apparatus.py \
  /abs/path/to/morrowind_apparatus_raw.json
```
