# Oblivion Enchanting — Rules and Mechanics

This document covers Oblivion enchanting: the two independent methods (sigil stones and soul gem
altars), how magnitude and charges are computed, and how to interpret the data returned by the
MCP tools.

---

## Two Independent Methods

Oblivion has two completely separate enchanting systems. Sigil stone enchanting and altar
enchanting are mutually exclusive on a per-item basis — but the available effects are a
**Venn diagram**: many effects can be applied via either method, while some effects are
exclusive to sigil stones and others are only available at altars.

---

## Common Rules (Both Methods)

1. **No re-enchanting.** An already-enchanted item cannot receive a second enchantment by any
   method.
2. **Apparel enchantments are constant while worn.** No charges, no duration — the effect is
   active as long as the item is equipped.
3. **Any enchantment can be placed on any item type.** There is no restriction separating
   "weapon effects" from "apparel effects." A damage or drain effect on clothing creates a
   cursed item (see Cursed Enchantments below).
4. **Item quality and upgrade level have no bearing on enchantment capacity.** A Fine sword
   and a plain sword accept identical enchantments.
5. **Arrows cannot be enchanted** by either method.

---

## Sigil Stone Enchanting

Requirements: **a sigil stone** and **an item to enchant**. No soul gems, gold, or altar needed.

1. **Only one effect per item.** This applies whether the item is a weapon or apparel.
2. **Adds zero to the item's value.** A sigil-stone-enchanted item is worth exactly its base
   item price.
3. **Magnitude is fixed by the stone.** No skill, no soul size, no gold — the stone's level
   (Descendent → Transcendent) fully determines the magnitude.
4. Not all effects are available via sigil stones; check `oblivion_sigil_stone()` for the full
   list of what is achievable.

---

## Soul Gem Reference (Altar Enchanting)

| Level | Soul Name | SoulGemNumber | Soul Power |
|-------|-----------|---------------|------------|
| 1 | Petty | 1 | 150 |
| 2 | Lesser | 2 | 300 |
| 3 | Common | 3 | 800 |
| 4 | Greater | 4 | 1200 |
| 5 | Grand | 5 | 1600 |

Black soul gems hold Grand-level souls (Power 1600). Most humanoid NPCs, Dremora, and
vampires have black souls.

**Gem-filling efficiency:** A soul gem can hold any soul of its size or smaller. The
`SoulGemNumber` in the apparel formula is the **gem's** level, not the soul's level. Because
`SoulGemNumber` appears in the denominator, a smaller gem used with the same soul yields a
**higher** enchantment magnitude. A Petty soul in a Petty gem outperforms the same Petty soul
in a Grand gem. Fill gems to capacity for best results.

---

## Altar Enchanting — Apparel (Constant Effects)

### Magnitude Formula

```
CEEF (Constant Effect Enchantment Factor) = (Power − 5) / SoulGemNumber / Base_Cost
Effect_Magnitude = Base_Cost × CEEF × Soul_Level + 5
```

Where:
- `Power` = soul power value (150 / 300 / 800 / 1200 / 1600)
- `SoulGemNumber` = capacity level of the **gem** (1–5)
- `Soul_Level` = level of the **soul** (1–5; same scale as SoulGemNumber)
- `Base_Cost` = the effect's base cost from `oblivion_enchant_effects`
- `5` = the game setting `fMagicCEEnchantMagOffset` (always 5)

When the soul exactly fills the gem (`Soul_Level = SoulGemNumber`), this simplifies to:
```
Effect_Magnitude = (Power − 5) + 5 = Power
```
Wait — that only holds if Base_Cost cancels. In practice, Base_Cost scales the CEEF and the
product retains only the soul/gem ratio. The formula as written is the authoritative source;
use `Base_Cost` from `oblivion_enchant_effects` for exact calculations.

**Special case — effects with no magnitude** (Night-Eye, Water Breathing, Water Walking):
these effects have no magnitude in the game. For the enchantment cost formula, treat the
effect magnitude as **5** (just the constant offset). The result is that any soul gem
produces the same flat enchantment, making even a Petty soul sufficient.

### Gold Cost to Create (Apparel)

```
Enchantment_Cost = Effect_Magnitude × Barter_Factor
```

