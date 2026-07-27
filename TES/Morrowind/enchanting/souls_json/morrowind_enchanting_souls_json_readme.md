# Purpose and Action

Parses the Morrowind, Tribunal, and Bloodmoon creature souls raw HTML into JSON records for `morrowind_enchant_souls`.

## Script

### `morrowind_parse_souls.py`

Reads `morrowind_souls_raw.json` (multi-page format) from the sibling `souls_parse/` directory and outputs `morrowind_souls_records.json` containing 215 records (148 Morrowind + 25 Tribunal-exclusive + 42 Bloodmoon-exclusive, after deduplication).

**Source page structure:** Multiple `wikitable` tables, one per soul gem type. Each table has data rows where a `<th>` contains the integer soul strength and `<td>` cells contain lists of creature names. Colspan `<th>` elements (gem type headers) are skipped. Some creatures appear at multiple soul sizes; both entries are stored. Footnote reference markers (`[1]`, `[2]`) are stripped from creature names.

**JSON record format:**
```json
{"name": "Mudcrab", "soul_size": 5}
```

**Deduplication:** Some creatures (e.g. Rat, Scrib at size 10) appear in multiple source pages. The `parse()` function deduplicates across all three pages by `(name, soul_size)`. All entries have fixed integer sizes.

## Usage

```bash
python3 TES/Morrowind/enchanting/souls_json/morrowind_parse_souls.py
```
