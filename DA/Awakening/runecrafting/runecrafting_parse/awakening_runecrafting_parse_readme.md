# awakening_runecrafting_parse_readme.md

Scraper for Dragon Age: Origins – Awakening runecrafting data.

## Script

`awakening_scrape_runecrafting.py` — fetches wikitext from the Fandom Dragon Age wiki
and writes a single `runecrafting_raw.json` file.

## Pages fetched (108 total)

| Source | Pages | Notes |
|--------|-------|-------|
| Runecrafting (§1 — Tiers) | 1 | Character-level gating for each skill rank |
| Runecrafting (§2 — Tracing Acquisition) | 1 | Non-hybrid and hybrid tables |
| Armor rune pages | 35 | 5 types × 7 levels (Novice…Paragon) |
| Armor hybrid rune pages | 4 | Amplification, Diligence, Endurance, Evasion |
| Weapon rune pages | 63 | 9 types × 7 levels (Novice…Paragon) |
| Weapon hybrid rune pages | 4 | Elemental, Intensifying, Menacing, Momentum |
| Support item pages | 2 | Blank Runestone, Etching Agent |

Sleep: 0.3 s between requests.

## Output

`runecrafting_raw.json` — structure:

```json
{
  "tiers_wikitext": "...",
  "tracing_wikitext": "...",
  "armor_runes":   [{"page": "Novice Barrier Rune", "wikitext": "..."}, ...],
  "weapon_runes":  [{"page": "Novice Flame Rune",   "wikitext": "..."}, ...],
  "support_items": [{"page": "Blank Runestone",      "wikitext": "..."}, ...]
}
```

## Usage

```bash
python3 DA/Awakening/runecrafting/runecrafting_parse/awakening_scrape_runecrafting.py \
    /abs/path/to/runecrafting_raw.json
```

## Notes

- Armor rune type `Barrier` has leveled pages (Novice through Paragon) but **no entry**
  in the tracing acquisition table — it is very rare in-game. Its pages are still scraped
  so the armor_runes table is complete.
- Support item pages use the full-page wikitext fetch (no section number) since the
  `{{ItemTransformer}}` block appears at the top level of each page.
