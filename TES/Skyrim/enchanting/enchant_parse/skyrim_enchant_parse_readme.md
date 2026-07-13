# Skyrim Enchanting Scraper

**Script**: `skyrim_scrape_enchanting.py`

Fetches enchanting perks and enchantment data from the Elder Scrolls Wiki via the Fandom MediaWiki JSON API. Makes two HTTP calls: Enchanting_(Skyrim) section 10 (perks) and section 13 (weapon + apparel enchantments).

Multi-rank perks (Enchanter 5-rank, Augmented Flames/Frost/Shock 2-rank each) are expanded into individual rows with prerequisite chains.

## Outputs

| File | Format | Description |
|------|--------|-------------|
| `skyrim_enchant_perks_raw.txt` | `name\|skill_level\|prerequisite\|description` | All enchanting perks, multi-rank expanded |
| `skyrim_enchant_effects_raw.txt` | `name\|school` | Weapon enchantment effects and their magic school |
| `skyrim_enchant_apparel_raw.txt` | `enchantment\|head\|chest\|hands\|feet\|shield\|amulet\|ring` | Apparel enchantments with True/False slot availability |

## Usage

```bash
python3 enchant_parse/skyrim_scrape_enchanting.py [--out-dir /path/to/output]
```
