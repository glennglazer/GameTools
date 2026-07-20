# Purpose and Action

This directory holds the parser that converts the Morrowind apparatus raw HTML
into JSON records for `morrowind_alchemy_apparatus`.

## Script

### `morrowind_parse_apparatus.py`

Reads `morrowind_apparatus_raw.json` from the sibling `apparatus_parse/`
directory and outputs `morrowind_apparatus_records.json` containing 22 records.

**Items parsed:** 5 quality grades × 4 apparatus types (Mortar and Pestle,
Alembic, Calcinator, Retort) plus 2 Skooma Pipes, which are functional
Mortar-and-Pestle substitutes and appear in the same wiki table.

**Table structure:** Each data row has exactly 8 `td` cells. Rows with fewer
cells are collapsible location rows and are skipped. Any CSS class on the row
is accepted — the table uses different classes for different quality grades
(`OBMagicRes`, `EffectPos`, `EffectMix`, `EffectNeg`, `MWMagicMys`, `RaceErr`).

**JSON record format:**
```json
{
  "id": "apparatus_a_mortar_01",
  "name": "Apprentice's Mortar and Pestle",
  "weight": 5.0,
  "value": 100,
  "quality": 0.5
}
```

Note: the Secret Master items are named `SecretMaster's ...` (no space) and the
Secret Master's Mortar is named `SecretMaster's Mortar and Pestl` (no final 'e')
— both are intentional in-game spellings preserved here as-is.

## Usage

```bash
python3 TES/Morrowind/alchemy/apparatus_json/morrowind_parse_apparatus.py
```

Or with explicit paths:

```bash
python3 TES/Morrowind/alchemy/apparatus_json/morrowind_parse_apparatus.py \
  /abs/path/to/morrowind_apparatus_raw.json \
  /abs/path/to/morrowind_apparatus_records.json
```
