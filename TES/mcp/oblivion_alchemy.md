# Oblivion Alchemy — Rules and Mechanics

This document covers the game rules for Oblivion alchemy: crafting mechanics, skill mastery
levels, apparatus effects, the potion/poison distinction, and the full strength calculation
formulas. Use it alongside the `oblivion_alchemy_*` tool functions, which query the live database.

---

## Crafting Mechanics

Potions and poisons are crafted using a **Mortar and Pestle** (the only required apparatus) plus
up to four ingredients. Additional apparatus in your inventory further modify the
results.

- A **potion** is produced when at least one shared effect among the chosen ingredients is
  **positive**. Potions appear pink in inventory and are consumed by drinking.
- A **poison** is produced when all shared effects are **negative** (exclusively). Poisons appear
  green and are applied to the active weapon; the next hit delivers the poison.
- A "spoiled potion" (positive + negative effects) counts as a potion, not a poison, and
  **cannot** be applied to a weapon.
- Potion crafting **always succeeds** as long as matching ingredients are selected. There is no
  failure chance — only Morrowind has a skill-based failure rate.
- **Hidden effects are ignored.** Only effects your character's skill level can recognise
  (see Mastery Levels below) are used when creating a potion. This differs from Morrowind,
  where hidden effects still affect the final potion.
- The **strength** of a potion is not influenced by which specific ingredients are used, only by
  the effects those ingredients share. A Pumpkin + Watermelon Restore Fatigue potion has the same
  magnitude and duration as a Flour + Apple Restore Fatigue potion (only weight differs).
- Using **more than two** ingredients that share the same effect does not increase that effect's
  strength. The extra ingredient contributes no additional magnitude or duration.
- Up to **eight effects** can be present in a single potion or poison simultaneously.
- You **cannot make potions when enemies are nearby**.
- Potions made from stolen ingredients are **not flagged as stolen**.

---

## Mastery Levels

Your Alchemy skill level primarily determines which ingredient effects your character can
**recognise and use** when crafting. Each ingredient has up to four effects, listed in order; only
the effects up to your recognition limit count toward crafting.

| Skill range | Rank | Effects recognised per ingredient |
|-------------|------|----------------------------------|
| 0 – 24 | Novice | First effect only |
| 25 – 49 | Apprentice | First two effects |
| 50 – 74 | Journeyman | First three effects |
| 75 – 99 | Expert | All four effects |
| 100 | Master | All four effects; plus can brew from a **single ingredient** |

**Practical implication:** if the shared effect you want is the second effect of an ingredient,
your character cannot use it in a potion until Alchemy reaches 25. If it is the third effect, you
need Alchemy ≥ 50, and so on. This can turn previously available poison recipes into unavailable
ones as skill increases unlock positive effects that were previously hidden.

**Master special rule:** At Alchemy 100, a single ingredient can be used to create a potion. Only
the ingredient's **first effect** is added into that potion — no additional effects. This is unique
to Oblivion; neither Morrowind nor Skyrim allow single-ingredient crafting.

---

## Effective Alchemy

Potion strength is determined by **Effective_Alchemy**, not raw Alchemy skill:

```
Effective_Alchemy = Alchemy_Skill + 0.4 * (Luck - 50)
```

- Only **base (unmodified)** Alchemy and Luck are used. Active magical effects — Fortify Alchemy,
  Drain Alchemy, Fortify Luck potions, spells, or enchanted items — have no effect on potion
  strength.
- The sole exception is the **Altar of Alchemical Brilliance** at Frostcrag Spire (DLC), which
  does count; but Effective_Alchemy is still capped at 100.
- Minimum Effective_Alchemy = 0, maximum = 100.
- A character with Alchemy 75 and Luck 70 has Effective_Alchemy = 75 + 0.4×(70−50) = 75 + 8 = 83.

---

## Apparatus

The **Mortar and Pestle** is the only required piece of apparatus. The others (Retort, Calcinator,
Alembic) modify strength and are optional. All apparatus comes in five quality grades.

### Apparatus strength values

| Grade | Strength |
|-------|----------|
| Novice | 0.10 |
| Apprentice | 0.25 |
| Journeyman | 0.50 |
| Expert | 0.75 |
| Master | 1.00 |

### What each apparatus does

**Mortar and Pestle** — Required for any alchemy. It also adds virtual Alchemy skill:
`MortarPestle_Strength × 25` is added to Effective_Alchemy in every strength calculation
(Novice: +2.5, Apprentice: +6.25, Journeyman: +12.5, Expert: +18.75, Master: +25).

**Retort** — Increases magnitude and duration of **positive effects only**. Has no effect on
negative effects or poisons.

**Calcinator** — Increases magnitude and duration of **all effects**, both positive and negative.

