# TES Enchanting Showcase

Thirteen questions spanning Skyrim, Oblivion, and Morrowind — database lookups, formula calculations, and multi-step strategy planning.

---

## Skyrim

### Q1 `[SKYRIM]` `[LOOKUP]` — Muffle: Items to Disenchant

**Q:** What items can I disenchant to learn the Muffle enchantment?

**A:** Exactly one item carries it:

| Item | Type |
|------|------|
| Boots of Muffling | Apparel (boots) |

**Notes:**
- Muffle has no magnitude — the enchantment is binary (on or off). A Petty soul produces the same result as a Grand soul; use the cheapest gem you have.
- First available at character level 11.
- Excellent for mass-enchanting and profit: because magnitude is irrelevant, any soul size produces an identical item, making Muffle one of the highest-value-per-soul enchantments at small gem sizes.

---

### Q2–Q5 `[SKYRIM]` `[FORMULA]` — Shock vs Frost Damage: Max Magnitude and Uses

**Setup for all four questions:**
- Enchanting skill: 100 (natural max)
- Fortify Enchanting potion: +36%
- Soul: Common (capacity 1000)
- Enchanter perk: 3/5 (enchanter_perk = 0.60)
- No Seeker of Sorcery, no Ahzidal's Genius, no Augmented elemental Destruction perks

**Q2:** Shock Damage, no Unofficial Skyrim Patch (USP), Storm Enchanter perk

**Q3:** Shock Damage, with USP, Storm Enchanter perk

**Q4:** Frost Damage, no USP, Frost Enchanter perk

**Q5:** Frost Damage, with USP, Frost Enchanter perk

---

**Formula — max magnitude:**

UESP-sourced base magnitudes (Grand soul, skill 0, no perks): Shock = **10**, Frost = **10**
Both base_costs from DB: Shock = **14**, Frost = **13**

*Without USP (vanilla):* potion is folded into effective skill  
`effective_skill = 100 + 36 = 136`  
`skill_multiplier = 1 + (1.36 × 1.22) / 3.4 = 1.488`

*With USP:* potion is a separate linear multiplier  
`skill_multiplier = 1 + (1.0 × 0.86) / 3.4 = 1.253`  
`potion factor = 1 + 0.36 = 1.36`

**Max magnitude (inner floor, then outer floor):**

| | No USP | USP |
|---|---|---|
| Shock (Storm Enchanter +0.25) | floor(10 × 1.488 × 1.6 × 1.25) = floor(29.76) = **29** | floor(10 × 1.253 × 1.36 × 1.6 × 1.25) = floor(34.08) = **34** |
| Frost (Frost Enchanter +0.25) | floor(10 × 1.488 × 1.6 × 1.25) = **29** | floor(10 × 1.253 × 1.36 × 1.6 × 1.25) = **34** |

**Charges per use at max magnitude** (independent of magnitude path):

`charges_per_use_at_max = 3 × base_cost^1.1 × (1 − √(100/200))`  
`= 3 × base_cost^1.1 × 0.2929`

| Effect | base_cost | base_cost^1.1 | charges/use | Uses (1000 / charges) |
|--------|-----------|---------------|-------------|----------------------|
| Shock Damage | 14 | 18.23 | 16.01 | **62** |
| Frost Damage | 13 | 16.80 | 14.76 | **67** |

**Summary table (Q2–Q5):**

| Q | Effect | Patch | Max Magnitude | Uses |
|---|--------|-------|--------------|------|
| 2 | Shock Damage | No USP | **29** | **62** |
| 3 | Shock Damage | USP | **34** | **62** |
| 4 | Frost Damage | No USP | **29** | **67** |
| 5 | Frost Damage | USP | **34** | **67** |

**Counter-intuitive finding:** At a +36% potion, the patched (USP) formula gives *higher* magnitudes than unpatched vanilla (34 vs 29). The vanilla "exponential" only beats the patch when potions exceed roughly +200–300%, which requires the full alchemy–enchanting exploit loop. For normal gameplay potions, USP is strictly more powerful.

