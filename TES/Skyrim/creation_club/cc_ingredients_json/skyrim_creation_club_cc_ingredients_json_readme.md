# Purpose and Action

This directory is intentionally empty.  No CC alchemy ingredients parser is
needed.

## Why

The CC content pages (Rare Curios, Fishing, Bittercup) include food items
described under "Ingredients" headings, but only some of those items are true
alchemy ingredients — i.e., combinable with other ingredients at an alchemy lab
to produce potions.  The actual CC alchemy ingredients (Healing Salts, Ironwood
Fruit, Corkbulb Root, Angler Larvae) are already present in
`skyrim_alchemy_ingredients` from the main Skyrim alchemy scrape.  The
remaining food items in those CC sections are not usable in alchemy and are not
stored in the ingredients table.

Because all CC alchemy ingredients are already in the database, no separate
parse or load step is required for this category.
