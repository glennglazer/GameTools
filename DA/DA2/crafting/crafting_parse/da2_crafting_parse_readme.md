# DA2 Crafting Parse

Scrapes Dragon Age II crafting data from the Fandom Dragon Age wiki and saves it as `da2_crafting_raw.json`.

## Script

`da2_scrape_crafting.py <output_path>`

## What it fetches

| Page | Purpose |
|------|---------|
| `Crafting_(Dragon_Age_II)` | Recipe locations by act and category |
| `Supplier` | Crafting resource node locations by act |
| `Recipe: <name>` / `Design: <name>` / `Formula: <name>` | Ingredients and crafting fee for each recipe |
| `<item name>` | Item effects (from ItemTransformer infobox) |

**Total HTTP calls**: ~68 (2 index pages + 33 recipe pages + 33 item pages)  
**Sleep between requests**: 0.3 s → ~21 s total

## Category → prefix mapping

| Category | Prefix |
|----------|--------|
| Potions | `Recipe:` |
| Runes | `Design:` |
| Poisons and grenades | `Formula:` |

The main crafting page uses three `=== Section ===` headers to separate categories. Item names are extracted from the first `[[...]]` link on each bullet line following an `* Act N[-M]:` prefix.

## Output format

```json
{
  "crafting_wikitext": "...",
  "supplier_wikitext": "...",
  "items": [
    {
      "name": "Elfroot Potion",
      "category": "potions",
      "prefix": "Recipe",
      "recipe_wikitext": "...",
      "item_wikitext": "..."
    },
    ...
  ]
}
```

The scraper fetches recipe and item wikitexts together in a single pass so the parser can extract both recipe ingredients and item effects without a second round of HTTP calls.

## Error handling

Failed fetches print a WARNING to stderr and store an empty string for that wikitext; the parser logs another WARNING and skips those items.

## DLC assumption

All DLCs are assumed installed, including the **Black Emporium** (provides catch-up purchases for permanently-missed resource nodes between acts).