`Barter_Factor` is from `oblivion_enchant_effects` (the `barter_factor` column).

---

## Altar Enchanting — Weapons (Charge-Based)

### Multiple Effects

A weapon may receive multiple effects at an altar (unlike sigil stones, which are limited to
one). Each additional effect increases the charge consumed per strike.

### Charge Per Use Formula

Weapon enchantments use the **unscaled spell cost** formula:

```
charge_per_use (single effect) = Base_Cost × 0.1 × Magnitude^1.28 × Duration × Range_Factor
```

For typical weapon enchantments (touch range, single-strike duration = 1, no area):
```
charge_per_use = Base_Cost × 0.1 × Magnitude^1.28
```

For target-range effects: multiply by **1.5** (`fMagicRangeTargetCostMult`).

With multiple effects, the **total** charge per use is the sum across all effects:
```
total_charge_per_use = Σ (Base_Cost_i × 0.1 × Magnitude_i^1.28)   for each effect i
```

`Base_Cost` here is the `base_cost` column from `oblivion_enchant_effects`. The CS wiki
(`cs.uesp.net/wiki/Category:Spell_Cost`) confirms weapon enchantment charge uses the unscaled
formula; do not use the scaled (magicka-to-cast) formula.

### Magicka Cost Cap

The UI caps the total magicka cost per use at **85**. When the chosen magnitudes would exceed
85, the UI prevents the enchantment. To check whether a combination is legal:
`total_charge_per_use ≤ 85`.

### Uses Per Full Charge

```
uses = soul_power / total_charge_per_use
```

Example: Grand soul (1600 power), one effect at maximum cost 85 → floor(1600 / 85) = 18 uses.

### Gold Cost to Create (Weapons)

```
Added_Value = 0.4 × (Enchantment_Cost + Item_Charge)
```

where `Enchantment_Cost` is the total magicka cost per use and `Item_Charge` is the total
charge (= `soul_power`).

---

## Value of Enchanted Items

| Method | Added Value |
|--------|-------------|
| Sigil stone | **+0** (zero) |
| Altar — apparel | `Magnitude × Barter_Factor` |
| Altar — weapon | `0.4 × (charge_per_use + soul_power)` |

---

## Cursed Enchantments

**Any** effect can be placed on **any** item type at an altar — including harmful effects
(Damage Health, Damage Fatigue, Drain Attribute, Silence, Disintegrate Armor, etc.) on
clothing or jewelry. Items with harmful constant-effect enchantments damage the wearer
while equipped and are commonly called cursed items.

⚠️ **When a user requests an enchantment using a harmful effect and does not specify they
are enchanting a weapon**, ask whether they intend a weapon or apparel enchantment before
computing anything. If they confirm apparel: warn them explicitly that the result will be
a cursed item — one that continuously damages the wearer — and confirm they intend this.
Note that even Sigil Stone "armor effects" can be harmful (drain/damage effects appear
in the stone's armor effect column).

---

## Recharging Weapons

1. **Soul gems** (cheapest and most reliable): drag a filled soul gem onto the weapon in
   inventory. One point of `soul_power` restores one charge point. Azura's Star is a reusable
   grand-level soul gem that can be filled and emptied indefinitely.
2. **Pay at Mages Guild**: 1 gold per charge point. Each guild hall has one member who offers
   this service. Convenient but expensive for large charges.
3. **Varla Stones**: activating one in inventory fully recharges all enchanted weapons and
   staves. Rare and non-respawning (found in Ayleid ruins). Worth ~1000 gold each; keep one
   or two in reserve.

Note: "septims" is the in-game name for gold pieces. 1 septim = 1 gold = 1 charge point
(for guild recharging).

---

## What the Database Tools Cover

| Question | Tool |
|----------|------|
| What enchantment effects exist? What are their base costs and barter factors? | `oblivion_enchant_effects(school?, name?)` |
| What soul size does creature X carry? | `oblivion_enchant_souls(name?)` |
| What sigil stones give a specific weapon or armor effect? What are their magnitudes? | `oblivion_sigil_stone(weapon_effect?, armor_effect?, level?)` |

The tools return live database data. Use `base_cost` and `barter_factor` from
`oblivion_enchant_effects` as inputs to the formulas in this document.
