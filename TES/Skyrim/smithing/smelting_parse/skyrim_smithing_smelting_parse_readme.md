# skyrim smelting — smelting_parse

Scrapes Skyrim smelting recipe and material data from the Elder Scrolls Fandom wiki.

## Script

`skyrim_scrape_smelting.py` — fetches and saves `smelting_raw.json`

## Sources

| Wiki Page | Data |
|-----------|------|
| `Smelting` (section 1) | Recipe table: source → ingot, quantities |
| Individual ore/ingot pages | Weight and base value per material |
| `Amber_(Skyrim_Creation_Club)`, `Madness_Ore`, `Refined_Amber`, `Madness_Ingot` | CC item stats |

## Output

`smelting_raw.json`:
```json
{
  "recipes":        [{"source": "Iron Ore", "source_to_ingot": 1, "ingot": "Iron Ingot", "ingots_produced": 1}, ...],
  "material_stats": {"Iron Ore": {"weight": 1, "value": 2}, ...},
  "ingot_stats":    {"Iron Ingot": {"weight": 1, "value": 7}, ...}
}
```

## Usage

```bash
python3 skyrim_scrape_smelting.py [outfile]
python3 skyrim_scrape_smelting.py --out-dir /abs/path/to/smelting_parse/
```

Requires: `requests`, `beautifulsoup4`