**Frost vs Shock:** Both effects have identical base magnitudes (10), so magnitude is the same at the same perk level. Frost Damage costs slightly less per use (base_cost 13 vs 14), yielding 5 more uses from the same soul.

---

## Oblivion

### Q6 `[OBLIVION]` `[LOOKUP]` — Effects Only Available via Sigil Stones

**Q:** Which enchantment effects can only be obtained via Sigil Stones?

**A:** None — no effects are exclusively available through Sigil Stones.

Every effect obtainable from a Sigil Stone also has a functional equivalent at an altar:

| Sigil Stone name | Altar equivalent |
|-----------------|-----------------|
| Fortify Strength, Fortify Agility, Fortify Speed, Fortify Intelligence, Fortify Willpower | **Fortify Attribute** (choose target attribute) |
| Fortify Blade, Fortify Blunt | **Fortify Skill** (choose target skill) |
| Absorb Agility, Absorb Endurance, Absorb Strength, Absorb Speed, Absorb Intelligence | **Absorb Attribute** (choose target attribute) |
| All others (Damage Health, Soul Trap, Chameleon, etc.) | Same effect name, exact match |

The Sigil Stone table uses specific attribute/skill names; the altar uses generic "Fortify Attribute" and "Fortify Skill" with a target selection. The game effect is identical.

**What sigil stones do offer that altars don't:**
- Zero cost — no soul gem, no gold
- No Sigil Stone skill required — anyone can use one instantly
- Single-effect items, with no need to stay within charge caps

---

### Q7 `[OBLIVION]` `[LOOKUP]` — Effects Only Available via Altar

**Q:** Which enchantment effects can only be obtained at the Altar?

**A:** 72 effects are available only at the altar. By school:

**Alteration (2):** Open · Water Breathing

