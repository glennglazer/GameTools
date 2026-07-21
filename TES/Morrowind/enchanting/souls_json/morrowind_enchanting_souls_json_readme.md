# Purpose and Action

Parses the Morrowind creature souls raw HTML into JSON records for `morrowind_enchant_souls`.

## Script

### `morrowind_parse_souls.py`

Reads `morrowind_souls_raw.json` from the sibling `souls_parse/` directory and outputs `morrowind_souls_records.json` containing 148 records.

**Source page structure:** Multiple `wikitable` tables, one per soul gem type (Petty, Greater). Each table has data rows where a `<th>` contains the integer soul strength and `<td>` cells contain lists of creature names. Colspan `<th>` elements (gem type headers) are skipped. Some creatures appear at multiple soul sizes; both entries are stored.

**JSON record format:**
```json
{"name": "Mudcrab", "soul_size": 5}
```

Note: No leveled souls appear on the base Morrowind:Souls page. All entries have fixed integer sizes.

## Usage

```bash
python3 TES/Morrowind/enchanting/souls_json/morrowind_parse_souls.py
```
