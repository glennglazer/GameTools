# Morrowind Enchanting — Rules and Formulae

## Overview

Enchanting imbues items with permanent magical effects powered by trapped creature souls. Unlike
Oblivion and Skyrim, **no enchanting station is required**: drag a filled soul gem onto your
character's paper doll (as if equipping it) to open the enchanting menu. You can enchant a new
item or recharge an existing one from the same menu.

There are two paths:
- **NPC enchanter**: 100% success rate, but very expensive in gold.
- **Self-enchanting**: Free, but carries a failure risk that destroys the soul gem.

## Enchantment Types

| Type | Description |
|------|-------------|
| Cast When Used (CWU) | Apply to any equippable item or scroll; activates on demand from the Magic menu |
| Cast When Strikes (CWS) | Apply to weapons only (not bows/crossbows — see below); fires on hit |
| Constant Effect (CE) | Passive; active whenever the item is equipped; no charges; requires soul ≥ 400 |

**Important**: CE cannot be mixed with CWU or CWS on the same item. CE enchantments may only have
on-Self effects.

**Bows and crossbows**: Although the UI allows choosing "Cast when Strikes", the effect **never
triggers** because the weapon never physically contacts the target. Use Cast When Used or Constant
Effect for bows and crossbows. Arrows and bolts cannot be enchanted.

**Thrown projectiles** (stars, darts): Can be enchanted, but lose stackability. Each projectile
must be enchanted individually.

**Any enchantment type on any apparel slot**: Unlike Skyrim, there is no restriction pairing effect
type to item type. Any effect can go on any piece of clothing or armor, regardless of slot.

## Touch vs. Target on Long-Reach Weapons

"Touch" range is calculated relative to the PC at a reach of 1, not from the weapon tip. With Cast
When Strikes, the enchantment fires on hit but the target must also be within Touch range of the PC
for the effect to land. For long-reach weapons — spears, most staves, and some hammers — use
**Target** range instead. The tradeoff: Target range multiplies the enchantment point cost by 1.5.

The **Ebony Staff** has the highest enchantment capacity (90 pts) of any weapon, more than four
times the next-best staff. Because of its long reach, **Touch range is wasted on it** — use Target
or CWU. The enchantment cost penalty is worth it for any serious offensive build on this weapon.

## Soul Gem Requirements

| Soul Gem | Capacity | Minimum CE support |
|----------|----------|--------------------|
| Petty | 30 | No |
| Lesser | 60 | No |
| Common | 120 | No |
| Greater | 180 | No |
| Grand | 600 | Yes (≥ 400 required) |
| Azura's Star | 600 | Yes — reusable; soul gem is not destroyed |

For Constant Effect, the soul **must be 400 or greater**. Souls qualifying for CE:
Golden Saint (400), Staada (400), Ascended Sleeper (400), Dahrk Mezalf (400), Vivec (1000),
Almalexia (1500).

**Key CE efficiency rule**: Because the item's enchantment capacity — not the soul's size — limits
CE power, using a 400-soul (Golden Saint) is optimal for CE. Vivec's 1000-soul and Almalexia's
1500-soul cannot be put to any additional use in a CE enchantment. Save those large souls for
Cast When Used or Cast When Strikes enchantments where the charge pool scales with soul size.

**Grizzly Bear disambiguation**: The Morrowind soul table contains two distinct Grizzly Bear
entries — one from Bloodmoon at soul size 50, another at soul size 100. If the user asks about
Grizzly Bear souls, always clarify which one they mean, and when returning results display the size
in parentheses: e.g. *Grizzly Bear (50)* and *Grizzly Bear (100)*.

## Enchantment Point Cost Formula

Every item has an enchantment capacity (query via `morrowind_enchant_item`; values divided by 10
from raw DB storage). Each enchantment effect consumes some of that capacity.

### Single-effect cost

```
C = max(1,
      avg_magnitude × 0.05 × baseCost × duration
      + 0.025 × max(1, area) × baseCost
    )
```

Where:
- `avg_magnitude = (max(1, minMag) + max(1, maxMag)) / 2`
- `duration` = effect duration in seconds; for Constant Effect, use **100**
- `baseCost` = from `morrowind_enchant_magic_effects."Base Cost"` (query via `morrowind_enchant_magic_effects`)
- **Target range**: multiply `C` by 1.5
- Self or Touch: no range adjustment

Verified examples (Exquisite Shirt, 60-pt capacity):
- Restore Fatigue CE 1pt Self → C = 1 × 0.05 × 1 × 100 = **5 pts**
- Restore Health CE 2pts Self → C = 2 × 0.05 × 5 × 100 = **50 pts**
- Restore Health CE 2–3pts Self → C = 2.5 × 0.05 × 5 × 100 ≈ **62 pts** (exceeds the shirt)

