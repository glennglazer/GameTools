# Skyrim Smithing Showcase

Two queries demonstrating the smithing database: material planning for a craftable armor set and
efficiency analysis of Dwemer salvage.

---

## Q1 — Glass Armor Set: Full Material Requirements

**Type:** Formula  
**Tables:** `skyrim_smithing_armor`, `skyrim_smelting`

A full Glass armor set (Helmet, Armor, Gauntlets, Boots) using standard Glass Gauntlets. The
table shows direct forge requirements (ingots and leather strips) and the upstream raw materials
needed to produce them: 2 ore smelt into 1 ingot for both Malachite and Moonstone; 1 leather
converts to 4 leather strips at the tanning rack. Leather totals include 1 piece used directly
per recipe plus ⌈strips ÷ 4⌉ for strip conversion, rounded up.

| Piece | Ref. Malachite | Malachite Ore | Ref. Moonstone | Moonstone Ore | Leather Strips | Leather |
|---|---:|---:|---:|---:|---:|---:|
| Glass Helmet | 2 | 4 | 1 | 2 | 1 | 2 |
| Glass Armor | 4 | 8 | 2 | 4 | 3 | 2 |
| Glass Gauntlets | 1 | 2 | 1 | 2 | 2 | 2 |
| Glass Boots | 2 | 4 | 1 | 2 | 2 | 2 |
| **Total** | **9** | **18** | **5** | **10** | **8** | **8** |

**Note on leather rounding:** Every piece in this set needs ⌈strips ÷ 4⌉ = 1 additional leather
regardless of strip count (1, 2, or 3 strips all round up to 1 leather), so all four pieces cost
exactly 2 leather each. Glass armor requires the Glass Smithing perk (Smithing 70, Advanced
Armors branch).

---

## Q2 — Dwemer Salvage: Ingot Yield vs. Carry Weight

**Type:** Strategy  
**Table:** `skyrim_smelting`

All six Dwemer scrap types smelt into Dwarven Metal Ingots (weight 1, value 30 each). Ranked by
ingots per unit of carry weight (efficiency when encumbered) and by raw source value per unit
weight.

| Source Item | Weight | Value | Ingots | Ingots/Wt | Rank | Val/Wt | Rank |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bent Dwemer Scrap Metal | 2 | 15 | 3 | 1.50 | 1 | 7.50 | 1 |
| Large Dwemer Plate Metal | 2 | 15 | 3 | 1.50 | 1 | 7.50 | 1 |
| Small Dwemer Plate Metal | 2 | 15 | 3 | 1.50 | 1 | 7.50 | 1 |
| Solid Dwemer Metal | 25 | 25 | 5 | 0.20 | 4 | 1.00 | 4 |
| Large Dwemer Strut | 20 | 15 | 3 | 0.15 | 5 | 0.75 | 5 |
| Large Decorative Dwemer Strut | 15 | 10 | 2 | 0.13 | 6 | 0.67 | 6 |

**Result:** The two rankings correlate perfectly (Spearman ρ = 1.0). The three compact scraps
(Bent, Large Plate, Small Plate) share identical stats — weight 2, value 15, 3 ingots — and tie
at the top of both lists. The larger pieces fall in the same order by both measures because the
game priced them proportionally to their weight and their ingot yield follows the same logic.

**Practical rule:** Prioritize the weight-2 scrap pieces when encumbered. Solid Dwemer Metal
yields the most ingots per piece (5) but ranks 4th per carry-weight slot. The Large Decorative
Dwemer Strut is the least efficient piece despite its name.

Dwemer items are found, never crafted; smelting them is the only way to obtain Dwarven Metal
Ingots. The Dwarven Smithing perk is required to craft Dwarven armor and weapons from those ingots.
