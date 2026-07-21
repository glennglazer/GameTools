# Skyrim Alchemy — Rules and Mechanics

This document covers the game rules for Skyrim alchemy: how potions are crafted, how perk bonuses
apply, how effects are classified, and how to interpret the data returned by the MCP tools. Use it
alongside the `skyrim_alchemy_*` tool functions, which query the live database.

---

## Crafting Mechanics

Potions are crafted at an **Alchemy Lab** using 2 or 3 ingredients. The result depends on which
effects the chosen ingredients **share**:

- Two ingredients can be combined if they share **at least one effect**.
- Three ingredients can be combined if **any pair** among them shares at least one effect. Effects
  from pairs that don't share an effect with any other ingredient in the combo are excluded from
  the final potion.
- An effect appears in the final potion only if **two or more** ingredients in the combo carry it.
  Effects present on only one ingredient are discarded.
- There is no upper limit on how many distinct effects a single potion can have — a well-chosen
  three-ingredient combo can produce potions with 4 or more effects simultaneously.

Each ingredient has exactly **four effects** in Skyrim. The first effect of every ingredient is
always revealed (no discovery needed). Additional effects are discovered by:
- Crafting potions that include the ingredient
- Eating the ingredient (reveals effects 1–N based on the Experimenter perk rank)
- Using the Keen Eye perk (not alchemy — this is harvesting)

---

## Effect Classification

Effects are classified as **beneficial** (positive for the player) or **harmful** (negative for
the player, useful as poisons applied to weapons). This classification determines which perks boost
a given potion.

**Beneficial effects** (60 distinct effects include these):
- All `Restore X` effects (Restore Health, Restore Magicka, Restore Stamina)
- All `Regenerate X` effects (Regenerate Health, Regenerate Magicka, Regenerate Stamina)
- All `Fortify X` effects (Fortify Health, Fortify Smithing, Fortify Enchanting, etc.)
- All `Resist X` effects (Resist Fire, Resist Frost, Resist Magic, Resist Poison, Resist Shock)
- Cure Disease, Cure Poison
- Invisibility, Night Eye, Light, Waterbreathing, Spell Absorption

**Harmful effects** (usable as poisons):
- All `Damage X` effects (Damage Health, Damage Magicka, Damage Stamina)
- All `Lingering Damage X` effects
- All `Ravage X` effects (Ravage Health, Ravage Magicka, Ravage Stamina)
- All `Weakness to X` effects
- All `Damage X Regen` effects
- Paralysis, Fear, Frenzy, Slow

**Fortify Barter** and **Fortify Persuasion** are beneficial but primarily economic (selling value,
Speech checks) — they don't improve combat or crafting capability directly.

---

## Perk Tree

The Skyrim alchemy perk tree (queryable via `skyrim_alchemy_perks()`) has 15 nodes across 9
named perks:

| Perk | Skill | Prerequisite | Effect Summary |
|------|-------|-------------|----------------|
| Alchemist (1/5) | 0 | None | +20% potion/poison strength |
| Alchemist (2/5) | 20 | Alchemist 1 | +40% |
| Alchemist (3/5) | 40 | Alchemist 2 | +60% |
| Alchemist (4/5) | 60 | Alchemist 3 | +80% |
| Alchemist (5/5) | 80 | Alchemist 4 | +100% (double strength) |
| Physician | 20 | Alchemist 1 | Restore Health/Stamina potions +25% |
| Poisoner | 30 | Physician | Poisons +25% effective |
| Benefactor | 30 | Physician | Beneficial-effect potions sell for +25% more |
| Experimenter (1/3) | 50 | Benefactor | Eating reveals 2 effects instead of 1 |
| Experimenter (2/3) | 70 | Experimenter 1 | Eating reveals 3 effects |
| Experimenter (3/3) | 90 | Experimenter 2 | Eating reveals all 4 effects |
| Concentrated Poison | 60 | Poisoner | Poisons last 2 hits instead of 1 |
| Green Thumb | 70 | Concentrated Poison | Harvest 2 ingredients from plants |
| Snakeblood | 80 | Concentrated Poison + Experimenter 1 | 50% poison resistance |
| Purity | 100 | Snakeblood | Remove negative effects from potions; remove positive effects from poisons |

**Perk priority guidance:**
- For potion crafting and gold-making: Alchemist (all 5 ranks) → Physician → Benefactor
- For poison builds: Alchemist → Poisoner → Concentrated Poison
- For gathering: Green Thumb is high value on any playthrough with significant alchemy use
- Purity is niche — it produces clean potions/poisons but requires 100 Alchemy and Snakeblood

---

## Skill Progression

Alchemy skill XP is gained per craft and scales with the **gold value** of the potion produced.
Higher-value potions give more XP. The most efficient leveling strategies exploit high-value effect
combinations (e.g., Fortify Enchanting, Fortify Smithing, Paralysis).

Skill level directly multiplies potion magnitude and duration: an Alchemy 100 character produces
significantly stronger potions than an Alchemy 15 character crafting the same ingredients. The
exact formula involves both the skill multiplier and any active perk bonuses applied multiplicatively.

The **Fortify Restoration loop** (buffing Fortify Restoration potions then re-equipping Restoration
gear to boost the next batch) is a known mechanic interaction but is out of scope for the standard
crafting queries.

---

## Effect Interaction Notes

**Cross-skill synergies** — these effect pairings are commonly used to boost other crafting skills:
- `Fortify Enchanting`: boosts enchanting potency; found on 9 ingredients
- `Fortify Smithing`: boosts tempering quality; found on several ingredients
- `Fortify Alchemy`: found on enchanted apparel, not on ingredients (no ingredient has this effect)

**Multi-effect potions** — three-ingredient combos can produce potions that do multiple things. For
example, combining Ancestor Moth Wing + Blue Butterfly Wing produces a potion with all four shared
effects: Damage Stamina, Damage Magicka Regen, Fortify Conjuration, and Fortify Enchanting.

**Poisons on weapons** — harmful-effect potions are applied to weapons with the `E` key. Each
application lasts 1 hit normally, or 2 hits with Concentrated Poison. Poisons cannot be stacked.

---

## What the Database Tools Cover

| Question | Tool to use |
|----------|-------------|
| What effects does ingredient X have? | `skyrim_alchemy_ingredient(name)` |
| Which ingredients have effect X? | `skyrim_alchemy_find_by_effect(effect)` |
| Given my ingredients, what can I combine? | `skyrim_alchemy_combos(ingredients)` |
| What are all possible effects? | `skyrim_alchemy_list_effects()` |
| What does perk X do / what skill level does it need? | `skyrim_alchemy_perks()` |
| Search for an ingredient by partial name | `skyrim_alchemy_search(query)` |

The tools return live data from the SQLite database. This document provides the rules context
needed to interpret the results and answer questions the database alone cannot answer (strategy,
formula details, mechanic interactions).