### Compounding multiple effects

When an item has n effects, each effect's cost is multiplied by its position counting from the end:
the **last** effect costs 1×, the second-to-last 2×, …, the first effect costs n×. Total:

```
totalPoints = n×C₁ + (n-1)×C₂ + … + 1×Cₙ   (integer truncation at each step)
```

**Ordering rule**: put cheapest effects first (smallest C first) to minimize the total. Reversing
the order can easily push a two-effect combination from fitting to exceeding capacity.

Practical example (Exquisite Shirt, 60 pts):
- Wrong order: Restore Health 2pt first (×2 = 100) + Restore Fatigue 1pt (×1 = 5) = **105** — fails
- Correct order: Restore Fatigue 1pt first (×2 = 10) + Restore Health 2pt (×1 = 50) = **60** — fits

### Finding optimal magnitudes for N effects on an item

To maximize magnitudes given a capacity cap, solve iteratively:
1. Sort effects cheapest → most expensive.
2. Assign each remaining capacity to the cheapest remaining effect as integer magnitude.
3. For effects with a fixed-cost structure (binary magnitude, e.g. Water Breathing), treat them as
   cost = C at magnitude 1.
4. Allocate capacity using the compounding formula above.

### Item capacity reference (query tools)

Use `morrowind_enchant_item` to look up item capacities. Key upper bounds:
- **Daedric Tower Shield**: 225 pts (highest of any item)
- **Exquisite Ring/Amulet**: 120 pts each
- **Ebony Staff**: 90 pts (highest weapon)
- **Daedric Gauntlets**: 60 pts each
- **Exquisite Shirt/Pants/Skirt**: 60 pts each (three slots; stack for 180 combined)
- **Daedric Cuirass**: 60 pts

Max combined capacity if wearing every optimal slot: approximately 1285–1335 pts (varies by DLC
and available equipment; see UESP Morrowind:Enchant#Total Wearable Enchant Points).

## Using Enchanted Items

Activation (CWU/CWS) draws charges based on the Enchant skill:

```
chargesUsed = baseCost × (1.1 − enchantSkill/100)
```

At Enchant 100 the multiplier is 0.1 (items last 10× longer than at Enchant 10).
Minimum 1 charge per use enforced by the game; the formula reaches 0 at Enchant 110.

## Self-Enchanting Success

The percent chance to successfully self-enchant one effect is:

```
Base = enchantSkill + intelligence/5 + luck/10 − 3 × enchantPoints
FatigueMod = 0.75 + 0.5 × (currentFatigue / maxFatigue)
SuccessChance% = Base × FatigueMod
For CE enchantment: SuccessChance% × 0.5
```

Where `enchantPoints` is the **cumulative** cost at that effect's position in the list. Vanilla
Morrowind checks success **for each effect separately** (a bug that makes multi-effect
self-enchanting disproportionately risky). A single failure destroys the soul gem.

**At maximum natural stats** (100 Enchant, 100 Int, 100 Luck, full fatigue):
- Base = 100 + 20 + 10 = 130; FatigueMod = 1.25
- Guaranteed success (≥ 100%) only up to ≈ 16.7 enchantment points
- Any nonzero chance up to ≈ 43.3 points (CE: same ceiling, chance halved throughout)

**Stat thresholds for 100% on any enchantment** (from UESP):
- Enchant skill fortified to ≥ 1225 (at base 100 Int/Luck), or
- Intelligence fortified to ≥ 4900 (at base 100 Enchant/Luck)

Fortifying **Enchant skill** is far more efficient than Intelligence — each +1 Enchant equals +5
Intelligence in the formula. Use Fortify Skill (Enchant) spells or potions.

## Recharging Enchanted Items

Drag a filled soul gem onto your character in inventory to attempt a recharge.

**Success check**:

```
intelligenceTerm = clamp(0.2 × intelligence, 1, 20)  [caps at intelligence 100]
luckTerm         = clamp(0.1 × luck, 1, 10)           [caps at luck 100]
successChance%   = (enchantSkill + intelligenceTerm + luckTerm) × fatigueMod
```

Roll 0–99: success if roll < successChance%.

**Charge restored on success**:
```
rechargedAmount = soulgem_charge × (roll / successChance)
```

The amount is always less than 100% of the soul gem (since roll < successChance). At natural stat
limits the missing range is at most ~25% of the gem.

**Overflow bug (vanilla only)**: If stats are artificially boosted to extreme values (enchant +
alchemy loop — see below), the original engine's integer arithmetic overflows. Instead of
guaranteeing a full recharge, the formula wraps to zero, returning only 1–2 charge points even
with a Grand Soul Gem. The **Morrowind Code Patch (MCP)** fixes this. MCP is very common but not
universal — ask the user if they don't specify whether they have it. (Note: "MCP" here refers to
the Morrowind Code Patch, not the Model Context Protocol server used by this tool system.)