**Alembic** — Intended to reduce the magnitude and duration of **negative side effects** in
potions (not poisons). In practice, it has significant quirks (see Strength Calculation). An
Alembic has no intended effect on poisons, but its presence in your inventory still alters the
calculation for them through an implementation bug.

---

## Potion Price

```
Price = floor((Effective_Alchemy + MortarPestle_Strength × 25) × 0.45)
```

- Prices range from **3 to 56 gold**.
- Only Alchemy skill, Luck, and Mortar and Pestle quality affect price. Number of ingredients,
  ingredient cost, number of effects, and quality of other apparatus have no effect.
- **Price is locked in** the first time you create a specific potion (same name + same effects +
  same strength). All subsequent identical potions share that price. To force a recalculation,
  rename the potion, change your Mortar and Pestle, or level up Alchemy mid-session.
- Potions with no variable strength (e.g., Cure Disease) never recalculate on their own —
  renaming is the only option.

---

## Potion Weight

Weight = average weight of the ingredients used. Like price, **weight is locked in** the first
time a specific potion is made. Using heavy ingredients for the first batch of a given potion will
make all subsequent identical potions heavy, even if later batches use lighter ingredients. Best
practice: always use your lightest ingredients first for any new recipe.

---

## Potion Strength Calculation

### Step 1 — Effective Magicka Cost (virtual)

```
Magicka_Cost = Effective_Alchemy + MortarPestle_Strength × 25
```

This is the budget used in all subsequent formulas. Higher is always better.

### Step 2 — Base magnitude and duration

The calculation differs by **effect type**. Check which category the effect falls into before
choosing a formula.

#### Most Effects (variable magnitude and duration)

The vast majority of effects fall here.

```
Base_Mag = (Magicka_Cost / (Effect_Base_Cost / 10 × 4)) ^ (1 / 2.28)
Base_Dur = 4 × Base_Mag
```

Base duration is always exactly four times base magnitude for these effects.

#### Duration-Only Effects (magnitude always = 1)

These six effects have fixed magnitude of 1; only duration varies:
**Invisibility, Night-Eye, Paralyze, Silence, Water Breathing, Water Walking**

```
Base_Dur = Magicka_Cost / (Effect_Base_Cost / 10)
```
(Base_Mag is always 1.)

#### Magnitude-Only Effect (duration always = 1)

Only **Dispel** falls here. Duration is always 1; only magnitude varies.

```
Base_Mag = (Magicka_Cost / (Effect_Base_Cost / 10)) ^ (1 / 1.28)
```

### Step 3 — Apparatus modifiers (Master Equations)

After calculating Base_Mag and Base_Dur, apply the apparatus factors:

```
Magnitude = Base_Mag × (1 + Calc_Fac × Calcinator_Strength
                          + Ret_Mag_Fac × Retort_Strength
                          − Alem_Fac × Alembic_Strength)

Duration  = Base_Dur × (1 + Calc_Fac × Calcinator_Strength
                          + Ret_Dur_Fac × Retort_Strength
                          − Alem_Fac × Alembic_Strength)
```

**Factor table** (Strength values are 0.10 / 0.25 / 0.50 / 0.75 / 1.00 for Novice–Master):

| Factor | Most Effects | Duration-Only | Magnitude-Only (Dispel) |
|--------|-------------|---------------|------------------------|
| `Calc_Fac` | 0.35 | 0.25 | 0.30 |
| `Ret_Mag_Fac` | 0.50 | — | 0.50 |
| `Ret_Dur_Fac` | 1.00 | 0.35 | — |
| `Alem_Fac` | 2.00 | 2.00 | 2.00 (always 0 in practice) |

**Factor activation rules:**
- `Ret_Mag_Fac` and `Ret_Dur_Fac` = **0 for negative effects** (Retort never helps poisons or
  negative side effects).
- `Alem_Fac` = **0 for positive effects** and **0 for all poisons** (Alembic only affects
  negative side effects in potions — in theory).

**Final rounding:** 0.5 rounds up; 0.49 rounds down. Minimum magnitude = 1, minimum duration = 1.

### Exceptions to the Master Equations

Two situations require substituting different factors.

**Exception 1 — Positive effects with both Calcinator AND Retort simultaneously:**

For magnitude only, replace `Calc_Fac` (0.35) with `Calc_Mag_Fac` (1.40):

```
Magnitude = Base_Mag × (1 + 1.4 × Calcinator_Strength + 0.5 × Retort_Strength)
Duration  = Base_Dur × (1 + 0.35 × Calcinator_Strength + 1.0 × Retort_Strength)
```

**Exception 2 — Negative effects in potions with Alembic present:**

The Calcinator factor appears twice (the Alembic triggers a double-application):

