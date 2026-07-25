# Skyrim Enchanting — Rules and Mechanics

This document covers Skyrim enchanting: how enchantments are placed on items, how magnitude is
computed, how weapon charges work, and how to interpret the data returned by the MCP tools.

---

## Unofficial Skyrim Patch — Must Ask

The **Unofficial Skyrim Legendary Edition Patch** (Nexus mod 71214) and the **Unofficial Skyrim
Special Edition Patch** (Nexus mod 266) make identical changes to the enchantment magnitude
formula. These patches are widely used but not universal.

**If a user asks about enchantment magnitudes, maximum power, or anything that requires applying
the formula, and they have not stated whether they have the patch, ask them before computing.**

The patch changes how Fortify Enchanting potions interact with the skill calculation:

- **With patch (USP)**: potion effect is a separate linear multiplier; base skill only feeds the
  quadratic term.
- **Without patch (vanilla)**: potion effect is folded into an "effective skill" that then goes
  through the quadratic formula, making potions exponentially more powerful.

Both paths share the same perk and soul multipliers; only the treatment of potions differs.

---

## Core Rules

**1. Enchantment limit per item.** An item can hold exactly one enchantment unless the character
has the **Extra Effect** perk (requires Enchanting 100). Extra Effect allows two enchantments on
one item. Each effect's magnitude is computed fully independently — there is no reduction for
combining two effects.

**1a. Two-effect calculation.** Because effects are independent, a sword with Fire Damage and Frost
Damage enchantments gets the full magnitude of each. For weapon charges, the Charges Per Use of
both effects are simply **added** together — two effects means the charge pool is consumed at the
combined rate of both.

**2. Items can only be enchanted once.** An already-enchanted item cannot receive additional
enchantments, even if the character has Extra Effect. Almost no exceptions exist (a few are bugs).
Players who want a differently-enchanted version must find an unenchanted base item.

**3. Apparel enchantments are passive and permanent while worn.** They consume no charges, require
no soul gems to maintain, and are always active as long as the piece is equipped. There is no
charge pool on apparel.

**3a. Weapon enchantments consume charges per strike.** When the charge pool reaches zero, the
enchantment stops activating but the weapon can still be used as a normal weapon. To restore
charges:
- Open inventory, drag a filled soul gem onto the weapon. The soul is consumed; the gem
  becomes empty. One soul point = one charge point restored.
- The **Soul Siphon** perk (Enchanting 40): death blows on creatures automatically trap 5% of
  the soul into the equipped weapon's charge pool.

**3b. Soul Squeezer perk (Enchanting 20):** Soul gems provide more magicka when recharging
weapons. This amplifies the charge restored when using a soul gem to recharge manually.

---

## Apparel: Enchantment Magnitude Formula

### With Unofficial Patch (USP)

```
net_magnitude = floor(
    base_magnitude
    × soul_multiplier
    × skill_multiplier
    × (1 + potion_effect)
    × (1 + enchanter_perk)
    × (1 + specific_perk)
    × (1 + seeker_of_sorcery)
)
```

where `skill_multiplier` depends only on base skill (no buffs folded in):

```
skill_multiplier = 1 + (skill / 100) × (skill / 100 − 0.14) / 3.4
```

### Without Unofficial Patch (vanilla)

```
net_magnitude = floor(
    base_magnitude
    × soul_multiplier
    × skill_multiplier1
    × (1 + enchanter_perk)
    × (1 + specific_perk)
    × (1 + seeker_of_sorcery)
)
```

Note: `potion_effect` is **absent as a separate factor** — instead it is folded into the
effective skill used to compute `skill_multiplier1`:

```
effective_skill  = skill + potion_magnitude + ahzidal_genius + haunting_gift
skill_multiplier1 = 1 + (effective_skill / 100) × (effective_skill / 100 − 0.14) / 3.4
```

### Definitions

