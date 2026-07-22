# Morrowind Alchemy — Rules and Mechanics

This document covers the game rules for Morrowind alchemy: crafting mechanics, effect visibility,
the success chance formula, apparatus, potion strength and duration formulas, and apparatus
modifiers. Use it alongside the `morrowind_alchemy_*` tool functions, which query the live database.

---

## Key Differences from Oblivion and Skyrim

Before the details, three things set Morrowind alchemy apart:

1. **Failure chance.** Potion creation can fail and waste the ingredients. Oblivion and Skyrim
   always succeed when matching ingredients are selected.
2. **No poisons.** Morrowind has no mechanism to apply a negative-effect concoction to a weapon.
   Negative effects in a potion only hurt the character who drinks it. The entire purpose of
   negative effects is therefore as an **impediment to be managed**, not a combat tool. Choosing
   ingredients should focus on minimising unwanted side effects.
3. **Hidden effects can be used.** A character can mix a potion using an effect they cannot yet
   see on the ingredient label. The Alchemy screen will reveal the shared hidden effect when two
   matching ingredients are selected. Oblivion ignores hidden effects entirely; only Morrowind
   allows this.

---

## Crafting Mechanics

Potions are mixed at the inventory screen by dragging a Mortar and Pestle onto the character
portrait. Only the Mortar and Pestle is strictly required; the other apparatus pieces are optional.

- You need at least **two ingredients** that share at least one effect. Up to **four ingredients**
  can be combined.
- Any effect shared by **two or more** of the selected ingredients is included in the potion.
- **Hidden effects count.** If two ingredients share an effect you cannot see, the Alchemy screen
  still shows that effect in the result preview. This is how low-skill characters can discover
  ingredient effects even before they can see them in item descriptions.
- Every potion produced affects only the **player character** — there is no weapon-application
  mechanic. A potion with all negative effects can be mixed and sold for profit, but confers no
  combat advantage.
- **Eating an ingredient raw** gives a very weak dose of its first effect and advances Alchemy
  skill at one-quarter the rate of mixing potions.
- Only a **successful** potion creation advances Alchemy skill. Failed attempts waste the
  ingredients and give no XP.

---

## Effect Visibility

How many of an ingredient's effects are shown in its item description depends on Alchemy skill:

| Alchemy skill | Effects visible |
|---------------|-----------------|
| 0 – 14 | None (all shown as "?") |
| 15 – 29 | First effect |
| 30 – 44 | First two effects |
| 45 – 59 | First three effects |
| 60 – 100 | All four effects |

Ingredients with fewer than four effects always show "?" placeholders for the missing slots, so
you can tell how many real effects an ingredient has regardless of skill level.

**Effect visibility does not gate crafting.** You can brew a potion using a hidden (invisible)
effect as long as two of your selected ingredients share it. The result preview in the Alchemy
screen will reveal the effect name even if your skill would normally hide it.

---

## Success Chance

```
SuccessChance = Alchemy + (Intelligence / 10) + (Luck / 10)
```

- This value is treated as a percentage. At 60, there is a 60 % chance of success.
- At or above 100 the attempt always succeeds.
- A failure wastes all ingredients used and gives no skill XP.
- Only the character's base Alchemy, Intelligence, and Luck are used (unmodified by active
  spell effects, in the same vein as Oblivion's Effective_Alchemy).

A new alchemist with Alchemy 30, Intelligence 50, Luck 40 has:
30 + 5 + 4 = 39 → 39 % success chance. Investing in Intelligence and Luck matters early.

---

## Apparatus

### Required

**Mortar and Pestle** — The only apparatus required to mix a potion. Its quality (`MortarQuality`)
appears in every strength and duration formula. The price and weight of the result are not affected
by the presence or absence of other apparatus.

### Optional

**Retort** — Increases the strength and duration of **positive effects** only. If the ingredients
share no positive effects the Retort has no effect.

**Calcinator** — Increases the strength and duration of **all effects**, positive and negative.

**Alembic** — Reduces the strength and duration of **negative effects** only. If the ingredients
share no negative effects the Alembic has no effect. Unlike in Oblivion, the Alembic in Morrowind
works correctly and unambiguously: it always reduces negative side effects, and using it together
with a Calcinator is strictly better than using the Calcinator alone for minimising negative side
effects.

### Apparatus quality values

The same five quality grades apply to all apparatus types. (Secret Master items are only
accessible on PC via the console or Construction Set mods.)

| Grade | Quality |
|-------|---------|
| Apprentice | 0.5 |
| Journeyman | 1.0 |
| Master | 1.2 |
| Grandmaster | 1.5 |
| Secret Master | 2.0 |

