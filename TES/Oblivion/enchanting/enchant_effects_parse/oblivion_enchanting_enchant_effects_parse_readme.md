# Purpose and Action

Scrapes the six school tables from `Oblivion:Spell_Effects` on UESP and saves all raw HTML sections as JSON. The Special Spell Effects section (section 7) is intentionally excluded — those effects are cut from the game, unavailable to characters as spells, or disabled from enchanting.

## Script

### `oblivion_scrape_enchant_effects.py`

Fetches sections 1–6 of `Oblivion:Spell_Effects` from the UESP MediaWiki API and writes `oblivion_enchant_effects_raw.json`.

**Output format:**
```json
{
  "page": "Oblivion:Spell_Effects",
  "sections": {
    "1": {"school": "Alteration", "html": "..."},
    "2": {"school": "Conjuration", "html": "..."},
    "3": {"school": "Destruction", "html": "..."},
    "4": {"school": "Illusion",    "html": "..."},
    "5": {"school": "Mysticism",   "html": "..."},
    "6": {"school": "Restoration", "html": "..."}
  }
}
```

The pre-fetched `oblivion_enchant_effects_raw.json` is checked in.

## Usage

```bash
python3 TES/Oblivion/enchanting/enchant_effects_parse/oblivion_scrape_enchant_effects.py
```
