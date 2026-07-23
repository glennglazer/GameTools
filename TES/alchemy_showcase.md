# TES Alchemy Showcase

Thirteen cross-game alchemy queries with full working, using live data from the GameTools SQLite database.

---

## Query 1 — Morrowind: Ingredients for Resist Blight Disease

```sql
SELECT name FROM morrowind_alchemy_effects WHERE effect = 'Resist Blight Disease';
```

**Result: no rows returned.** The effect "Resist Blight Disease" does not exist in Morrowind alchemy. Blight diseases are unique to Vvardenfell, but no ingredient carries a resistance to them. The closest available effects are:

**Resist Common Disease** (standard diseases only; does not protect against Blight):

```sql
SELECT name FROM morrowind_alchemy_effects WHERE effect = 'Resist Common Disease' ORDER BY name;
```

| Ingredient |
|-----------|
| Ash Yam |
| Bear Pelt |
| Kagouti Hide |
| Pearl |
| Resin |
| Snow Bear Pelt |
| Snow Wolf Pelt |
| Wolf Pelt |

**Cure Blight Disease** (treats an active Blight infection after contracting it):

```sql
SELECT name FROM morrowind_alchemy_effects WHERE effect = 'Cure Blight Disease' ORDER BY name;
```

| Ingredient |
|-----------|
| Ash Salts |
| Meteor Slime |
| Scrib Jelly |

To avoid Blight proactively on Vvardenfell, carry Cure Blight Disease potions or seek out a Dunmer Temple healer. Resist Common Disease is useless against Blight specifically.

---

## Query 2 — Oblivion: Potion from Black Tar and Boar Meat

```sql
SELECT effect FROM oblivion_alchemy_effects
WHERE name = 'Black Tar' AND effect IS NOT NULL ORDER BY rowid;

SELECT effect FROM oblivion_alchemy_effects
WHERE name = 'Boar Meat' AND effect IS NOT NULL ORDER BY rowid;
```

**Black Tar effects (game order):**

| Position | Effect |
|----------|--------|
| 1 | Damage Speed |
| 2 | Damage Fatigue |
| 3 | Damage Health |
| 4 | Shock Damage |

**Boar Meat effects (game order):**

| Position | Effect |
|----------|--------|
| 1 | Restore Health |
| 2 | Damage Speed |
| 3 | Fortify Health |
| 4 | Burden |

**Shared effect: Damage Speed**

- In Black Tar: **position 1** — visible at any skill level (Novice)
- In Boar Meat: **position 2** — visible at Apprentice rank (Alchemy ≥ 25)

**Minimum required skill: Apprentice (Alchemy 25)**

**Result: Poison of Damage Speed**

Below skill 25, Boar Meat shows only Restore Health, which has no counterpart in Black Tar — no potion can be made. At skill 25 or above, Boar Meat's Damage Speed becomes visible and the two ingredients overlap. Since Damage Speed is a harmful effect and all shared effects must be negative for the result to be a poison, this produces a green poison applied to a weapon.

---

## Query 3 — Skyrim: Ingredients with only positive effects

In Skyrim, ingredient effects are always fully visible regardless of skill. The question is which ingredients carry only beneficial effects — none that damage, weaken, ravage, or otherwise harm.

**Harmful effects excluded by this query:**
Damage Health, Damage Magicka, Damage Stamina, Damage Magicka Regen, Damage Stamina Regen,
Lingering Damage Health/Magicka/Stamina, Ravage Health/Magicka/Stamina,
Weakness to Fire/Frost/Shock/Poison/Magic, Paralysis, Frenzy, Fear, Slow.