---

## Potion Strength and Duration Formulas

Define the shared skill factor used in every formula:

```
SkillFactor = Alchemy + (Intelligence / 10) + (Luck / 10)
```

(This is the same expression as the SuccessChance — success chance and potion quality scale
together.)

### Base values (Mortar and Pestle only)

```
Base_Strength = SkillFactor × MortarQuality / (3 × EffectBaseCost)
Base_Duration = SkillFactor × MortarQuality / EffectBaseCost
```

Note that Base_Duration = 3 × Base_Strength for every standard effect.

### Apparatus modifiers for **positive** effects

Apply the following additional adjustment to both Base_Strength and Base_Duration:

| Apparatus in use | Adjustment |
|------------------|-----------|
| Retort only | + RetortQuality |
| Calcinator only | + CalcinatorQuality |
| Both Retort and Calcinator | + CalcinatorQuality + (RetortQuality × 2) |

Using both is always better than using either alone.

### Apparatus modifiers for **negative** effects

Apply the following adjustment to both Base_Strength and Base_Duration:

| Apparatus in use | Adjustment |
|------------------|-----------|
| Alembic only | ÷ (AlembicQuality + 1) |
| Calcinator only | + round(CalcinatorQuality), minimum +1 |
| Both Alembic and Calcinator | ÷ (AlembicQuality × 2 + CalcinatorQuality × 3) |

**Key point — Alembic + Calcinator:** In Morrowind, using both an Alembic and a Calcinator on
negative effects is strictly better than either alone. The Calcinator does not fight the Alembic;
instead, it amplifies the Alembic's reduction by increasing the divisor further (the divisor grows
to AlembicQuality × 2 + CalcinatorQuality × 3, which is always larger than AlembicQuality + 1
alone). This is the opposite of the confusing Oblivion behaviour.

### Rounding

Round the final strength and duration to the nearest whole number; 0.5 rounds up.

### Special effects (magnitude-only or duration-only)

Five effects have only a magnitude or only a duration:
**Dispel, Invisibility, Paralyze, Water Breathing, Water Walking**

The base formulas are the same (Base_Strength and Base_Duration above). The apparatus modifiers
differ:

**For positive special effects (Dispel, Invisibility, Water Breathing, Water Walking):**

| Apparatus in use | Adjustment |
|------------------|-----------|
| Retort only | × (RetortQuality + 0.5) |
| Calcinator only | × (CalcinatorQuality + 0.5) |
| Both Retort and Calcinator | + 2/3 × (RetortQuality + CalcinatorQuality) + 0.5 |

Note: the additive combined formula is usually **less effective** than using either piece alone
(because the multiplier > 1 produces a larger result than the additive form for typical quality
values).

**For the negative special effect (Paralyze only):**

| Apparatus in use | Adjustment |
|------------------|-----------|
| Calcinator only | × (CalcinatorQuality + 0.5) |
| Alembic present (with or without Calcinator) | Use the normal negative-effect formula above |

---

## Potion Value and Weight

```
Value = SkillFactor × MortarQuality
```

- Value is **not** affected by the presence or quality of Retort, Alembic, or Calcinator.
- Value is **not** affected by the type of effects (Drain Strength and Reflect potions sell for
  the same price at the same skill level). This means all effects are equally profitable for
  levelling Alchemy through selling.
- **Weight** = average weight of the ingredients used, rounded down.

---

## Skill Progression

- XP is gained only when a potion is **successfully** created; failed attempts give nothing.
- Eating an ingredient raw increases Alchemy at one-quarter the rate of a successful potion mix.
- Higher skill increases both success rate (SuccessChance) and potion strength (Base_Strength,
  Base_Duration) simultaneously, because both formulas share SkillFactor.
- Intelligence and Luck each contribute one-tenth of their value to SkillFactor and
  SuccessChance, so both attributes are worth investing in for serious alchemists.

---

## What the Database Tools Cover

| Question | Tool to use |
|----------|-------------|
| What effects does ingredient X have? | `morrowind_alchemy_ingredient(name)` |
| Which ingredients have effect X? | `morrowind_alchemy_find_by_effect(effect)` |
| Given my ingredients, what can I combine? | `morrowind_alchemy_combos(ingredients)` |
| What are all possible effects? | `morrowind_alchemy_list_effects()` |
| Search for an ingredient by partial name | `morrowind_alchemy_search(query)` |

The tools return live data from the SQLite database. This document provides the rules context
needed to interpret results and answer questions the database alone cannot answer (success chance,
strength formulas, apparatus interactions).
