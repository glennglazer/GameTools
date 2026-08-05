# skyrim_homestead_wings_parse

Scrapes the nine wing room furnishing pages from the Fandom Elder Scrolls wiki
and saves the combined result as `wings_raw.json`.

## Source

Fandom Elder Scrolls wiki — Hearthfire wing room pages:

| Source key | Page | Wing | Sections |
|---|---|---|---|
| `enchanters_tower` | `Enchanter%27s_Tower_%28Skyrim%29` | West Wing | 4–9 |
| `bedrooms` | `Bedrooms` | West Wing | 4–9 |
| `greenhouse` | `Greenhouse` | West Wing | 5–9 (section 4 is a heading only) |
| `trophy_room` | `Trophy_Room` | North Wing | 4–8 |
| `storage_room` | `Storage_Room` | North Wing | 4–8 |
| `alchemy_laboratory` | `Alchemy_Laboratory_%28Skyrim%29` | North Wing | 4–9 |
| `library` | `Library` | East Wing | 4–8 |
| `armory` | `Armory_%28Hearthfire%29` | East Wing | 4–9 |
| `kitchen` | `Kitchen` | East Wing | 4–7 |

## Output: `wings_raw.json`

```json
{
  "source": "Fandom Elder Scrolls wiki",
  "fetched": "YYYY-MM-DD",
  "rooms": {
    "enchanters_tower": {
      "page": "Enchanter%27s_Tower_%28Skyrim%29",
      "sections": [{"index": "4", "number": "3.1", "title": "Containers", "html": "..."}]
    },
    ...
  }
}
```

## Usage

```bash
python3 TES/Skyrim/homestead/wings_parse/skyrim_scrape_homestead_wings.py \
  /abs/path/to/wings_raw.json
```

The output is consumed by `build_json/skyrim_parse_homestead_build.py`.
