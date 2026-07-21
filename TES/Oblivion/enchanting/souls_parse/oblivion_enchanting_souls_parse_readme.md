# Purpose and Action

Scrapes the Oblivion creature souls page from UESP and saves the raw HTML as JSON.

## Script

### `oblivion_scrape_souls.py`

Fetches two sections of `Oblivion:Souls` from the UESP MediaWiki API and writes `oblivion_souls_raw.json`:

- **Section 1** (Souls Alphabetically): four wikitables covering standard, location-specific, and quest creatures
- **Section 3** (Soul Strengths): the name-to-integer mapping (Petty=150 … Black=1600)

**Output format:**
```json
{
  "page": "Oblivion:Souls",
  "section_creatures": "1",
  "section_mapping": "3",
  "creatures_html": "...",
  "mapping_html": "..."
}
```

The pre-fetched `oblivion_souls_raw.json` is checked in.

## Usage

```bash
python3 TES/Oblivion/enchanting/souls_parse/oblivion_scrape_souls.py
```
