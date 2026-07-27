# TES Enchanting Showcase

Eleven questions spanning Skyrim, Oblivion, and Morrowind — database lookups, formula calculations, and multi-step strategy planning.

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

**Q:** Plan the alchemy-enchant loop to self-enchant an Ebony Staff with Paralyze 2s + Weakness to Shock 39% 2s + Shock Damage 49pts CWS at 100% success. Include ingredients, soul values, and a summary table.

---

**Step 1: Verify the enchantment fits**

The Ebony Staff (item_type BluntTwoWide, long reach) requires **Target range** for all effects to reliably land. Target range multiplies enchantment cost by ×1.5.

Effect costs:

| Effect | avg_mag | base_cost | duration | C (self) | ×1.5 Target | Integer |
|--------|---------|-----------|----------|----------|-------------|---------|
| Paralyze 2s | 1 (no magnitude) | 40 | 2 | 4.0 | 6.0 | **6** |
| Weakness to Shock 39% 2s | 39 | 2 | 2 | 7.8 | 11.7 | **11** |
| Shock Damage 49pts | 49 | 7 | 1 | 17.15 | 25.73 | **25** |

Compounding (cheapest → most expensive): `3×6 + 2×11 + 1×25 = 18 + 22 + 25 = 65 pts`

Ebony Staff capacity: **90 pts**. **65 ≤ 90 ✓** — the enchantment fits with 25 pts spare.

---

**Step 2: Check baseline success**

`Base = enchantSkill + intel/5 + luck/10 − 3 × enchantPoints`

At natural maximum (Enchant 100, Intel 100, Luck 100, full fatigue):  
`Base = 100 + 20 + 10 − 195 = −65`  
`SuccessChance = −65 × 1.25 = negative → 0%`

The alchemy-enchant loop is required.

For 100% at full fatigue (FatigueMod = 1.25):  
`Base × 1.25 ≥ 100 → Base ≥ 80`  
`enchantSkill + intel/5 + luck/10 ≥ 275`

---

**Step 3: Loop plan**

**Alchemy ingredients for Fortify Intelligence:**  
From DB: **Ash Yam**, **Bloat**, Horker Tusk, Netch Leather

Use Ash Yam + Bloat (two ingredients sharing Fortify Intelligence) for maximum purity. With Master's Mortar & Pestle and Alchemy 100, each potion gives approximately +20–40 Intel for a limited duration.

**Spellmaker shortcut:**  
If you know any Fortify Skill spell (from a Mages Guild spellmaker), you can create Fortify Skill (Enchant) at any magnitude and duration. Even knowing Fortify Heavy Armor is enough. Aim for Fortify Enchant +100–150 for 10–15 seconds.

| Step | Action | Materials | Resulting Stats |
|------|--------|-----------|----------------|
| 1 | At spellmaker: create Fortify Skill (Enchant) +150, 15s | ~700 gold | Enchant → 250 when cast |
| 2 | Brew Fortify Intelligence potions × ~8 | Ash Yam × 8 + Bloat × 8 | Intel → ~260–300 |
| 3 | Drink all pots, cast spell, drag gem to paper doll | Grand Soul Gem + Vivec (1000) | Attempt self-enchant |

Success check at Intel 280, Enchant 250 (fortified), Luck 100, full fatigue:  
`Base = 250 + 56 + 10 − 195 = 121`  
`SuccessChance = 121 × 1.25 = 151% → capped at 100% ✓`

---

**Step 4: Soul choice and uses**

This is a **CWS** enchantment — CE's 400-soul threshold does NOT apply. Any soul fills the charge pool.

Use **Vivec (soul_size 1000)** in Azura's Star:
- Azura's Star is not consumed when used to create an enchantment (the star becomes empty and can be refilled)
- Charge pool on the Ebony Staff: 1000

At Enchant 100 (natural), uses:  
`chargesUsed = total_enchant_cost × (1.1 − 1.0) = 65 × 0.1 = 6.5 → ~7 per use`  
`Uses = floor(1000 / 7) ≈ 142 strikes`

---

**Q11 Summary Table**

| Parameter | Value |
|-----------|-------|
| Enchantment total cost | 65 pts (of 90 capacity) |
| Baseline success chance | **0%** (negative at natural stats) |
| Stats needed for 100% | Enchant + Intel/5 + Luck/10 ≥ 275 |
| Loop: Fortify Intel ingredients | Ash Yam + Bloat |
| Loop: Fortify Enchant method | Spellmaker (any known Fortify Skill) |
| Soul for Ebony Staff | Vivec (1000) in Azura's Star |
| Charge pool | 1000 charges |
| Uses at Enchant 100 | ~142 strikes |
| Recharge options | Passive (1/20s), active rest, or refill Azura's Star |
