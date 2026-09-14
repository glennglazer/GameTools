# DA2 Crafting JSON

Parses `da2_crafting_raw.json` into four structured JSON files, one per DB table.

## Script

```
da2_parse_crafting.py <raw_json> <locations_json> <resources_json> <recipes_json> <effects_json>
```

## Output files

| File | Rows | Description |
|------|------|-------------|
| `da2_crafting_recipe_locations.json` | 33 | Where each recipe is found, by act |
| `da2_crafting_resources.json` | ~80 | Crafting resource nodes by act |
| `da2_crafting_recipes.json` | 33 | Sparse ingredient table + crafting fee |
| `da2_crafting_item_effects.json` | 33 | Crafted item effect text |

## Key parsing notes

### depth-counter template extractor

Both `RecipeTransformer` (recipe pages) and `ItemTransformer` (item pages) contain `{{{style|}}}` triple-brace arguments. A naïve `}}` regex terminates at the wrong place; `extract_template_block()` uses a depth counter that correctly handles nested `{{ }}` pairs.

The counter starts at `depth=1` when the opening `{{TemplateName` is found, increments on every subsequent `{{`, and decrements on every `}}`. The block ends at the first `}}` that returns depth to 0.

### Act range parsing

Recipe location lines have the form `* Act N[-M]: [[Item Name]] location text.`

- `"Act 2"` → `{"acts": [2]}`
- `"Act 1-3"` → `{"acts": [1, 2, 3]}`

The `act` column stores this as a JSON string.

### Canonical ingredient mapping

Wiki display names often include disambiguation suffixes (`Elfroot (Dragon Age II)`, `Lyrium (crafting resource)`). `canonical_ingredient()` strips `(...)` suffixes and maps the result to the 12-column ingredient schema:

```
Ambrosia, Deathroot, Deep Mushroom, Dragon's Blood, Elfroot,
Embrium, Felandaris, Glitterdust, Lyrium, Orichalcum, Silverite, Spindleweed
```

Unknown ingredient names print a WARNING to stderr.

### Sparse ingredient table

The recipe table has one column per ingredient (12 total). Unused ingredients store `0`. Most recipes use 1–4 ingredients.

### Currency conversion

Recipe pages include `It costs {{Currency|N}}` where N is the total in bronze:
- `Gold = N // 10000`
- `Silver = (N % 10000) // 100`
- `Bronze = N % 100`

Example: `{{Currency|3750}}` → `Gold=0, Silver=37, Bronze=50`

### Item effects

`{{ColorPositiveStat|text}}` calls are extracted from the `effects` field of the `ItemTransformer` block. Multiple effects (separated by `<br>` in the wikitext) are joined with `"; "`.

### Resource node parsing

The Supplier page organizes rows under `=== Act N ===` headers. The parser tracks the current act and assigns it as an integer column. Empty quest cells are stored as `None`. Display text is extracted from `[[Page|Display]]` links; disambiguation suffixes are stripped from resource names.

## DA2 crafting mechanic note

Ingredient counters in DA2 count **distinct resource nodes discovered**, not items held. Finding one Elfroot node gives unlimited Elfroot supply for a 1-Elfroot recipe, but a 3-Elfroot recipe requires 3 distinct nodes found. Maps are rewritten between acts; unfound nodes are permanently lost (Black Emporium DLC provides partial catch-up).
