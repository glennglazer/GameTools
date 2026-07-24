# skyrim_disenchant_parse

Scraper: fetches `Skyrim:Enchanting_Effects` sections 2 (Apparel) and 3 (Weapons) from the UESP wiki via the MediaWiki API and parses the collapsible Disenchant column into structured JSON records.

## Source

UESP: `https://en.uesp.net/wiki/Skyrim:Enchanting_Effects` — sections 2 and 3.

## Script

`skyrim_scrape_disenchant.py` — produces two raw JSON files:

| Output file | Contents |
|---|---|
| `disenchant_apparel_raw.json` | 35 apparel enchantments, ~200+ records |
| `disenchant_weapons_raw.json` | 19 weapon enchantments, ~100+ records |

Each record: `{"effect": "Fortify Alchemy", "item": "Bracers of Alchemy", "note": "All levels of enchantment"}`.  
`note` is `null` when no context applies.

## Usage

```bash
python3 TES/Skyrim/enchanting/disenchant_parse/skyrim_scrape_disenchant.py
```

Optional flags (defaults to same directory):

```bash
--apparel-out /path/to/disenchant_apparel_raw.json
--weapons-out /path/to/disenchant_weapons_raw.json
```

## Parsing patterns

The Disenchant column contains collapsible `<div>` elements. This scraper handles all patterns found in the data:

| Pattern | Example | Output |
|---|---|---|
| Generic item types + "Includes" sub-note | "All varieties of Bracers/Gauntlets, Helmets, and Necklaces of Alchemy" | One row per item type; note = "All levels of enchantment" |
| Generic item types, no sub-note | "All varieties of Armor, Necklaces, and Rings of Mending" | One row per item type; note = null |
| Multiple italic keywords in one entry | Resist Magic: 6 keyword variants × 3 item types | 18 rows; note = null |
| Named specific item | `Muiri's Ring` | One row; note = null |
| Named item with sub-list note | `Ring of Pure Mixtures` | note = sub-list text |
| Bug sentence | "Due to a bug, the Dwarven Helmet of Eminent Alteration..." | note = "This is due to a bug." |
| CC items | "Elite and Ascendant Necromancer Hoods" | Two rows; note = "Creation Club content" |
| "Most" varieties | "**Most** varieties of Armor and Necklaces of the Knight" | note = "Most varieties; all levels of enchantment" |
| Paragraph context | "A second version of the effect is available from one item:" | paragraph text becomes note for the next item |
| Weapons: "All weapons of X" | "All weapons of Absorption" | item = "All weapons of Absorption"; note = null |
| Weapons: "All varieties of [adj] weapons" | "All varieties of Blessed weapons" | item = "Blessed weapons"; note = null |
| Weapons: named item with dash note | "Drainspell Bow - has unique version of effect" | note = "Has unique version of effect." |

Effect names are taken from the wiki href (e.g. `/wiki/Skyrim:Fortify_Alchemy` → `"Fortify Alchemy"`). The `_(effect)` disambiguation suffix is stripped from names like `Muffle_(effect)`.
