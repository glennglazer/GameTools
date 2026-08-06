# Skyrim Homestead (Hearthfire) — Construction Rules

## Overview

Hearthfire adds three buildable manors: **Lakeview Manor**, **Heljarchen Hall**, and
**Windstad Manor**. Each is independent but shares the same room catalogue and construction
system. All building is **one-way**: materials spent cannot be recovered. There is no
"undo" — only the finished or partially-finished structure.

## Location Taxonomy

Every buildable item in `skyrim_homestead_build` belongs to a `location`. Use these
location prefixes with `skyrim_homestead_build(location=...)` and
`skyrim_homestead_manifest(locations=...)`:

| Location prefix | Description |
|---|---|
| `Small House` | Starting small house on each plot |
| `Main Hall` | Core hall added to the foundation |
| `Main_Hall_Downstairs_*` | Main Hall ground-floor furnishings |
| `Main_Hall_Upstairs_*` | Main Hall upper-floor furnishings |
| `Main_Hall_Back_Room_*` | Main Hall back room furnishings |
| `Entryway` | Optional conversion of Small House into pass-through entry (after Main Hall) |
| `West_Wing` | Tower wing shell (structural only) |
| `West_Wing_Enchanter's_Tower_*` | Tower wing — Enchanter's Tower room furnishings |
| `West_Wing_Bedrooms_*` | Tower wing — Bedrooms room furnishings |
| `West_Wing_Greenhouse_*` | Tower wing — Greenhouse room furnishings |
| `North_Wing` | Room with Outdoor Patio wing shell (structural only) |
| `North_Wing_Trophy_Room_*` | Patio wing — Trophy Room furnishings |
| `North_Wing_Storage_Room_*` | Patio wing — Storage Room furnishings |
| `North_Wing_Alchemy_Laboratory_*` | Patio wing — Alchemy Laboratory furnishings |
| `East_Wing` | Downstairs Room wing shell (structural only) |
| `East_Wing_Library_*` | Downstairs wing — Library room furnishings |
| `East_Wing_Armory_*` | Downstairs wing — Armory room furnishings |
| `East_Wing_Kitchen_*` | Downstairs wing — Kitchen room furnishings |
| `Cellar` | Underground cellar (added after Main Hall) |
| `Cellar_Aquarium_*` | CC Aquarium extension of the Cellar |
| `Exterior` | Exterior structures: Stable, Apiary, Fish Hatchery, etc. |

**Wing restriction**: each manor has exactly **one** wing slot. Choose one of the three wing
shells (West/North/East) and exactly **one** room within it. Do not combine furnishing rows
from multiple wing types or multiple rooms in the same manifest.

## Three-Layer Materials Hierarchy

Building anything in Hearthfire involves up to three layers of abstraction:

```
Completed object  (the built room/item)
      ↓
Constructed component  (nails, hinge, iron fittings, lock — built at the forge)
      ↓
Base material  (iron ore → iron ingot → nails; leather → leather strips)
```

The `skyrim_homestead_manifest(locations, level)` tool computes materials at each layer.

### Level 1 — Component (raw build table)

Returns the exact quantities listed in `skyrim_homestead_build`: crafted components
(nails, hinge, iron_fittings, lock) appear as integer counts alongside direct materials
(sawn logs, quarried stone, ingots, etc.). This is the closest to what the in-game
building menu shows.

### Level 2 — Ingot (crafted components expanded)

Crafted components are resolved to the ingots consumed to forge them. Batch sizes matter:

| Component | Batch size | Iron Ingot | Corundum Ingot |
|---|---|---|---|
| nails | 10 per forge action | 1 | 0 |
| hinge | 2 per forge action | 1 | 0 |
| iron fittings | 1 per forge action | 1 | 0 |
| lock | 1 per forge action | 1 | 1 |

**Ceiling rule**: always round up to whole forge actions.
`batches = ceil(needed / batch_size)`, `ingots = batches × ingots_per_batch`.

**Batch waste**: `produced = batches × batch_size`, `waste = produced − needed`.
The manifest reports this when any waste is non-zero. For example, needing 11 nails requires
2 forge actions (20 produced), wasting 9 nails.

At Level 2, `leather_strips` remains as a distinct column — it is converted at Level 3.