```sql
SELECT name FROM skyrim_alchemy_effects
WHERE effect IS NOT NULL
GROUP BY name
HAVING SUM(CASE WHEN effect IN (
    'Damage Health','Damage Magicka','Damage Stamina',
    'Damage Magicka Regen','Damage Stamina Regen',
    'Lingering Damage Health','Lingering Damage Magicka','Lingering Damage Stamina',
    'Ravage Health','Ravage Magicka','Ravage Stamina',
    'Weakness to Fire','Weakness to Frost','Weakness to Shock',
    'Weakness to Poison','Weakness to Magic',
    'Paralysis','Frenzy','Fear','Slow'
) THEN 1 ELSE 0 END) = 0
ORDER BY name;
```

**37 ingredients with only positive effects:**

| | | | |
|---|---|---|---|
| Ambrosia | Angelfish | Beehive Husk | Blind Watcher's Eye |
| Blister Pod Cap | Charred Skeever Hide | Dragon's Tongue | Felsaad Tern Feathers |
| Fungus Stalk | Garlic | Glassfish | Glowing Mushroom |
| Goldfish | Hawk Beak | Hawk Feathers | Heart of Order |
| Hydnum Azure Giant Spore | Juvenile Mudcrab | Lichor | Lyretail Anthias |
| Mudcrab Chitin | Pearl | Pearlfish | Red Kelp Gas Bladder |
| Salmon Roe | Screaming Maw | Scrib Jelly | Small Pearl |
| Snowberries | Spadefish | Steel-Blue Entoloma | Tundra Cotton |
| Vampire Dust | Void Essence | Watcher's Eye | Wisp Wrappings |
| Withering Moon | | | |

Many are Dragonborn DLC fish or Dawnguard-era flora. The only widely available vanilla ingredients on this list are Garlic, Mudcrab Chitin, Snowberries, and Vampire Dust.

---

## Query 4 — Morrowind: Resist Fire potion

**Character:** Alchemy 50, Intelligence 70, Luck 25
**Apparatus:** Apprentice Mortar & Pestle (0.5), Journeyman Alembic (1.0), Master Calcinator (1.2), Grandmaster Retort (1.5)

**Ingredients with Resist Fire:**
```sql
SELECT name FROM morrowind_alchemy_effects WHERE effect = 'Resist Fire' ORDER BY name;
```
→ Ash Yam, Black Anther, Fire Petal, Frost Salts. Any two can be combined.

---

**Step 1 — SkillFactor and success chance**

```
SkillFactor = Alchemy + Intelligence/10 + Luck/10
            = 50 + 70/10 + 25/10
            = 50 + 7 + 2.5
            = 59.5
```

**Success Chance: 59.5%** — just under three-in-five odds of the attempt succeeding. Stock up on ingredients.

---

**Step 2 — EffectBaseCost**

Resist Fire EffectBaseCost = **1.0** (Morrowind Construction Set constant; not stored in the GameTools database).

---

**Step 3 — Base values (Mortar & Pestle only)**

```
Base_Strength = SkillFactor × MortarQuality / (3 × EffectBaseCost)
              = 59.5 × 0.5 / (3 × 1.0)
              = 29.75 / 3
              = 9.917

Base_Duration = SkillFactor × MortarQuality / EffectBaseCost
              = 59.5 × 0.5 / 1.0
              = 29.75
```

---

**Step 4 — Apparatus modifier (positive effect)**

Resist Fire is positive. Both Calcinator (1.2) and Retort (1.5) are present:

```
Adjustment = CalcinatorQuality + (RetortQuality × 2)
           = 1.2 + (1.5 × 2)
           = 1.2 + 3.0
           = 4.2
```

The Journeyman Alembic has **no effect on positive effects** — it only reduces negative side effects.

---

**Step 5 — Final values**

```
Final_Strength = 9.917 + 4.2 = 14.117  →  14 (rounded)
Final_Duration = 29.75 + 4.2  = 33.95   →  34 (rounded)
Value          = SkillFactor × MortarQuality = 59.5 × 0.5 = 29.75  →  30 gp
```

**Result: Resist Fire 14% for 34 seconds | 59.5% success chance | 30 gp**

---

## Query 5 — Morrowind: "Resist Health" (→ Restore Health)

