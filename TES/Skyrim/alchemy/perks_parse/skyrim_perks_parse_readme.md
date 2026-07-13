# Purpose and Action

This directory holds the scraper that fetches Skyrim alchemy perk data from the
Fandom wiki and writes a pipe-delimited raw text file for the JSON parser.

## Script

### `skyrim_scrape_alchemy_perks.py`

Fetches section 11 (Perks) of the `Alchemy_(Skyrim)` page via the Fandom
MediaWiki `action=parse` API, parses the HTML table, expands multi-rank perks,
and writes `skyrim_alchemy_perks_raw.txt` to the script's own directory (or
`--out-dir` if specified).

**Multi-rank expansion:**
- **Alchemist (5 ranks)** — expanded into `Alchemist (1/5)` through `Alchemist (5/5)`,
  each with its own skill requirement (0/20/40/60/80) and prerequisite chain.
- **Experimenter (3 ranks)** — expanded into `Experimenter (1/3)` through
  `Experimenter (3/3)`, each with its own skill requirement (50/70/90).

Bare prerequisite names are remapped: `Alchemist` → `Alchemist (1/5)`,
`Experimenter` → `Experimenter (1/3)`.

**Output format** — one perk per line, pipe-delimited:
```
name|skill_level|prerequisite|description
```

Example:
```
Alchemist (1/5)|0|None|Potions and poisons are 20% stronger.
Alchemist (2/5)|20|Alchemist (1/5)|Potions and poisons are 40% stronger.
Physician|20|Alchemist (1/5)|Potions you mix that restore health or stamina are 25% more powerful.
```

## Usage

```bash
python3 TES/Skyrim/alchemy/perks_parse/skyrim_scrape_alchemy_perks.py
```

Or with an explicit output directory:

```bash
python3 TES/Skyrim/alchemy/perks_parse/skyrim_scrape_alchemy_perks.py \
  --out-dir /abs/path/to/perks_parse/
```