**Conjuration (35):** All 11 Bound items (Axe, Boots, Bow, Cuirass, Dagger, Gauntlets, Greaves, Helmet, Mace, Shield, Sword) · All 24 Summon effects (Ancestor Guardian, Bear, Clannfear, Daedroth, Dremora, Dremora Lord, Faded Wraith, Flame Atronach, Frost Atronach, Ghost, Gloom Wraith, Headless Zombie, Lich, Rufio's Ghost, Scamp, Skeleton, Skeleton Champion, Skeleton Guardian, Skeleton Hero, Spider Daedra, Spiderling, Storm Atronach, Xivilai, Zombie)

**Destruction (13):** Damage Attribute · Drain Attribute · Drain Fatigue · Drain Health · Drain Magicka · Drain Skill · Weakness to Disease · Weakness to Fire · Weakness to Frost · Weakness to Magic · Weakness to Normal Weapons · Weakness to Poison · Weakness to Shock

**Illusion (8):** Calm · Charm · Command Creature · Command Humanoid · Frenzy · Invisibility · Paralyze · Rally

**Mysticism (3):** Reflect Damage · Reflect Spell · Telekinesis

**Restoration (11):** Absorb Skill · Cure Disease · Cure Paralysis · Cure Poison · Resist Normal Weapons · Resist Paralysis · Resist Poison · Restore Attribute · Restore Fatigue · Restore Health · Restore Magicka

These include the most strategically important effects (Paralyze, Invisibility, all Summons, Drain and Weakness families, all Restore/Cure effects) — the altar is required for any serious enchanting build.

---

### Q8 `[OBLIVION]` `[FORMULA]` — Damage Health Weapon on Greater Soul Gem (1200 power)

**Q:** Damage Health weapon enchantment using a Greater soul gem (power 1200) — what is the maximum magnitude, number of uses, and added item value?

DB data: Damage Health — `base_cost = 12`, `barter_factor = 0`

**Max magnitude** — charge per use must not exceed 85:

`charge_per_use = 12 × 0.1 × magnitude^1.28 = 1.2 × magnitude^1.28 ≤ 85`  
`magnitude^1.28 ≤ 70.83` → `magnitude ≤ 27.9` → **magnitude = 27**

Verify: `1.2 × 27^1.28 = 1.2 × 67.93 = 81.52 ≤ 85` ✓  
At 28: `1.2 × 71.17 = 85.40 > 85` ✗

**Uses:** `floor(1200 / 81.52) = 14 uses`

**Added gold value:**  
`0.4 × (charge_per_use + soul_power) = 0.4 × (81.52 + 1200) ≈ 513 gold`

| Stat | Value |
|------|-------|
| Damage per strike | **27** |
| Charge pool | 1200 |
| Uses at max magnitude | **14** |
| Added item value | **~513 gold** |

Note: Damage Health has barter_factor = 0 — it is a harmful effect with no resale value added from the barter multiplier, only from the weapon charge formula.

---

### Q9 `[OBLIVION]` `[FORMULA]` — Fortify Strength Apparel on Greater Soul Gem (1200 power)

**Q:** Fortify Strength constant-effect apparel using a Greater soul gem (power 1200, exactly filling a Greater gem) — what is the magnitude and added item value?

"Fortify Strength" in Oblivion = **Fortify Attribute** (target: Strength)  
DB data: `base_cost = 0.6`, `barter_factor = 100`

**Magnitude formula** (Greater soul exactly fills Greater gem — Soul_Level = SoulGemNumber = 4):

When the soul exactly fills the gem, all effects simplify to:  
`Effect_Magnitude = Power = 1200`

The base_cost cancels entirely in the CEEF calculation. Every effect enchanted on a perfectly filled gem always gives magnitude = the soul's Power value.

**Added gold value:**  
`Magnitude × Barter_Factor = 1200 × 100 = 120,000 gold`

| Stat | Value |
|------|-------|
| Fortify Strength magnitude | **+1200** |
| Added item value | **120,000 gold** |

This also means: when the soul fills the gem exactly, the base_cost is irrelevant to magnitude — only the soul's Power matters. A Greater soul always yields magnitude 1200 regardless of whether the effect is Feather (base_cost 0.01) or Paralyze (base_cost 475). Base_cost becomes important only when the soul doesn't fill the gem.

---

## Morrowind

### Q10 `[MORROWIND]` `[FORMULA]` — Glass Shield CE Levitate + CE Chameleon, 180pt Soul

**Q:** What is the maximum Levitate and Chameleon magnitude on a Glass Shield with CE using a 180pt soul?

**A:** This combination is not achievable as stated. A 180pt soul is a Greater-class soul, and **Constant Effect requires soul ≥ 400.** The 180pt soul can only power Cast When Used or Cast When Strikes enchantments.

DB data: Glass Shield — `enchant_pts = 30`  
Effects: Levitate `base_cost = 3` (Alteration), Chameleon `base_cost = 1` (Illusion)

**If the question assumed CE is possible (educational):**  
CE formula: `C = avg_mag × 0.05 × base_cost × 100`

At magnitude 1:
- C_Chameleon = 1 × 0.05 × 1 × 100 = **5 pts**
- C_Levitate = 1 × 0.05 × 3 × 100 = **15 pts**

Compounding (cheapest first): `2 × 5 + 1 × 15 = 25 pts ≤ 30 pts` ✓

Maximum magnitudes given 30 pts capacity:  
`10 × mag_C + 15 × mag_L ≤ 30`  
→ With both: mag_C=1, mag_L=1 (25 pts total, 5 pts wasted). No room to raise either to 2.

| Configuration | Chameleon | Levitate | Total Cost | Remaining |
|--------------|-----------|----------|------------|-----------|
| Both at min | 1 | 1 | 25 pts | 5 wasted |
| Chameleon only | 6 | — | 30 pts | 0 wasted |
| Levitate only | — | 2 | 30 pts | 0 wasted |

**Corrected plan:** Use a Golden Saint (soul_size 400) in a Grand Soul Gem (or Azura's Star). Alternatively, choose a higher-capacity item: an Exquisite Ring (120 pts) with the same soul gives CE Levitate up to 8 points and CE Chameleon up to 24 — all while combining both effects (e.g. Levitate 3 + Chameleon 18, total = 3×90+1×18 = ask separately for exact split).

---

### Q11 `[MORROWIND]` `[STRATEGY]` — Ebony Staff: Alchemy-Enchant Loop for 100% Success

**Q:** Plan the alchemy-enchant loop to self-enchant an Ebony Staff with Paralyze 2s + Weakness to Shock 39% 2s + Shock Damage 49pts CWS at 100% success. Work out each iteration: what is produced, at what magnitude, and what soul gem strength is used.

---

**Enchantment verified (pre-loop)**

The Ebony Staff (`item_type BluntTwoWide`, long reach) requires **Target range** for CWS to reliably land. Target range multiplies enchantment cost by ×1.5.

| Effect | avg_mag | base_cost | dur | C (self) | ×1.5 Target | Integer |
|--------|---------|-----------|-----|----------|-------------|---------|
| Paralyze 2s | 1 (none) | 40 | 2 | 4.0 | 6.0 | **6** |
| Weakness to Shock 39% 2s | 39 | 2 | 2 | 7.8 | 11.7 | **11** |
| Shock Damage 49pts | 49 | 7 | 1 | 17.15 | 25.73 | **25** |

Compounding (cheapest → most expensive): `3×6 + 2×11 + 1×25 = 65 pts`  
Ebony Staff capacity: **90 pts**. 65 ≤ 90 ✓

**Ingredients:** Fortify Intelligence: Ash Yam + Bloat (confirmed in DB).  
Fortify Enchant: no ingredient provides this — use the spellmaker shortcut (any known Fortify Skill effect unlocks Fortify Skill [Enchant] at any magnitude).

---

**Start**

| Stat | Value |
|------|-------|
| Enchant | 60 |
| Intelligence | 70 |
| Luck | 50 |
| Alchemy | 65 |
| Apparatus | Master M&P (1.2) · Master Calcinator (1.2) · Master Retort (1.2) |
| Success chance (base) | **0%** — Base = 60 + 14 + 5 − 195 = −116 |
| Target for 100% | Enchant + Intel/5 + Luck/10 ≥ 275 (full fatigue) |

---

**Iteration 1 — Spellmaker: Create Fortify Skill (Enchant) Spell**

Produces: **a spell** — Fortify Skill [Enchant] +180 pts for 10 seconds on Self  
Soul gem required: **none** — this is a spell, not an enchantment

Visit any Mages Guild spellmaker. You already know any Fortify Skill effect (e.g., Fortify Heavy Armor). Purchase spell for ~500–700 gold.

```
When cast: Enchant temporarily = 60 + 180 = 240  (10-second window)
Approximate magicka cost to cast: ~144

Intermediate check (spell active, base stats):
  Base = 240 + 70/5 + 50/10 − 195 = 240 + 14 + 5 − 195 = 64
  SuccessChance = 64 × 1.25 = 80%  — not yet 100%; need more Intel
```

*Do not cast yet. File in spellbook for the final step.*

---

**Iteration 2 — Brew Fortify Intelligence Potions (Ash Yam + Bloat)**

Produces: **5 × Fortify Intelligence potion**, magnitude +34 pts each  
Soul gem required: **none** — these are potions

```
SkillFactor = Alchemy + Intel/10 + Luck/10 = 65 + 7 + 5 = 77
Fortify Intelligence EffectBaseCost = 1.0  (Fortify Attribute family)

Base_Strength = 77 × 1.2 / (3 × 1.0) = 30.8
Adjustment    = 1.2 + (1.2 × 2)       = 3.6
Potion_Intel  = 30.8 + 3.6 = 34.4  →  34 pts per potion
Potion_Duration = (77 × 1.2 / 1.0) + 3.6 = 96 seconds
```

Brew 5 potions (5× Ash Yam + 5× Bloat). Store; do not drink yet.

---

**Final Attempt — Stack Buffs · Attempt Self-Enchant**

Soul gem required: **Azura's Star holding Vivec (soul_size = 1 000)**

Action sequence — must complete within 96 seconds of drinking:
1. Ensure full Fatigue
2. Drink all 5 Fortify Intelligence potions → Intel = 70 + 5 × 34 = **240** temporarily
3. Cast Fortify Skill (Enchant) 180 → Enchant = 60 + 180 = **240** temporarily
4. Open inventory → drag Azura's Star to Ebony Staff paper doll → configure effects → confirm

```
Stats during attempt:
  Enchant (fortified):      240
  Intelligence (fortified): 240
  Luck (base):               50
  enchantPoints:             65

Base = 240 + 240/5 + 50/10 − 3 × 65
     = 240 + 48 + 5 − 195
     = 98

FatigueMod    = 1.25 (full fatigue)
SuccessChance = 98 × 1.25 = 122.5%  →  100%  ✓
```

**Soul and uses:**

| Parameter | Value |
|-----------|-------|
| Soul | Vivec (soul_size 1 000) in Azura's Star |
| Charge pool | 1 000 |
| chargesUsed at Enchant 60 | 65 × (1.1 − 0.60) = 32.5 → **33 per strike** |
| Uses at Enchant 60 | floor(1 000 / 33) ≈ **30 strikes** |
| Uses at Enchant 100 | floor(1 000 / 7) ≈ **142 strikes** (as skill grows) |
| Azura's Star fate | Returns empty after use — refillable for future enchantments |

---

### Q12 `[MORROWIND]` `[STRATEGY]` — Ebony Staff: Same Goal, No Fortify Skill Available

**Q:** Same enchantment, same character — but the Spellmaker shortcut is unavailable (Fortify Skill not known). Can 100% success still be reached, and how?

---

Without any source of Fortify Enchant, the skill stays at base 60 throughout. The success formula must be satisfied by Intelligence alone:

```
Enchant + Intel/5 + Luck/10 ≥ 275
60 + Intel/5 + 5 ≥ 275
Intel/5 ≥ 210  →  Intel ≥ 1 050
```

**Ingredients:** Fortify Intelligence: Ash Yam + Bloat (same as Q11). The spell is replaced with three nested brew sessions — each brewed at higher Intelligence than the last. All three batches must be **simultaneously active** when the enchanting attempt begins. Batch 1 sets the tightest timer: **96 seconds**.

---

**Start — same stats as Q11**

| Stat | Value |
|------|-------|
| Enchant | **60** — fixed; no Fortify Enchant available |
| Intelligence | 70 |
| Luck | 50 |
| Alchemy | 65 |
| Apparatus | Master M&P (1.2) · Master Calcinator (1.2) · Master Retort (1.2) |
| Target Intel | **≥ 1 050** (vs 240 in Q11) |

---

**Iteration 1 — Pre-brew Batch 1 (at base Intelligence 70)**

Produces: **10 × Fortify Intelligence**, +34 pts · 96 seconds  
Soul gem required: **none**

```
SkillFactor     = 65 + 70/10 + 50/10 = 77
Base_Strength   = 77 × 1.2 / (3 × 1.0) = 30.8
Adjustment      = 1.2 + (1.2 × 2) = 3.6
Potion_Intel    = 30.8 + 3.6 = 34 pts
Potion_Duration = (77 × 1.2 / 1.0) + 3.6 = 96 seconds
```

Brew 10 potions (10× Ash Yam + 10× Bloat). **Store; do not drink yet.**

---

**Iteration 2 — Drink Batch 1, Brew Batch 2 (at Intelligence 410)**

Produces: **10 × Fortify Intelligence**, +48 pts · 136 seconds  
Soul gem required: **none** — **96-second window begins now**

```
Drink Batch 1 (10 × 34) → Intel = 70 + 340 = 410  (96s clock starts)

SkillFactor     = 65 + 410/10 + 50/10 = 111
Base_Strength   = 111 × 1.2 / 3 = 44.4
Potion_Intel    = 44.4 + 3.6 = 48 pts
Potion_Duration = (111 × 1.2) + 3.6 = 136 seconds
```

Brew 10 potions (10× Ash Yam + 10× Bloat). **Drink immediately.** Intel = 70 + 340 + 480 = **890**.

---

**Iteration 3 — Brew Batch 3 (at Intelligence 890, both buffs active)**

Produces: **10 × Fortify Intelligence**, +67 pts · 194 seconds  
Soul gem required: **none** — Batch 1 has ~86 seconds remaining

```
Intel now = 890  (Batch 1 + Batch 2 both active)

SkillFactor     = 65 + 890/10 + 50/10 = 159
Base_Strength   = 159 × 1.2 / 3 = 63.6
Potion_Intel    = 63.6 + 3.6 = 67 pts
Potion_Duration = (159 × 1.2) + 3.6 = 194 seconds
```

Brew 10 potions (10× Ash Yam + 10× Bloat). **Drink immediately.** Intel = 70 + 340 + 480 + 670 = **1 560**.

---

**Final Attempt — All Three Batches Stacked · Attempt Self-Enchant**

Soul gem required: **Azura's Star holding Vivec (soul_size = 1 000)**

All three batches simultaneously active. Batch 1 sets the expiry (~96s from when it was drunk; brewing Batches 2 and 3 takes ~10s total, leaving ~86s to complete the enchantment).

```
Stats during attempt:
  Enchant (base, no buff):  60
  Intelligence (fortified): 1 560
  Luck (base):               50
  enchantPoints:             65

Base = 60 + 1560/5 + 50/10 − 3 × 65
     = 60 + 312 + 5 − 195
     = 182

FatigueMod    = 1.25 (full fatigue)
SuccessChance = 182 × 1.25 = 227.5%  →  100%  ✓
```

**Q11 vs Q12 comparison:**

|  | Q11 (Fortify Skill) | Q12 (no Fortify Skill) |
|---|---|---|
| Brew sessions | 1 | 3 |
| Total potions brewed | 5 | 30 |
| Ingredients | 5 Ash Yam + 5 Bloat | 30 Ash Yam + 30 Bloat |
| Final Intelligence | 240 | 1 560 |
| Enchant at attempt | 240 (fortified) | 60 (base) |
| Success chance | 122.5% | **227.5%** |
| Time pressure | 96s (1 buff expiry) | 96s (Batch 1 expiry) |
| Soul gem | Vivec (1 000) in Azura's Star | same |

Paradoxically, the path without Fortify Skill achieves a *higher* final success chance (227.5% vs 122.5%). The deeper Intel loop overshoots the 275 threshold by a larger margin than the one-brew-plus-spell path. The cost is 25 more potions, but the same 96-second window applies in both cases.

Soul uses: floor(1 000 / 33) ≈ **30 strikes** at Enchant 60; floor(1 000 / 7) ≈ **142 strikes** at Enchant 100.

---

## Skyrim (continued)

### Q13 `[SKYRIM]` `[FORMULA]` — The Alchemy–Enchanting Feedback Loop (Skyrim)

**Q:** Does iterating Fortify Alchemy enchantments → Fortify Enchanting potions → stronger Fortify Alchemy enchantments compound indefinitely in Skyrim, or does the loop converge? Work through 10 iterations for three characters with different skill and perk investments.

**Sources:** `skyrim_alchemy_effects` (Fortify Enchanting base_magnitude = 1); `skyrim_enchant_apparel` (Fortify Alchemy in 4 slots: head, hands, amulet, ring; base_cost = 167 → +8% per piece at skill 0, no perks).

#### Character profiles

| Attribute | Alvin | Simon | Theodore |
|-----------|-------|-------|----------|
| Alchemy skill | 0 | 40 | 100 |
| Alchemist perk | none ×1.0 | 3/5 ×1.6 | 5/5 ×2.0 |
| Benefactor perk | — | — | ×1.25 |
| Enchanting skill | 0 | 40 | 100 |
| Enchanter perk | none ×1.0 | 3/5 ×1.6 | 5/5 ×2.0 |
| Insightful Enchanter | — | — | ×1.25 |

#### Formulas

```
FE_potion = floor( 4 × BaseMag × SkillMult × AlchemistPerk × BenefactorPerk × FortifyAlchemy )
    SkillMult      = 1 + 0.5 × (Alchemy / 100)
    FortifyAlchemy = 1 + (total FA% / 100)

FA_per_piece = floor( 8 × skill_mult × EnchanterPerk × InsightfulEnchanter )
    eff_skill  = Enchanting + FE_potion%
    s          = eff_skill / 100
    skill_mult = 1 + (s × max(0, s − 0.14)) / 3.4
Total FA% = 4 × FA_per_piece
```

State machine per loop: brew FE potion with current FA bonus → drink → re-enchant 4 FA apparel pieces. Start state: FA factor = 1.0.

#### 10-iteration summary

| Loop | Alvin FA% | Simon FA% | Theodore FA% | Theodore FE% | Theodore FA/piece |
|------|-----------|-----------|--------------|--------------|-------------------|
| Start | 0% | 0% | 0% | — | — |
| **1** | 32% | 52% | **104%** | 15% | 26% |
| **2** | 32% | 52% | **112%** | 30% | 28% |
| **3** | 32% | 52% | **116%** | 31% | 29% |
| 4 | 32% | 52% | 116% | 32% | 29% |
| 5–10 | 32% | 52% | 116% | 32% | 29% |

Alvin and Simon converge after iteration 1. Theodore converges after iteration 4.

#### Theodore — iteration detail

```
Loop 1  (FA factor = 1.00):
  FE = floor(4 × 1 × 1.5 × 2.5 × 1.00) = 15%
  eff = 115;  sm = 1.3416;  FA/piece = floor(8 × 1.3416 × 2.5) = 26%;  total = 104%

Loop 2  (FA factor = 2.04):
  FE = floor(4 × 1 × 1.5 × 2.5 × 2.04) = 30%
  eff = 130;  sm = 1.4435;  FA/piece = floor(8 × 1.4435 × 2.5) = 28%;  total = 112%

Loop 3  (FA factor = 2.12):
  FE = floor(4 × 1 × 1.5 × 2.5 × 2.12) = 31%
  eff = 131;  sm = 1.4508;  FA/piece = floor(8 × 1.4508 × 2.5) = 29%;  total = 116%

Loop 4  (FA factor = 2.16):
  FE = floor(4 × 1 × 1.5 × 2.5 × 2.16) = 32%
  eff = 132;  sm = 1.4581;  FA/piece = floor(8 × 1.4581 × 2.5) = 29%;  total = 116%  ← converged
```

#### Secondary power — Restore Health with Theodore's full loop

```
Without loop  (FA = 1.00):  floor(4 × 5 × 1.5 × 2.5 × 1.00) = 75 HP
With 116% FA  (FA = 2.16):  floor(4 × 5 × 1.5 × 2.5 × 2.16) = 162 HP
```

#### Why it converges

Both the alchemy and enchanting formulas use `floor()`. Once the marginal gain from a stronger FA multiplier rounds down to zero FE% improvement, the enchanting skill plateaus and FA/piece stops growing. The `floor()` in both legs is the brake that prevents the Morrowind-style Intelligence explosion.

**Result:** The Skyrim loop converges to a fixed point in at most 4 iterations. Fixed points: Alvin 32% FA, Simon 52% FA, Theodore 116% FA. A fully-invested character gains a ×2.16 multiplier on all beneficial potions permanently after four loops.