**The effect "Resist Health" does not exist in Morrowind.** There is no Resist Health spell effect in any Elder Scrolls game. The closest meaningful interpretation is **Restore Health**, which does exist.

**Same character and apparatus as Query 4.**

**Ingredients with Restore Health:**
```sql
SELECT name FROM morrowind_alchemy_effects WHERE effect = 'Restore Health' ORDER BY name;
```
→ Ampoule Pod, Balyna's Soothing Balm, Bloat, Bread, Comberry, Crab Meat, Diamond, Emerald, Hackle-Lo Leaf, Human Flesh, Luminous Russula, Marshmerrow, Roobrush, Saltrice, Scrib Jelly, and more.

---

**Step 1 — SkillFactor:** 59.5 (same as Query 4)

**Step 2 — EffectBaseCost:** Restore Health = **2.0** (Morrowind CS; twice the cost of Resist Fire)

**Step 3 — Base values**

```
Base_Strength = 59.5 × 0.5 / (3 × 2.0) = 29.75 / 6 = 4.958
Base_Duration = 59.5 × 0.5 / 2.0        = 29.75 / 2 = 14.875
```

**Step 4 — Apparatus modifier:** same as Query 4 → Adjustment = 4.2

**Step 5 — Final values**

```
Final_Strength = 4.958 + 4.2 = 9.158   →  9 HP
Final_Duration = 14.875 + 4.2 = 19.075 →  19 seconds
Value          = 29.75  →  30 gp
```

**Result: Restore Health 9 HP for 19 seconds | 59.5% success chance | 30 gp**

The apparatus modifier (+4.2) added the same absolute points to both effects. But because Restore Health starts from a smaller base (due to higher EffectBaseCost), the modifier is proportionally more valuable here — it added 47% of the unadjusted magnitude for Resist Fire (4.2/9.9) but 85% for Restore Health (4.2/4.96). A Grandmaster Retort is doing real work even on low-skill potions.

---

## Query 6 — Oblivion: Resist Frost, Apprentice apparatus

**Character:** Alchemy 50, Luck 70
**Apparatus:** Full Apprentice set — Mortar & Pestle (0.25), Calcinator (0.25), Retort (0.25), Alembic (0.25)

**Ingredients with Resist Frost:**
```sql
SELECT name FROM oblivion_alchemy_effects WHERE effect = 'Resist Frost' ORDER BY name;
```
→ Columbine Root Pulp, Dryad Saddle Polypore Cap, Fire Salts, Redwort Flower, Sacred Lotus Seeds, Steel-Blue Entoloma Cap

**Effect base_cost from database:**
```sql
SELECT DISTINCT base_cost FROM oblivion_alchemy_effects WHERE effect = 'Resist Frost';
-- 0.5
```

---

**Step 1 — Effective Alchemy**

```
Effective_Alchemy = Alchemy + 0.4 × (Luck − 50)
                  = 50 + 0.4 × (70 − 50)
                  = 50 + 8
                  = 58
```

**Step 2 — Price**

```
Price = floor((Effective_Alchemy + M&P_Strength × 25) × 0.45)
      = floor((58 + 0.25 × 25) × 0.45)
      = floor(64.25 × 0.45)
      = floor(28.91)
      = 28 gp
```

**Step 3 — Magicka Cost**

```
Magicka_Cost = 58 + 0.25 × 25 = 64.25
```

**Step 4 — Base magnitude and duration** (Resist Frost is a "Most Effects" positive type)

```
Base_Mag = (Magicka_Cost / (base_cost/10 × 4)) ^ (1/2.28)
         = (64.25 / (0.05 × 4)) ^ (1/2.28)
         = (64.25 / 0.2) ^ (1/2.28)
         = 321.25 ^ 0.4386
         = 12.575

Base_Dur = 4 × 12.575 = 50.30
```

**Step 5 — Apparatus modifier (Exception 1)**

