# Purpose and Action

This directory holds the script that converts the pipe-delimited raw perks text
file into JSON and writes diff files for the SQL loader.

## Script

### `skyrim_parse_perks_to_json.py`

Reads `skyrim_alchemy_perks_raw.txt` from the sibling `perks_parse/` directory,
parses it into a list of perk dicts, and writes:

- `skyrim_alchemy_perks.json` — full current perk list
- `skyrim_alchemy_perks.upsert.json` — new and changed perks (empty sentinel `{}` if none)
- `skyrim_alchemy_perks.delete.json` — removed perks (empty sentinel `{}` if none)

If the parsed data is identical to the existing JSON file, the script exits
cleanly with a "No changes" message and writes no output.

**JSON record format:**
```json
{
  "name": "Alchemist (1/5)",
  "skill_level": 0,
  "prerequisite": "None",
  "description": "Potions and poisons are 20% stronger."
}
```

The `prerequisite` field is either `"None"` (no prerequisite) or a
comma-separated list of expanded perk names (e.g. `"Concentrated Poison, Experimenter (1/3)"`).

## Usage

```bash
python3 TES/Skyrim/alchemy/perks_json/skyrim_parse_perks_to_json.py
```

Or with explicit paths:

```bash
python3 TES/Skyrim/alchemy/perks_json/skyrim_parse_perks_to_json.py \
  /abs/path/to/skyrim_alchemy_perks_raw.txt \
  /abs/path/to/skyrim_alchemy_perks.json
```
