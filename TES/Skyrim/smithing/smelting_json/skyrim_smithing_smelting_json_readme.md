# skyrim smelting — smelting_json

Parses `smelting_raw.json` into structured smelting records and produces diff files for the SQL loader.

## Script

`skyrim_parse_smelting_to_json.py`

## Input

`smelting_parse/smelting_raw.json` — scraper output

## Output

`skyrim_smelting.json` — list of 20 smelting records  
`skyrim_smelting.upsert.json` — rows to insert/update  
`skyrim_smelting.delete.json` — rows to remove

## Schema

| Column | Type | Notes |
|--------|------|-------|
| `Source_Name` | TEXT | composite unique key with `Ingot_Name` |
| `Source_Weight` | INTEGER | NULL for Stalhrim |
| `Source_Value` | INTEGER | NULL for Stalhrim |
| `Source_To_Ingot` | INTEGER | NULL for Stalhrim |
| `Ingot_Name` | TEXT | NULL for Stalhrim |
| `Ingots_Produced` | INTEGER | NULL for Stalhrim |
| `Ingot_Weight` | INTEGER | NULL for Stalhrim |
| `Ingot_Value` | INTEGER | NULL for Stalhrim |
| `Note` | TEXT | used for Steel 2-row notes, Stalhrim explanation, CC attribution |

## Special cases

- **Steel Ingot** — split into two rows: (Iron Ore, Steel Ingot) and (Corundum Ore, Steel Ingot), each with a cross-reference Note.
- **Stalhrim** — one NULL row; all numeric fields and Ingot_Name are NULL; Note explains no smelting is needed.
- **CC items** — Amber → Refined Amber and Madness Ore → Madness Ingot; both have a Saints & Seducers attribution Note.

## Usage

```bash
python3 skyrim_parse_smelting_to_json.py [infile [outfile]]
```
