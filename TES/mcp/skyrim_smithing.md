# Skyrim Smithing — Rules and Mechanics

This document covers Skyrim smithing: how items are crafted and improved, how the quality system
works, how Fortify Smithing interacts with effective skill, and how to interpret the data returned
by the MCP tools.

---

## One-Way Processes

All three smithing operations are **irreversible**:

- **Smelting** (smelter): raw ore or Dwemer scrap → ingot. The ingot cannot be broken back down.
- **Crafting** (forge or anvil): ingots + materials → armor or weapon. Items cannot be reduced
  back to ingots.
- **Improving / tempering** (grindstone for weapons, workbench for armor): an ingot of the
  appropriate material is consumed to raise the item's quality. The quality can be raised further
  later (consuming another ingot) but cannot be undone.

Dwemer items (scrap metal from ruins) are always found, never crafted. They are the only source
material for Dwarven Metal Ingots via smelting. Dwarven weapons and armor can be crafted normally
from those ingots once the Dwarven Smithing perk is taken.

---

## Perk Tree

Smithing has ten perks arranged as two branches off a shared base. All perks in the "create and
improve" category also allow improving those items **twice as much** (effectively doubles the
improvement multiplier).

| Perk | Skill | Prerequisite |
|------|-------|-------------|
| Steel Smithing | 0 | None |
| Elven Smithing | 30 | Steel Smithing |
| Advanced Armors | 50 | Elven Smithing |
| Dwarven Smithing | 30 | Steel Smithing |
| Orcish Smithing | 50 | Dwarven Smithing |
| Arcane Blacksmith | 60 | Steel Smithing |
| Glass Smithing | 70 | Advanced Armors |
| Ebony Smithing | 80 | Orcish Smithing |
| Daedric Smithing | 90 | Ebony Smithing |
| Dragon Armor | 100 | Glass Smithing **or** Daedric Smithing |

**Left branch** (primarily light armor): Steel → Elven → Advanced Armors → Glass → Dragon.
**Right branch** (primarily heavy armor): Steel → Dwarven → Orcish → Ebony → Daedric → Dragon.

Advanced Armors also enables Scaled and Steel Plate armor (Steel Plate is heavy despite being on
the light-armor branch). One perk fewer is needed on the left branch to reach Dragon Armor.

**Arcane Blacksmith** (60, off Steel Smithing): required to improve already-enchanted items.
Without this perk, attempting to improve a magical item does nothing.

Steel Smithing also enables Bonemold (Dragonborn DLC) and Vigil armor (Creation Club). The
Creation Club Saints & Seducers content adds Amber and Madness armor and weapons; those can be
crafted and improved without an additional perk once the CC is installed.

---

## Crafting Items

Items are crafted at a **Forge** or **Anvil** using the materials listed in the database. The
relevant perk must be taken to unlock a recipe.

### XP from crafting

```
XP = 3 × item_value ^ 0.65 + 25
```

`item_value` is the base gold value of the crafted item (or cumulative value if multiple items are
produced, e.g. gold rings). The flat +25 per craft makes cheap items reasonably efficient for
leveling — five iron daggers give more XP than one iron armor piece using the same ingots.

**Efficient early leveling**: Gold rings (2 per gold ingot, value ~75 each) give ~52 XP per ore
when using Transmute Mineral Ore to convert iron → silver → gold ore.

---

## Improving Items (Tempering)

Armor is improved at a **Workbench**; weapons at a **Grindstone**. Each improvement consumes one
unit of the item's tempering material (see `skyrim_tempering_materials()` tool).

### Effective Skill

The quality level achievable is determined by **effective smithing skill**:

```
effective_skill = base_smithing_skill + fortify_smithing_total
```

`fortify_smithing_total` is the sum of all active Fortify Smithing bonuses from equipped apparel
enchantments and consumed potions.

### Quality Levels

| Quality Level | Q# | Effective Skill (no perk) | Effective Skill (with perk) | Chest Armor Bonus | Other Bonus | Value Multiplier |
|---------------|----|---------------------------|-----------------------------|-------------------|-------------|-----------------|
| Fine          | 1  | 14                        | 14                          | +2                | +1          | 1.167×          |
| Superior      | 2  | 31                        | 22                          | +6                | +3          | 1.333×          |
| Exquisite     | 3  | 65                        | 40                          | +10               | +5          | 1.5×            |
| Flawless      | 4  | 100                       | 57                          | +13               | +7          | 1.667×          |
| Epic          | 5  | 134                       | 74                          | +17               | +9          | 1.833×          |
| Legendary     | 6  | 168                       | 91                          | +20               | +10         | 2.0×            |

"Other" covers helmets, gauntlets, boots, shields, and weapons.

"With perk" means having the smithing perk specific to the item's material category (e.g. Ebony
Smithing for ebony items, Daedric Smithing for daedric items). Items with **no associated perk**
(Iron, some unique pieces) always use the "no perk" column — their natural maximum is Flawless
(effective_skill 100). Fortify Smithing can push them higher.

### Disclosing Legendary Quality

**Always disclose the actual quality number when quality is Legendary.** The game permanently
displays "Legendary" for any quality level ≥ 6, but the actual bonuses continue to increase with
higher effective skill. Reporting "Legendary" without a number is ambiguous and unhelpful to the
player.

