# skyrim_homestead_entryway_parse

Scrapes the Main Hall: Entryway furnishing table from the UESP wiki.

The Fandom wiki does not cover this optional step (converting the Small House
into a pass-through Entryway after the Main Hall is built). The UESP wiki has
the data at `Skyrim:Main_Hall` section 2.

## Source

UESP wiki — `https://en.uesp.net/w/api.php?action=parse&page=Skyrim:Main_Hall&section=2`

The table format is `Type | Options | Materials | Notes` — the same "type-options
table" format used by the CC Aquarium. The parser handles it via `parse_type_options_table()`.

## Output: `entryway_raw.json`

```json
{
  "page": "Skyrim:Main_Hall",
  "source": "UESP",
  "fetched": "YYYY-MM-DD",
  "sections": [
    {"index": "2", "title": "Main Hall: Entryway", "html": "..."}
  ]
}
```

## Usage

```bash
python3 TES/Skyrim/homestead/entryway_parse/skyrim_scrape_homestead_entryway.py \
  /abs/path/to/entryway_raw.json
```

The output is consumed by `build_json/skyrim_parse_homestead_build.py`.