```
Magnitude = Base_Mag × (1 + 0.35×C) × (1 + 0.35×C − 2×A)
Duration  = Base_Dur × (1 + 0.35×C) × (1 + 0.35×C − 2×A)
```

where C = Calcinator_Strength and A = Alembic_Strength.

For **poisons** (all-negative concoctions), `Alem_Fac` is forced to 0, so:
```
Magnitude = Base_Mag × (1 + 0.35×C) × (1 + 0.35×C)
Duration  = Base_Dur × (1 + 0.35×C) × (1 + 0.35×C)
```
This means merely having an Alembic in your inventory — regardless of quality — inflates poison
strength by squaring the Calcinator factor. Do not carry an Alembic if you want predictable
poisons.

### Full expanded multiplier table

Using C = Calcinator_Strength, R = Retort_Strength, A = Alembic_Strength:

| Scenario | Magnitude | Duration |
|---|---|---|
| Most positive — Calcinator or Retort | 1 + 0.35C + 0.5R | 1 + 0.35C + R |
| Most positive — Calcinator AND Retort | 1 + 1.4C + 0.5R | 1 + 1.4C + R |
| Magnitude-Only (Dispel) — Calcinator or Retort | 1 + 0.3C + 0.5R | 1 (fixed) |
| Magnitude-Only (Dispel) — Calcinator AND Retort | 1 + 0.15 × C × R | 1 (fixed) |
| Duration-Only — any apparatus | 1 (fixed) | 1 + 0.25C + 0.35R − 2A |
| Most negative — no Alembic | 1 + 0.35C | 1 + 0.35C |
| Most negative — Alembic present (potion side effects) | (1 + 0.35C)(1 + 0.35C − 2A) | (1 + 0.35C)(1 + 0.35C − 2A) |

---

## Apparatus Quirks and Traps

**Novice Alembic can backfire.** With a Novice Alembic (strength 0.10) and an Expert or Master
Calcinator, the formula `(1 + 0.35C)(1 + 0.35C − 2×0.10)` can yield a multiplier greater than 1,
meaning the Alembic actively strengthens the negative side effect rather than reducing it.

**Expert Alembic is the ceiling.** With an Expert Alembic (strength 0.75), `1 + 0.35C − 2×0.75`
evaluates to ≤ 0 for any Calcinator, so the inner term hits the minimum of 1. All negative side
effects are reduced to magnitude = duration = 1. A Master Alembic (strength 1.00) provides no
additional benefit.

**Duration-Only effects (Paralyze, Silence) have no Alembic quirk.** The Duration-Only formula
uses the standard `−2A` term (not the double-application), so the Alembic always decreases
duration of these negative effects correctly.

**Dispel (Magnitude-Only) is weakened by Calcinator when Retort is also present.** With both
Calcinator and Retort, the Dispel formula uses `1 + 0.15 × C × R` (factors multiplied, not added).
Since C and R are both ≤ 1, this is smaller than using either alone. The strongest Dispel potions
are made with a **Retort only** (multiplier = 1 + 0.5×R).

---

## Skill Progression

- Alchemy XP: **+5** per potion with 2 or more ingredients; **+0.5** per non-food ingredient
  eaten (Wortcraft).
- One-ingredient potions (possible below level 100 with boosting items, or at Master) give **no**
  XP.
- You only need a Mortar and Pestle in your inventory to gain skill — no lab bench required.
- Farms are the best source of free ingredients for rapid skill leveling. Food ingredients from
  crops can be taken without incurring a steal flag.
- Potions and poisons sell for profit, simultaneously training both Alchemy and Mercantile.

---

## Potion vs Poison Summary

| | Potion | Poison |
|---|---|---|
| Colour in inventory | Pink | Green |
| Effect composition | At least one positive effect | All effects negative |
| On activation | Drunk by character | Applied to active weapon |
| Alembic reduces side effects | Yes (with quirks) | No (Alembic actually hurts — see above) |
| Retort boosts positive effects | Yes | No (Retort has no effect) |

---

## What the Database Tools Cover

| Question | Tool to use |
|----------|-------------|
| What effects does ingredient X have? | `oblivion_alchemy_ingredient(name)` |
| Which ingredients have effect X? | `oblivion_alchemy_find_by_effect(effect)` |
| Given my ingredients, what can I combine? | `oblivion_alchemy_combos(ingredients)` |
| What are all possible effects? | `oblivion_alchemy_list_effects()` |
| Search for an ingredient by partial name | `oblivion_alchemy_search(query)` |

The tools return live data from the SQLite database. This document provides the rules context
needed to interpret results and answer questions the database alone cannot answer (apparatus
interactions, strength formulas, Effective_Alchemy calculation).
