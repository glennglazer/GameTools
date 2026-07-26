# Purpose and Action

Scrapes the Oblivion sigil stone effects and magnitudes page from UESP and saves the raw HTML as JSON.

## Script

### `oblivion_scrape_sigil_stone.py`

Fetches section 2 (Effects and Magnitudes) of `Oblivion:Sigil_Stone` from the UESP MediaWiki API and writes `oblivion_sigil_stone_raw.json`.

**Output format:**
```json
{
  "page": "Oblivion:Sigil_Stone",
  "section": "2",
  "html": "..."
}
```

The pre-fetched `oblivion_sigil_stone_raw.json` is checked in.

## Usage

```bash
python3 TES/Oblivion/enchanting/sigil_stone_parse/oblivion_scrape_sigil_stone.py
```