Format: **Legendary (Q)** — e.g., "Legendary (24)" or "Legendary (6)".

### Beyond Legendary

Quality levels above 6 are achievable through Fortify Smithing stacking. The bonus continues to
grow approximately linearly past Legendary:

- **Without perk**: each additional quality level requires approximately **34 more effective
  skill**, matching the spacing between Exquisite–Epic–Legendary. Threshold for Q=7: ~202,
  Q=8: ~236, and so on.
- **With perk**: approximately **17 more effective skill** per quality level past Legendary.

Maximum effective skill (and approximate quality) achievable in the base game with the full
alchemy–enchanting loop:

| Configuration | Max Effective Skill | Approx. Quality |
|--------------|--------------------|-----------------| 
| Base game (no Dragonborn DLC) | ~974 | Legendary (29) |
| With Dragonborn DLC (Seeker of Might) | ~1393 | Legendary (41) |

These assume the alchemy–enchanting feedback loop is fully optimized (see the Skyrim Enchanting
rules for details).

### XP from improving

```
ΔXP = 3.8 × ΔValue ^ 0.5 × ΔQ ^ 0.5
```

where `ΔValue` is the gold value increase from the improvement and `ΔQ` is the change in quality
number. Improving expensive items (Ebony, Daedric) or going several quality levels at once gives
significantly more XP.

---

## Armor Rating Cap

The game caps effective damage reduction at a displayed armor rating of **567**. Any total worn
armor rating above 567 provides no additional protection in almost all combat scenarios. A very
small number of rare enemies ignore a percentage of armor, making minor amounts above 567 useful
only against them.

Practical implication: crafting and improving armor beyond what is needed to reach 567 across the
four worn pieces (head, chest, hands, feet) is generally not worth the ingots. With sufficiently
high Smithing skill and Fortify Smithing, almost any armor material can be improved to reach the
cap — the difference in base armor rating between materials mostly determines whether you need
one more or fewer ingot to get there.

---

## Smelting Special Notes

**Steel Ingot is the only smelting recipe that requires two different ore types.** One Steel Ingot
requires 1 Iron Ore AND 1 Corundum Ore. All other smelting recipes use a single source material.

**Stalhrim cannot be smelted.** It is extracted from burial sites in Solstheim (Dragonborn DLC)
and used directly as a crafting material. The smelting database contains a Stalhrim row with all
numeric fields NULL and a note explaining this.

**Creation Club additions** (Saints & Seducers):
- 2 Amber → 1 Refined Amber
- 2 Madness Ore → 1 Madness Ingot

**Dwemer scrap metal** smelts into Dwarven Metal Ingots at rates of 1–5 ingots per piece
depending on the scrap type. Dwemer items are always found, never crafted; smelting them is
the only way to obtain Dwarven Metal Ingots.

---

## Weapon and Armor Quality Hierarchy

For reference when advising players on upgrade paths (highest quality = best base stats before
tempering):

**Weapons** (ascending damage): Iron < Steel < Orcish < Dwarven < Elven = Nord Hero < Glass <
Ebony ≤ Stalhrim < Daedric < Dragonbone = Amber (lighter) < Madness

**Heavy Armor** (ascending base rating): Iron = Ancient Nord < Steel < Bonemold < Dwarven <
Improved Bonemold < Orcish < Steel Plate = Chitin < Golden < Nordic < Ebony < Dragonplate =
Stalhrim < Daedric < Madness

**Light Armor** (ascending base rating): Hide < Leather < Elven < Chitin < Scaled = Elven
Gilded < Dark < Glass < Stalhrim < Dragonscale < Amber

Note: after tempering to the armor cap (567), base armor rating differences matter less than
weight, perk availability, and aesthetic preference.

---

## Fortify Smithing Loop

Analogous to the alchemy–enchanting loop: craft Fortify Smithing potions using Fortify Alchemy
gear, use those potions to enchant stronger Fortify Alchemy gear, and finally use both to produce
the maximum Fortify Smithing effect. See the Skyrim Enchanting rules for the full loop procedure.

---

## What the Database Tools Cover

| Question | Tool |
|----------|------|
| What smithing perks exist and what do they require? | `skyrim_smithing_perks()` |
| What materials do I need to craft armor piece X? | `skyrim_smithing_armor(name)` |
| What armor pieces can I make with Elven Smithing? | `skyrim_smithing_armor(perk='Elven')` |
| What materials do I need to craft weapon X? | `skyrim_smithing_weapons(name)` |
| What is the tempering material for Daedric items? | `skyrim_tempering_materials('Daedric')` |
| What quality level will my item reach at skill X? | `skyrim_smithing_improvement()` + compare effective_skill |
| What ore/scrap does this ingot come from? | `skyrim_smelting(ingot=name)` |
| What ingot comes from this ore? | `skyrim_smelting(source=name)` |

The `skyrim_smithing_improvement()` tool returns the full quality table including all thresholds;
compute quality level by finding the highest threshold ≤ effective_skill in the appropriate column.
Always report quality as **Legendary (N)** when quality_number ≥ 6.
