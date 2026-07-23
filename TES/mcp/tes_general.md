# TES GameTools — General Query Rules

This document covers cross-game conventions that apply to all three TES games (Morrowind,
Oblivion, Skyrim) and all crafting systems. Game-specific mechanics are in the individual
RAG docs for each game and system.

---

## Cross-Game Queries — Explicit Absence Rule

When a question is asked across multiple games (e.g. "which ingredients produce a Feather
potion in each game?"), **always address every game explicitly**, even when the answer for
one or more games is that the effect, mechanic, or system does not exist.

**Do not silently omit a game.** A missing section is indistinguishable from an oversight.
Instead, include the game with a clear explanation:

> **Skyrim — Feather**: Skyrim has no Feather effect. Carry weight is handled through the
> Steed Stone and Fortify Carry Weight enchantments; no alchemy ingredient carries this effect.

This rule applies to:
- Effects that exist in some games but not others (e.g. Feather, Burden, Chameleon)
- Crafting systems that exist in some games but not others (e.g. apparatus in Morrowind
  and Oblivion but not Skyrim; Skyrim has perks where the others have mastery levels)
- Soul sizes, enchantment slots, or other mechanics that differ structurally across games
- Any future game families added to the database

---

## Partial Data — NULL Fields

Some fields are NULL in the database when the relevant scraper has not been run or the
data source does not cover that entry. When a query returns NULL for a field that is
expected to have a value, note it explicitly rather than silently omitting the field or
substituting a guess.

Example: `base_cost` and `base_magnitude` in `skyrim_alchemy_effects` are NULL until
the UESP effects scraper runs. If a calculation requires these fields and they are NULL,
report that the data is missing rather than computing with a substitute.

---

## Mechanic Doesn't Exist vs. Data Missing

Distinguish between two different absences:

1. **The mechanic doesn't exist in this game.** Example: Skyrim has no alchemy apparatus;
   Morrowind has no poisons. State this as a game design fact.

2. **The mechanic exists but the data hasn't been loaded yet.** Example: Oblivion enchanting
   tables exist in the schema but the loader hasn't been run. State this as a data gap, not
   a game design fact.

Never conflate the two — one is a permanent answer, the other is a temporary limitation.
