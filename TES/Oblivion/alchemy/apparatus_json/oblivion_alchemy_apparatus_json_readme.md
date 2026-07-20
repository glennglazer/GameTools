# Purpose and Action

This directory holds the parser that converts the Oblivion apparatus raw HTML
into JSON records for `oblivion_alchemy_apparatus`.

## Script

### `oblivion_parse_apparatus.py`

Reads `oblivion_apparatus_raw.json` from the sibling `apparatus_parse/`
directory and outputs `oblivion_apparatus_records.json` containing 21 records.

**Items parsed:** 4 apparatus types (Alembic, Calcinator, Mortar & Pestle,
Retort) × 5 grades (Novice → Master), plus one additional tutorial Mortar &
Pestle with its own form ID (obtained during the tutorial quest).

**Table structure:** Each item spans multiple rows via rowspan on the image,
name, and notes cells. First row of each item has 8 `td` cells; subsequent
grade rows have 5 cells. The second wikitable in the section (a level
progression chart) is ignored — only the first table is parsed.

**JSON record format:**
```json
{
  "name": "Alembic",
  "grade": "Novice",
  "id": "00010604",
  "weight": 7.0,
  "cost": 50,
  "strength": 0.1
}
```

Note: `cost` (not `value`) is used to match the Oblivion wiki's column header
and to distinguish from the Morrowind apparatus schema.  The tutorial Mortar &
Pestle row is in italic in the wiki; the parser strips the italic tags and
includes it with `grade = "Novice"` alongside the regular Novice.

## Usage

```bash
python3 TES/Oblivion/alchemy/apparatus_json/oblivion_parse_apparatus.py
```

Or with explicit paths:

```bash
python3 TES/Oblivion/alchemy/apparatus_json/oblivion_parse_apparatus.py \
  /abs/path/to/oblivion_apparatus_raw.json \
  /abs/path/to/oblivion_apparatus_records.json
```
