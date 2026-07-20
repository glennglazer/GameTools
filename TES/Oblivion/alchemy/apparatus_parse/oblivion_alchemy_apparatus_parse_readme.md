# Purpose and Action

This directory holds the scraper that fetches the Oblivion alchemy equipment
section from the UESP wiki and saves the raw HTML as JSON for the downstream parser.

## Script

### `oblivion_scrape_apparatus.py`

Fetches `Oblivion:Miscellaneous_Items` section 2 (Alchemy Equipment) from the
UESP MediaWiki API and writes `oblivion_apparatus_raw.json`.

**Output format:**
```json
{
  "page": "Oblivion:Miscellaneous_Items",
  "section": "2",
  "html": "<div class=\"mw-parser-output\">..."
}
```

The pre-fetched `oblivion_apparatus_raw.json` is checked in, so this scraper
only needs to be re-run if the UESP page changes.

## Usage

```bash
python3 TES/Oblivion/alchemy/apparatus_parse/oblivion_scrape_apparatus.py
```

Or with an explicit output path:

```bash
python3 TES/Oblivion/alchemy/apparatus_parse/oblivion_scrape_apparatus.py \
  /abs/path/to/oblivion_apparatus_raw.json
```