Both Calcinator (C = 0.25) AND Retort (R = 0.25) are present, and Resist Frost is a positive effect. Exception 1 applies — the Calcinator factor for magnitude is boosted from 0.35 to 1.40:

```
Magnitude = Base_Mag × (1 + 1.4C + 0.5R)
          = 12.575 × (1 + 1.4×0.25 + 0.5×0.25)
          = 12.575 × (1 + 0.35 + 0.125)
          = 12.575 × 1.475
          = 18.55  →  19%

Duration  = Base_Dur × (1 + 0.35C + R)
          = 50.30 × (1 + 0.35×0.25 + 0.25)
          = 50.30 × (1 + 0.0875 + 0.25)
          = 50.30 × 1.3375
          = 67.28  →  67 seconds
```

The Alembic has no effect on positive effects (Alembic_Fac = 0 for positive).

**Result: Resist Frost 19% for 67 seconds | 28 gp**

---

## Query 7 — Oblivion: Resist Frost, Master apparatus

**Same character, same effect — apparatus upgraded to a full Master set (strength 1.0 each).**

**Price:**

```
Magicka_Cost = 58 + 1.0 × 25 = 83
Price = floor(83 × 0.45) = floor(37.35) = 37 gp
```

**Base values:**

```
Base_Mag = (83 / 0.2) ^ (1/2.28) = 415 ^ 0.4386 = 14.069
Base_Dur = 4 × 14.069 = 56.28
```

**Exception 1** (C = 1.0, R = 1.0):

```
Magnitude = 14.069 × (1 + 1.4×1.0 + 0.5×1.0)
          = 14.069 × 2.9
          = 40.80  →  41%

Duration  = 56.28 × (1 + 0.35×1.0 + 1.0)
          = 56.28 × 2.35
          = 132.26  →  132 seconds
```

**Result: Resist Frost 41% for 132 seconds | 37 gp**

**Comparison (Apprentice vs Master):**

| | Apprentice | Master | Gain |
|---|---|---|---|
| Price | 28 gp | 37 gp | +32% |
| Magnitude | 19% | 41% | +116% |
| Duration | 67 s | 132 s | +97% |

Upgrading the full apparatus set roughly doubles both magnitude and duration while adding only 9 gp to the selling price — a strong investment for a serious alchemist.

---

## Query 8 — Oblivion: Invisibility, Apprentice apparatus

**Same character and apparatus as Query 6 (Apprentice full set).**

**Effect base_cost from database:**
```sql
SELECT DISTINCT base_cost FROM oblivion_alchemy_effects WHERE effect = 'Invisibility';
-- 40.0
```

**Invisibility is a Duration-Only effect** — magnitude is always 1; only duration varies. The six Duration-Only effects in Oblivion are: Invisibility, Night-Eye, Paralyze, Silence, Water Breathing, Water Walking.

**Price:** 28 gp (same formula; only M&P and skill affect price)

**Base Duration:**

```
Base_Dur = Magicka_Cost / (base_cost / 10)
         = 64.25 / (40.0 / 10)
         = 64.25 / 4
         = 16.06 seconds
```

**Apparatus modifier for Duration-Only positive effects:**

Invisibility is positive, so Alembic_Fac = 0. The Duration-Only formula:

```
Duration = Base_Dur × (1 + 0.25C + 0.35R − 2A)
         = 16.06 × (1 + 0.25×0.25 + 0.35×0.25 − 2×0)
         = 16.06 × (1 + 0.0625 + 0.0875)
         = 16.06 × 1.15
         = 18.47  →  18 seconds
```

**Result: Invisibility for 18 seconds | magnitude 1 (fixed) | 28 gp**

---

## Query 9 — Oblivion: Dispel, Apprentice apparatus

**Same character and apparatus as Query 6 (Apprentice full set).**

**Effect base_cost from database:**
```sql
SELECT DISTINCT base_cost FROM oblivion_alchemy_effects WHERE effect = 'Dispel';
-- 3.6
```