| Symbol | Meaning |
|--------|---------|
| `base_magnitude` | The value shown in the enchanting UI when hovering over the enchantment without a soul selected; this is the magnitude at Grand soul, skill 0, no perks. Not stored in the DB — read from the in-game enchanting table hover. |
| `skill` | The character's base Enchanting skill level (0–100; up to 110 with Ahzidal's Genius active). |
| `potion_effect` | Fractional bonus from a Fortify Enchanting potion (e.g., a +32% potion → `potion_effect = 0.32`). Used only in the patched formula as a separate multiplier. |
| `potion_magnitude` | Same potion expressed as the raw magnitude value (e.g., +32% → `potion_magnitude = 32`). Used in vanilla effective_skill only; equals `potion_effect × 100`. |
| `ahzidal_genius` | 10 if 4+ pieces of Ahzidal's armor set are equipped (Dragonborn DLC), else 0. Folded into effective_skill in vanilla only. |
| `haunting_gift` | Sum of all Haunting Gift effect stacks × 10 (Necromantic Grimoire CC). Folded into effective_skill in vanilla only. |
| `enchanter_perk` | See Perk Modifiers table. One value for all five Enchanter ranks (0.2 per rank: 0.2 / 0.4 / 0.6 / 0.8 / 1.0). |
| `specific_perk` | Additional +0.25 from Fire Enchanter, Frost Enchanter, Storm Enchanter, Insightful Enchanter, or Corpus Enchanter (see Perk Modifiers). |
| `seeker_of_sorcery` | +0.1 from the Seeker of Sorcery power (Dragonborn DLC). Binary: 0.1 or 0. |

### Soul Multiplier

| Soul Class | Multiplier | Capacity |
|------------|-----------|----------|
| Grand      | 1         | 3000     |
| Greater    | 2/3       | 2000     |
| Common     | 1/3       | 1000     |
| Lesser     | 1/6       | 500      |
| Petty      | 1/12      | 250      |

Using a Petty soul for an apparel enchantment yields only 1/12 of the Grand-soul magnitude.

### Typical result

At skill 100, no potions, no perks: `skill_multiplier ≈ 1.253`. Maximum possible natural
multiplier (skill 100, Enchanter 5/5, applicable specific perk, Grand soul, Seeker of Sorcery):
approximately **3.132×** base_magnitude (same for both patched and unpatched without potions).
With a Fortify Enchanting potion and no exploits, the maximum is approximately **4.22×**.

---

## Weapons: Maximum Magnitude Formula

For weapons the player selects the magnitude anywhere from 1 to a computed maximum. Higher
magnitude means fewer uses per charge pool.

### Maximum Magnitude

```
max_magnitude = floor(
    floor(
        base_magnitude
        × skill_multiplier
        × (1 + potion_effect)
        × (1 + enchanter_perk)
        × (1 + specific_perk)
        × (1 + seeker_of_sorcery)
    )
    × (1 + elemental_destruction_perk)
)
```

`skill_multiplier` follows the same patched/unpatched distinction as apparel. The elemental
Destruction perk modifier is applied in a separate outer `floor()` — see Special Interactions.

If the soul is too small to give even 1 use at maximum magnitude, the game auto-reduces max
magnitude to ensure at least 1 use.

### Charges Per Use (at chosen magnitude)

```
charges_per_use = 3 × (base_cost × magnitude / max_magnitude)^1.1 × (1 − sqrt(skill / 200))
```

At **maximum magnitude** (`magnitude = max_magnitude`) this simplifies to:

```
charges_per_use_at_max = 3 × base_cost^1.1 × (1 − sqrt(skill / 200))
```

`base_cost` here is `skyrim_enchant_weapons.base_cost` in the database (the "Base Cost" column
from the UESP enchanting effects table).

### Net Number of Uses

```
net_uses = soul_charge_capacity / charges_per_use
```

Both `soul_charge_capacity` and `base_cost` are in the database. With these two values plus skill
level, the LLM can compute approximate net uses without knowing base_magnitude.

### Key scaling facts