### Level 3 — Ore / Base (raw materials)

All ingot columns are replaced by the raw ores used to smelt them:

| Build-table column | Ore needed | Rate |
|---|---|---|
| `iron_ingot` | Iron Ore | 1 ore per ingot |
| `corundum_ingot` | Corundum Ore | 2 ore per ingot |
| `steel_ingot` | Iron Ore **and** Corundum Ore | 1 of each per ingot |
| `quicksilver_ingot` | Quicksilver Ore | 2 ore per ingot |
| `refined_moonstone` | Moonstone Ore | 2 ore per ingot |
| `gold_ingot` | Gold Ore | 2 ore per ingot |
| `orichalcum_ingot` | Orichalcum Ore | 2 ore per ingot |
| `silver_ingot` | Silver Ore | 2 ore per ingot |
| `ebony_ingot` | Ebony Ore | 2 ore per ingot |
| `refined_malachite` | Malachite Ore | 2 ore per ingot |

**Steel special case**: Steel Ingot = 1 Iron Ore + 1 Corundum Ore. Both ore types are added
to their respective totals for every steel ingot.

**Leather strips**: the tanning rack produces 4 leather strips from 1 leather.
At Level 3, `leather_strips` is folded into `leather`: `leather = ceil(strips / 4)`.

**Non-reducible materials** carry through unchanged at all levels:
`sawn_log`, `quarried_stone`, `clay`, `glass`, `straw`, `filled_grand_soul_gem`,
all hides and pelts (deer_hide, goat_hide, wolf_pelt, sabre_cat_pelt, sabre_cat_snow_pelt,
bear_pelt), teeth and horns (sabre_cat_tooth, goat_horns, large_antlers, small_antlers,
horker_tusk), creature parts (vampire_dust, mudcrab_chitin, slaughterfish_scales),
bones (dragon_bone, dragon_scales), amulets (amulet_of_*), gems (flawless_amethyst,
flawless_sapphire).

## Steward vs. Self-Build

The steward NPC can furnish most rooms for gold, or the player can build everything
manually — the result is identical. Use `skyrim_homestead_steward_cost()` to see per-room
gold costs. Steward furnishing and manual building are interchangeable for any given room.

**Exception**: the Cellar cannot be furnished by the steward — all cellar items must be
built by the player at the in-game workbench.

## Entry Hall Ordering Rule

After the Main Hall is built, the player can optionally convert the Small House into an
Entryway (pass-through hall). This adds beds to the upstairs area of the Small House.
**If the player has or plans to adopt children**, those beds will block the placement of
children's chests in the same area. The player must **furnish the Main Hall upstairs first**
before converting the Small House into the Entryway, or the children's chest locations will
be permanently blocked.

Location for Entryway materials: `Entryway` in the build table.

## Key Query Patterns

**What do I need to build my Enchanter's Tower (shell + furnishings)?**
```
skyrim_homestead_manifest(locations="West_Wing,West_Wing_Enchanter's_Tower", level=1)
```

**Full manor manifest at the ore level:**
```
skyrim_homestead_manifest(level=3)  # no locations = all rows
```

**Just the Main Hall at ingot level:**
```
skyrim_homestead_manifest(locations="Main Hall,Main_Hall", level=2)
```

**Can the steward furnish my Alchemy Laboratory?**
```
skyrim_homestead_steward_cost(room="Alchemy")
```
→ Yes, at 2500 gold for `North_Wing_Alchemy_Laboratory`.

## Database Tables

| Table | Key | Description |
|---|---|---|
| `skyrim_homestead_build` | `(section, location)` | 410 rows; 48 material columns (0 = not needed) |
| `skyrim_homestead_crafted_components` | `name` | 4 forge recipes for nails/hinge/iron fittings/lock |
| `skyrim_homestead_steward_cost` | `room` | Gold cost per room (steward furnishing); 12 rows |
| `skyrim_homestead_exclusive_exterior` | `manor` | Each manor's unique exterior option |

JOIN pattern for steward cost:
```sql
SELECT b.location, c.gold_cost
FROM skyrim_homestead_build b
JOIN skyrim_homestead_steward_cost c
  ON b.location LIKE c.room || '%'
```