**Dispel is a Magnitude-Only effect** — duration is always 1; only magnitude varies.

**Price:** 28 gp (same formula)

**Base Magnitude:**

```
Base_Mag = (Magicka_Cost / (base_cost / 10)) ^ (1 / 1.28)
         = (64.25 / 0.36) ^ (1/1.28)
         = 178.47 ^ 0.7813
         = 57.42
```

**Apparatus modifier — the Dispel quirk:**

Dispel interacts with Calcinator and Retort differently from other effects. The standard formula and the combined formula give strikingly different results:

| Apparatus | Formula | Multiplier | Magnitude |
|-----------|---------|-----------|-----------|
| None | 1 | 1.000 | 57 |
| Calcinator only (C=0.25) | 1 + 0.3×C | 1.075 | 62 |
| Retort only (R=0.25) | 1 + 0.5×R | 1.125 | **65** |
| **Both C + R (full set)** | **1 + 0.15×C×R** | **1.009** | **58** |

```
Magnitude (full Apprentice set) = 57.42 × (1 + 0.15 × 0.25 × 0.25)
                                 = 57.42 × 1.009375
                                 = 57.96  →  58
```

**Result: Dispel magnitude 58 | duration 1 second (fixed) | 28 gp**

The Dispel quirk: when both Calcinator and Retort are present, the formula uses the product of their strengths (C×R) rather than summing them. Because C and R are both ≤ 1, the product is always smaller than either individual term — so using both pieces simultaneously yields a *weaker* result (58) than using the Retort alone (65). For any Dispel potion, leave the Calcinator in a chest. The full Apprentice set actually hurts you here.

---

## Query 10 — Oblivion: Ingredients with fewer than 4 effects

```sql
SELECT name, COUNT(effect) AS effect_count
FROM oblivion_alchemy_effects
WHERE effect IS NOT NULL
GROUP BY name
HAVING COUNT(effect) < 4
ORDER BY effect_count ASC, name ASC;
```

**13 ingredients, all with exactly 1 effect:**

| Ingredient | Source |
|-----------|--------|
| Ambrosia | Deepscorn Hollow (Vile Lair DLC) |
| Beating Heart | Shivering Isles |
| Chokeberry | Shivering Isles |
| Deformed Swamp Tentacle | Shivering Isles |
| Felldew | Shivering Isles (addictive — withdrawal effects) |
| Greenmote | Shivering Isles (addictive — overdose risk) |
| Heart of Order | Shivering Isles |
| Imp Fluid | Shivering Isles |
| Lichor | Shivering Isles |
| Mugwort Seeds | Rare wilderness flora |
| Poisoned Apple | Dark Brotherhood questline |
| Rat Poison | Found in homes and larders |
| Unicorn Horn | Unique creature drop |

No ingredients have 2 or 3 effects — the split is sharply binary: either the standard 4 effects, or a special 1-effect item from a DLC or quest. A 1-effect ingredient can only be combined with another ingredient that also carries that exact same effect; none of these 13 can be combined with each other.

---

## Query 11 — Skyrim: Restore Health with Physician perk

**Character:** Alchemy 50; perks: Alchemist rank 1/5 (skill 0, required as Physician prerequisite), Physician (skill 20)
**Ingredients:** Blue Mountain Flower + Wheat (both carry Restore Health, confirmed by database)

Note: In Skyrim all four ingredient effects are always visible, regardless of skill level. Skill affects potion strength only.

**Effect stats from database:**
```sql
SELECT DISTINCT base_cost, base_magnitude FROM skyrim_alchemy_effects
WHERE effect = 'Restore Health' AND base_cost IS NOT NULL;
-- base_cost: 0.5 | base_magnitude: 5.0
```

---

**Step 1 — Magnitude**