Soul gems are **always destroyed on recharge**, whether the attempt succeeds or fails — except
**Azura's Star**, which is reusable.

**Passive recharge** (always available, no risk): Enchanted items recharge at 1 charge point every
20 seconds automatically, even when not equipped and even near enemies. This rate accelerates
during Waiting, Traveling, and Resting. In nearly all situations, opening the Rest menu and
waiting 24 hours (≈ 1 minute real-time) is the most practical recharge strategy — it costs
nothing, risks nothing, and cannot be interrupted except by nearby enemies.

## The Alchemy-Enchant Loop

Truly powerful enchanting requires astronomically high stats. The canonical approach:

1. Make **Fortify Intelligence** potions → drink them → alchemist skill produces stronger potions
2. Stack potions to reach extreme Intelligence
3. Make **Fortify Enchant** potions (or Fortify Skill spells) → self-enchant with extreme success chance
4. Enchant gear with **Fortify Alchemy** or **Fortify Intelligence** → wear it → loop repeats with
   even more powerful potions

**Fortify Enchant skill is more efficient than Intelligence** (5× the formula weight). Prioritize
Fortify Skill (Enchant) items in the early loop before moving to pure Intelligence stacking.

**Spellmaking shortcut (rule #6)**: If you know *any* Fortify Skill spell from a spellmaker NPC,
you can create a Fortify Enchant spell without learning that specific effect separately. Knowing
Fortify Illusion is enough to make a low-level Fortify Enchant spell. This is a critical early
accelerant.

### Feasibility check before planning a loop

Before laying out loop iterations, verify the target enchantment is physically possible:
- Enchantment point cost must not exceed the item's capacity (max 225 pts)
- CE requires soul ≥ 400; CWU/CWS use the soul as the charge pool
- If the target cost exceeds 225 pts, no amount of skill or alchemy can make it work — the item
  simply cannot hold that enchantment

### Loop planning heuristic

Given current character stats and a target enchantment specification:
1. Compute cost using the enchantment formula
2. Compute required `enchantSkill + intelligence/5 + luck/10` for 100% success
3. Compute how much Fortify Enchant skill is needed via short-term potion/spell
4. If achievable in one round, enchant immediately
5. Otherwise: enchant Fortify Alchemy or Fortify Intelligence gear first → higher-tier potions →
   repeat until stats are sufficient

Aim for the **fewest iterations** — getting Fortify Enchant skill high enough early (via
spellmaking) collapses the loop by skipping Intelligence-grinding rounds.

## Constant Effect Strategies

**Minimum magnitude = 1 is free**: Setting minMag = 0 gives the same enchantment cost as minMag =
1 (both use `max(1, magnitudeMin) = 1`). Always set minimum to 1 to avoid getting 0-pt effects.

**Variable magnitude trick**: CE chooses a random magnitude in [minMag, maxMag] each time the item
is equipped. You can set a wide range (e.g. 1–59 on a 60-pt item) for the same cost as the median
(30). Re-equip the item until you roll a high magnitude. Best used on durable items not
frequently swapped.

**When to ask**: If the user doesn't specify a preference, ask whether they prefer maximizing the
guaranteed minimum (fixed magnitude, e.g. 30–30) or maximizing the potential ceiling (variable
magnitude, e.g. 1–59).

## Perils of Constant Effect

- **Constant Levitate** prevents sleeping anywhere except beds, bedrolls, or hammocks.
- **Constant Water Walking** makes it impossible to go underwater (blocks certain quests and areas).
- **Constant Water Breathing** and **Constant Restore Health** interfere with a Tribunal Temple quest.
- **Bound Armor CE**: Never enchant a piece of armor with Constant Effect Bound Armor of the same
  slot (e.g. a helmet enchanted with Bound Helm) — this creates a permanent bound item that cannot
  be dropped or repaired.
- **Damaged attribute bug**: If a stat is Damaged (not Drained), it cannot be restored until all
  items Fortifying that stat are unequipped. This makes Fortify Strength CE tedious when frequently
  fighting Greater Bonewalkers. Plan accordingly.

## Tool Coverage

| Question | Tool |
|----------|------|
| What does effect X cost (baseCost)? | `morrowind_enchant_magic_effects` |
| Which items have capacity ≥ N? | `morrowind_enchant_item` |
| What soul sizes are available? | `morrowind_enchant_souls` |
| What do soul gems hold? | `morrowind_enchant_soul_gems` |
