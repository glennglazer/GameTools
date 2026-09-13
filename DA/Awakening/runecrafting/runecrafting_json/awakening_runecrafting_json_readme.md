# awakening_runecrafting_json_readme.md

Parser for Dragon Age: Origins – Awakening runecrafting data.

## Script

`awakening_parse_runecrafting.py` — reads `runecrafting_raw.json` (from the scraper)
and produces six structured JSON files.

## Output files

| File | Rows | Description |
|------|------|-------------|
| `awakening_runecrafting_skill.json` | 4 | Skill tiers with character-level requirements and rune-level unlocks |
| `awakening_runecrafting_tracing_acquisition.json` | 13 | Non-hybrid tracing sources, one JSON column per rune level (Journeyman…Paragon) |
| `awakening_runecrafting_hybrid_tracing_acquisition.json` | 8 | Hybrid tracing sources (single location each) |
| `awakening_runecrafting_armor_runes.json` | 39 | Armor rune effects by name and level; `level=null` for hybrids |
| `awakening_runecrafting_weapon_runes.json` | 67 | Weapon rune effects by name and level; `level=null` for hybrids |
| `awakening_runecrafting_costs.json` | 16 | Sell-value (gold/silver/bronze) for Novice runes and support items |

## Key parsing decisions

### ItemTransformer depth-counting
The `{{ItemTransformer ...}}` template on each rune page contains `{{{style|}}}` (a
triple-brace template argument). A simple non-greedy regex stops at the first `}}` it
finds inside `}}}`, cutting the block short. The parser instead uses a depth counter
(`{{` → depth+1, `}}` → depth-1) to find the true matching close.

### Rune naming convention
Page names follow the pattern `{Level} {Type} Rune` (e.g. "Novice Flame Rune") or
`{Type} Rune` (hybrid, e.g. "Intensifying Rune"). `parse_rune_page_name()` strips the
trailing " Rune" suffix and level prefix so the DB stores only the type name with the
level in a separate column.

### Hybrid runes
Hybrid runes have no level prefix. `level` is stored as `None` (→ NULL in the DB).
They appear in both `armor_runes.json` and `weapon_runes.json` depending on type.

### Effects (JSON)
Effects are extracted from `{{ColorPositiveStat|effect1 <br> effect2}}` and stored as
`{"effects": ["effect1", "effect2"]}` in the `effect` column.

### Tracing sources (JSON)
Each level column (`journeyman`…`paragon`) stores `{"sources": ["Source1", "Source2"]}`.
`extract_sources()` parses wiki links including `[[Yuriah|Yuriah (+N upgrade/upgrades)]]`
display text, which is preserved verbatim to convey the conditional nature of Yuriah's
restocking events.

### Currency
The `value` field from `ItemTransformer` is in bronze (the game's sell price).
`value_to_currency()` converts it to `(gold, silver, bronze)` with missing higher
denominations filled as 0. **Buy price from merchants = sell_value × 1.1** (documented
in the future RAG doc; not stored in the DB).

### Costs table scope
Only Novice rune pages and the two support items (Blank Runestone, Etching Agent) are
included in `costs.json`. Higher-level rune costs are fully computable from the binary-
tree recurrence documented in the RAG doc (see `CLAUDE.md` for the formula).

## Usage

```bash
python3 DA/Awakening/runecrafting/runecrafting_json/awakening_parse_runecrafting.py \
    /abs/path/to/runecrafting_raw.json \
    /abs/path/to/awakening_runecrafting_skill.json \
    /abs/path/to/awakening_runecrafting_tracing_acquisition.json \
    /abs/path/to/awakening_runecrafting_hybrid_tracing_acquisition.json \
    /abs/path/to/awakening_runecrafting_armor_runes.json \
    /abs/path/to/awakening_runecrafting_weapon_runes.json \
    /abs/path/to/awakening_runecrafting_costs.json
```