```
magnitude = 4 × BaseMag × (1 + 0.5 × Skill/100) × Alchemist × Physician
          = 4 × 5.0 × (1 + 0.5 × 50/100) × 1.2 × 1.25
          = 4 × 5.0 × 1.25 × 1.2 × 1.25
          = 20 × 1.875
          = 37.5  →  38 HP
```

**Step 2 — Value**

Restore Health is instant (NoDuration) → durationFactor = 1.

```
effectValue = floor(base_cost × (magnitude × durationFactor) ^ 1.1)
            = floor(0.5 × (38 × 1) ^ 1.1)
            = floor(0.5 × 38 ^ 1.1)
            = floor(0.5 × 54.69)
            = floor(27.34)
            = 27 gp
```

**Result: Restore Health 38 HP | 27 gp**

Perk cost: 2 points (Alchemist 1/5 and Physician). Minimum skill required: Alchemy 20 for Physician.

---

## Query 12 — Skyrim: Restore Health adding Benefactor

**Same character, same ingredients, adding Benefactor (skill 30, ×1.25 to beneficial potions).**

**Step 1 — Updated magnitude**

```
magnitude = 4 × 5.0 × 1.25 × 1.2 × 1.25 × 1.25
          = 37.5 × 1.25
          = 46.875  →  47 HP
```

**Step 2 — Updated value**

```
effectValue = floor(0.5 × 47 ^ 1.1)
            = floor(0.5 × 68.86)
            = floor(34.43)
            = 34 gp
```

**Result: Restore Health 47 HP | 34 gp**

**Comparison:**

| Perks active | Magnitude | Value |
|---|---|---|
| Alchemist 1/5 + Physician | 38 HP | 27 gp |
| + Benefactor | 47 HP | 34 gp |
| Gain | +24% | +26% |

Benefactor costs one additional perk point (at skill 30) and delivers a 9 HP increase — going from a potion that heals roughly half a low-level health bar to one that handles a meaningfully larger chunk of combat damage.

---

## Query 13 — Skyrim: Most expensive potion without Fortify Alchemy

Without the Fortify Alchemy loop, potion value is bounded by base skill and perks. The goal is to find the effect(s) with the highest `base_cost`, since `effectValue = floor(base_cost × (magnitude or duration factor)^1.1)`.

**Top base_cost effects from database:**

```sql
SELECT DISTINCT effect, base_cost, base_magnitude
FROM skyrim_alchemy_effects
WHERE base_cost IS NOT NULL
ORDER BY base_cost DESC LIMIT 5;
```

| Effect | base_cost | Type |
|--------|-----------|------|
| Paralysis | 500.0 | Poison, NoMagnitude |
| Invisibility | 100.0 | Potion, NoMagnitude |
| Waterbreathing | 30.0 | Potion, NoMagnitude |
| Frenzy | 15.0 | Poison, has magnitude+duration |
| Lingering Damage Health | 12.0 | Poison, has magnitude+duration |

Paralysis (base_cost 500) is in a class by itself — ten times higher than the next best effect.

---

**Finding the best 2-ingredient combination**

The pair must share Paralysis and ideally also share a high-value secondary effect. Querying which ingredients carry Paralysis and Damage Health simultaneously:

```sql
SELECT e1.name, e1.effect
FROM skyrim_alchemy_effects e1
WHERE e1.name IN (
    SELECT name FROM skyrim_alchemy_effects WHERE effect = 'Paralysis'
)
AND e1.effect IN ('Paralysis','Damage Health')
ORDER BY e1.name;
```

**Harrada** and **Imp Stool** are the two ingredients that share both Paralysis and Damage Health:

| Effect | Harrada position | Imp Stool position |
|--------|------------------|--------------------|
| Damage Health (3.0) | 1 | 1 |
| Paralysis (500.0) | 3 | 3 |

In Skyrim all effects are visible at any skill level, so both shared effects are always active. The result is a **poison** (all shared effects are harmful).

---

**Required character**