- At skill 15: net use skill multiplier ≈ 1.38×
- At skill 100: net use skill multiplier ≈ 4.375×
- At skill 110 (Ahzidal's Genius): net use skill multiplier ≈ 5.21×
- Skill must never exceed 200 in the formula (charges per use would become 0 or imaginary);
  Fortify Enchanting potions intentionally add to magnitude, not to skill, to avoid this.

### Two-effect weapons

With Extra Effect, both enchantments' `charges_per_use` values are added together to get the
combined drain rate per strike. The charge pool is still from the single soul used.

---

## Soul Gems

Soul gem capacities (queryable via `skyrim_enchant_soul_gems()`):

| Gem | Capacity | Trappable |
|-----|----------|-----------|
| Petty Soul Gem | 250 | Creature souls, level < 4 |
| Lesser Soul Gem | 500 | Creature souls, level < 16 |
| Common Soul Gem | 1000 | Creature souls, level < 28 |
| Greater Soul Gem | 2000 | Creature souls, level < 38 |
| Grand Soul Gem | 3000 | Any creature soul (not humanoids) |
| Black Soul Gem | 3000 | Any soul including humanoids (black souls) |
| Azura's Star | 3000 | Any creature soul; reusable (never consumed) |
| The Black Star | 3000 | Any soul; reusable (the lore says humanoid-only but it accepts any) |

Black souls (humanoids — most NPCs, vampires, etc.) are always Grand-level and require a
Black Soul Gem or The Black Star. NPCs in `skyrim_enchant_souls` with soul_size = 3000 are
black souls (the column type is INTEGER).

Soul Gem Fragments and Warped Soul Gems have capacity 0 and cannot trap souls.

---

## Perk Modifiers

All modifiers are additive within the formula's `(1 + ...)` terms, not chained.

| Perk | Skill | Condition / Effect | `enchanter_perk` contribution |
|------|-------|--------------------|-------------------------------|
| Enchanter (1/5) | 0 | All enchantments | +0.20 |
| Enchanter (2/5) | 20 | All enchantments | +0.40 |
| Enchanter (3/5) | 40 | All enchantments | +0.60 |
| Enchanter (4/5) | 60 | All enchantments | +0.80 |
| Enchanter (5/5) | 80 | All enchantments | **+1.00** (double) |

The `enchanter_perk` value = 0.2 × (number of Enchanter ranks taken).

| Perk | Skill | `specific_perk` contribution | Applies to |
|------|-------|------------------------------|-----------|
| Fire Enchanter | 30 | +0.25 | Fire Damage weapon enchantments |
| Frost Enchanter | 40 | +0.25 | Frost Damage weapon enchantments |
| Storm Enchanter | 50 | +0.25 | Shock Damage weapon enchantments |
| Insightful Enchanter | 50 | +0.25 | Skill-boosting apparel enchantments (Fortify X skill) |
| Corpus Enchanter | 70 | +0.25 | Health, magicka, and stamina apparel enchantments |

Only one `specific_perk` applies per enchantment (but Chaos Damage can accumulate up to three
elemental-Destruction modifiers — see Special Interactions).

| Power / Effect | Modifier |
|----------------|---------|
| Seeker of Sorcery (Dragonborn DLC Black Book power) | `seeker_of_sorcery = 0.1` (+10% all enchantments) |

---

## Special Interactions

**Elemental Destruction perks and weapon enchantments.** Fire Enchanter, Frost Enchanter, and
Storm Enchanter each give +25% to their respective weapon enchantment. These are in addition to
the generic Enchanter perk. The elemental Destruction skill perks (Augmented Flames, Augmented
Frost, Augmented Shock) also apply to the corresponding weapon enchantments — the weapon formula
wraps the elemental Destruction modifier in a separate outer floor():

```
max_magnitude = floor(floor(... × (1 + enchanting_modifiers)) × (1 + elemental_destruction_perk))
```

Augmented Flames / Frost / Shock each provide +0.25 (rank 1) or +0.50 (rank 2).

**Chaos Damage** (Dragonborn DLC) can stack Fire Enchanter, Frost Enchanter, and Storm Enchanter
(all three `specific_perk` values add) plus up to three Augmented ranks, potentially giving a
very large multiplier.

**Necromage + Vampire.** If the player is a vampire with the Necromage perk (Restoration 70),
all self-applied enchantments are treated as if they are applied to an "undead" target (the
player). This boosts enchantment magnitude by 25% and duration by 50%. This is widely regarded
as a bug but is present in unpatched vanilla.

**Damage Stamina + Fire perks (vanilla only).** Due to an erroneous keyword in unpatched vanilla,
the Damage Stamina enchantment is affected by both Fire Enchanter and Augmented Flames. The
Unofficial Patch 1.3.2 fixes this.

**Stability (Alteration perk).** Increases the duration of Paralyze weapon enchantment effects.

**Kindred Mage / Animage (Illusion perks).** Increase the effective level cap of Fear weapon
enchantments against humanoids and animals respectively.

**Total charge capacity and magic-school skill.** The total number of uses for a weapon
enchantment is increased by high skill in the relevant magic school (and by cost-reducing gear),
but **not** by the Novice through Master spell-cost perks.

---

## Maximizing Enchantment Power

The alchemy–enchanting loop produces the strongest possible enchantments without glitches. Full
optimisation requires Dragonborn DLC; the core loop works without it.

**Prerequisites:**
- Enchanting 100, Alchemy 100, all Enchanter perks, relevant specific perk
- (Dragonborn) Ahzidal's armor set, Seeker of Shadows / Seeker of Sorcery Black Book powers,
  Conjure Haunting Spirit from the Necromantic Grimoire (CC optional)

**Core loop:**
1. Acquire **Seeker of Shadows** (boosts Alchemy 10%).
2. Equip five pieces of Fortify Alchemy apparel (falmer helmet + circlet, necklace, ring, gloves).
   _Note: wearing both a falmer helmet and a circlet simultaneously is a known bug._
3. (Optional) Cast Conjure Haunting Spirit and kill the spirit for Haunting Gift (+10 to alchemy
   effective skill in vanilla, or linear +10% in patched).
4. Craft a **Fortify Enchanting** potion (and optionally a Fortify Restoration potion).
   Using Dreugh Wax or Stoneflower Petals (Rare Curios CC) doubles the effect.
5. Acquire **Seeker of Sorcery** (+10% enchantments).
6. If available, equip Ahzidal's set.
7. Drink the Fortify Enchanting potion in front of the enchanting table.
8. Enchant five new pieces of apparel with stronger Fortify Alchemy enchantments.
9. Repeat from step 1 with the new stronger gear. This has diminishing returns.

**Maximum achievable (no bugs/exploits, no CC):** approximately +40% Fortify Enchanting potion,
giving an overall enchanting multiplier of about 4.22× base magnitude.

**With the falmer-helmet+circlet bug and Necromage+Vampire:** the Fortify Enchanting potion can
reach approximately +61% (requires verification with Haunting Gift stacking).

---

## Enchanting for Profit

Weapon enchantments generally yield more gold per soul used than apparel enchantments. Profit is
inversely proportional to base uses — enchantments with fewer base uses (higher base_cost per
unit magnitude) fetch more gold.

**Most profitable weapon enchantments (descending order):**
1. Banish (base_cost = 113) — by far the highest-value weapon enchantment
2. Paralyze (base_cost = 34)
3. Absorb Health (base_cost = 31)

For apparel mass-enchanting, the most profitable options at petty soul level are Waterbreathing
and Muffle — these have no magnitude or duration, so a petty soul produces the same effect and
value as a grand soul. Fortify Sneak surpasses them with lesser souls or better.

Use larger soul gems preferentially on apparel (price difference from soul quality is
proportionally greater for apparel than weapons).

---

## Notes: Effect Availability by Level

Most enchantments are available from level 1. Exceptions:
- Resist Poison: level 5
- Resist Disease: level 10
- Muffle: level 11
- Fortify Healing Rate, Fortify Stamina Regen: level 16
- Banish, Paralyze: level 22

---

## What the Database Tools Cover

| Question | Tool |
|----------|------|
| What are the Enchanting perks, skill levels, and prerequisites? | `skyrim_enchant_perks()` |
| What weapon enchantments exist? What are their schools and base costs? | `skyrim_enchant_weapon_effects(name?)` |
| What apparel enchantments exist? What slots do they fit? What are their base costs? | `skyrim_enchant_apparel_effects(slot?, name?)` |
| How many charges/uses will I get from this weapon enchantment at skill X with soul Y? | Compute using `base_cost` from `skyrim_enchant_weapon_effects()` + capacity from `skyrim_enchant_soul_gems()` + formula above |
| What soul gems exist? What creatures can fill them? | `skyrim_enchant_soul_gems()` |
| What soul size does creature X have? | `skyrim_enchant_souls(name?)` |
| What items do I need to disenchant to learn enchantment X? | `skyrim_enchant_disenchant(effect)` |

The tools return live database data. The formulas in this document provide the rules context for
any calculation or strategy question beyond a simple lookup.