```sql
SELECT name, skill_level FROM skyrim_alchemy_perks
WHERE name IN ('Alchemist (1/5)','Alchemist (2/5)','Alchemist (3/5)',
               'Alchemist (4/5)','Alchemist (5/5)','Poisoner')
ORDER BY skill_level;
```

| Perk | Min skill | Effect |
|------|-----------|--------|
| Alchemist 1/5 | 0 | ×1.2 |
| Alchemist 2/5 | 20 | ×1.4 |
| Alchemist 3/5 | 40 | ×1.6 |
| Alchemist 4/5 | 60 | ×1.8 |
| Alchemist 5/5 | 80 | ×2.0 |
| Poisoner | 30 | ×1.25 to poisons |

**Required: Alchemy 100 (to reach Alchemist 5/5 at skill 80), 6 perk points total.**

At Alchemy 100: SkillMult = 1 + 0.5 × 100/100 = 1.5; Alchemist 5/5 = ×2.0; Poisoner = ×1.25.

---

**Calculation**

**Damage Health (NoDuration, base_mag = 2.0):**

```
magnitude = 4 × 2.0 × 1.5 × 2.0 × 1.25 = 30

effectValue = floor(3.0 × 30 ^ 1.1)
            = floor(3.0 × 42.17)
            = floor(126.51)
            = 126 gp
```

**Paralysis (NoMagnitude: magnitude = 1, base_cost = 500):**

Paralysis has a fixed magnitude of 1 (you are paralysed or you are not). What varies is duration. The base_duration of 1 second comes from the Skyrim Construction Set — this constant is not currently stored in the GameTools database.

```
duration = 4 × base_duration × SkillMult × Alchemist × Poisoner
         = 4 × 1 × 1.5 × 2.0 × 1.25
         = 15 seconds

effectValue = floor(500 × (duration / 10) ^ 1.1)
            = floor(500 × 1.5 ^ 1.1)
            = floor(500 × 1.587)
            = floor(793.5)
            = 793 gp
```

**Total poison value: 126 + 793 = 919 gp**

---

**Result: Harrada + Imp Stool → Damage Health 30 + Paralysis 15 seconds | ~919 gp**

This poison is applied to a weapon. The next successful hit delivers 30 total damage and renders the target unable to move for 15 seconds.

**Why Paralysis dominates:** Its base_cost of 500 means even a 10-second duration outscores the entire Damage Health + Damage Magicka combination. Every other effect in the game is noise by comparison.

**Caveat:** The Paralysis duration figure (15 seconds) relies on the base_duration constant from Skyrim game files, which is not yet in the GameTools database. The Damage Health figure (126 gp) is fully computed from database data alone. For a value computed entirely from the database using NoDuration effects only:

**Harrada + Human Heart** (share Damage Health and Damage Magicka):

| Effect | base_cost | magnitude | effectValue |
|--------|-----------|-----------|-------------|
| Damage Health | 3.0 | 30 | 126 gp |
| Damage Magicka | 2.2 | 45 | 144 gp |
| **Total** | | | **270 gp** |

```sql
SELECT e1.effect, e1.base_cost, e1.base_magnitude
FROM skyrim_alchemy_effects e1
JOIN skyrim_alchemy_effects e2 ON e1.effect = e2.effect
WHERE e1.name = 'Harrada' AND e2.name = 'Human Heart'
AND e1.effect IS NOT NULL;
-- Damage Health (3.0 / 2.0), Damage Magicka (2.2 / 3.0), Damage Magicka Regen (0.5 / 100.0)
```

(Damage Magicka Regen adds further value as a duration-based effect, but requires base_duration data not yet in the database to compute precisely.)

---

*All database queries run against `TES/database/gametools.sqlite3`. Formula constants for Morrowind EffectBaseCost and Skyrim Paralysis base_duration are sourced from Construction Set game files and UESP documentation, as the GameTools database does not currently store per-effect base values for Morrowind alchemy, and Skyrim base_duration is not yet in the effects table.*
