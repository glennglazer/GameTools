"""Parse raw DAO:A Trap-Making wiki data into structured JSON files.

Reads trap_making_raw.json (output of the Awakening scraper) and produces
five JSON files:
  awakening_trap_making_recipes.json           — wide recipe table (plan name + result)
  awakening_trap_making_ingredient_recipes.json — ingredient → recipe mapping
  awakening_trap_making_tiers.json             — recipe → required tier (all 4)
  awakening_trap_making_unlimited_supply.json  — always empty (no Awakening supply)
  awakening_trap_making_effects.json           — trap name → damage_type/power/effect

Key differences from Origins:
  - Only 4 recipes, all Tier 4, with gxa_ item IDs
  - Ingredient disambiguation: [[Blood Lotus (Origins)]] → "Blood Lotus"
  - Elemental Trap has multi-element damage stored as sorted comma-joined string + total power
  - No dual-damage rows; effects table keyed on trap name alone
  - No locations/supply section (Awakening has no unlimited supply vendors for traps)

Usage:
    python3 awakening_parse_trap_making.py <raw_json> \\
        <recipes_json> <ingredient_recipes_json> <tiers_json> <supply_json> <effects_json>
"""
import argparse
import json
import re
import sys
from pathlib import Path


# ─── Wikitext helpers ─────────────────────────────────────────────────────────

def strip_wiki_link(text: str) -> str | None:
    """Convert [[Target|Display]] → Display, [[Target]] → Target."""
    if text is None:
        return None
    return re.sub(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]", r"\1", text).strip()


def normalize_ingredient_name(name: str) -> str:
    """Remove wiki disambiguation suffixes like ' (Origins)' from ingredient names.

    [[Blood Lotus (Origins)]] → strip_wiki_link → "Blood Lotus (Origins)"
                              → normalize → "Blood Lotus"
    """
    return re.sub(r"\s*\([^)]+\)\s*$", "", name).strip()


def get_field(name: str, block: str) -> str | None:
    """Extract a named field value from a RecipeTransformer wikitext block."""
    pattern = rf"\|\s*{re.escape(name)}\s*=\s*(.*?)(?=\n\s*\||\n\s*}}}}|$)"
    m = re.search(pattern, block, re.DOTALL)
    if m:
        return m.group(1).strip() or None
    return None


# ─── Recipe parser ────────────────────────────────────────────────────────────

def parse_recipe(title: str, wikitext: str) -> dict:
    """Parse one RecipeTransformer wikitext block into a structured dict.

    Applies normalize_ingredient_name() to handle disambiguation links like
    [[Blood Lotus (Origins)]] that appear without a display-name pipe.
    """
    m = re.search(r"<onlyinclude>(.*?)</onlyinclude>", wikitext, re.DOTALL)
    block = m.group(1) if m else wikitext

    name_raw = get_field("name", block)
    result_raw = get_field("result", block)
    description = get_field("description", block)
    item_id = get_field("item_id", block)
    requires_raw = get_field("requires", block)

    # Tier: "Trap-Making: Rank N" → N
    tier = None
    if requires_raw:
        tm = re.search(r"Rank\s+(\d+)", requires_raw)
        if tm:
            tier = int(tm.group(1))

    # Up to 4 ingredient/quantity pairs
    ingredients = []
    for i in range(1, 5):
        ing_raw = get_field(f"ingredient{i}", block)
        qty_raw = get_field(f"quantity{i}", block)
        if ing_raw:
            ing_name = strip_wiki_link(ing_raw)
            if ing_name:
                ing_name = normalize_ingredient_name(ing_name)
            qty = int(qty_raw) if qty_raw and qty_raw.isdigit() else 1
            ingredients.append({"ingredient": ing_name, "quantity": qty})

    record = {
        "name": strip_wiki_link(name_raw) if name_raw else title,
        "result": strip_wiki_link(result_raw) if result_raw else None,
        "description": description,
        "item_id": item_id,
        "tier": tier,
        "ingredient1": None, "quantity1": None,
        "ingredient2": None, "quantity2": None,
        "ingredient3": None, "quantity3": None,
        "ingredient4": None, "quantity4": None,
    }
    for idx, ing in enumerate(ingredients[:4], 1):
        record[f"ingredient{idx}"] = ing["ingredient"]
        record[f"quantity{idx}"] = ing["quantity"]

    return record


# ─── Effects parser ───────────────────────────────────────────────────────────

# Matches the Elemental Trap effect text:
# "dealing 40 cold, fire, electricity, nature, and spirit damage (total: 200)"
_ELEMENTAL_TRAP_RE = re.compile(
    r"dealing\s+\d+\s+([\w]+(?:\s*,\s*[\w]+)*(?:\s*,?\s*and\s+[\w]+)?)\s+damage.*?\(total:\s*(\d+)\)",
    re.IGNORECASE,
)


def _parse_elemental_trap(effect_text: str) -> tuple[str, int] | None:
    """Return (damage_type_str, total_power) for a multi-element Elemental Trap row.

    The type string is alphabetically sorted and comma-joined, matching the
    pattern used for Elemental Grenade/Coating in the Awakening poisons/grenades
    pipeline.

    Returns None if the text does not match the elemental pattern.
    """
    m = _ELEMENTAL_TRAP_RE.search(effect_text)
    if not m:
        return None
    raw_types = re.sub(r",?\s*and\s+", ", ", m.group(1))
    types = sorted(t.strip() for t in raw_types.split(",") if t.strip())
    damage_type = ", ".join(types)
    power = int(m.group(2))
    return damage_type, power


def parse_awakening_trap_effects(traps_wikitext: str) -> list[dict]:
    """Parse only the Awakening Tier Four Traps table from the Traps section.

    The Traps section contains two daotables: the first lists DAO Tier 1–4 traps;
    the second (headed 'Tier Four Traps (Awakening)') lists the four Awakening-
    exclusive traps. This function extracts only the second table.

    Each record has:
        name TEXT         — trap name (keyed to the result field in recipes)
        damage_type TEXT  — nullable; "cold, electricity, fire, nature, spirit" for
                           Elemental Trap; None for all others
        power INTEGER     — nullable; 200 for Elemental Trap; None for all others
        effect TEXT       — nullable; verbatim text (br tags → spaces) for non-elemental
                           traps; None for Elemental Trap
    """
    start_marker = "Tier Four Traps (Awakening)"
    idx = traps_wikitext.find(start_marker)
    if idx == -1:
        return []
    awakening_section = traps_wikitext[idx:]

    records: list[dict] = []
    for line in awakening_section.splitlines():
        line = line.strip()
        # Data rows start with | followed by a wiki link
        if not re.match(r"^\|\s*\[\[", line):
            continue
        parts = [p.strip() for p in line.split("||")]
        if len(parts) < 2:
            continue

        # Cell 0: trap name
        name_m = re.search(r"\[\[([^\]|]+)\]\]", parts[0])
        if not name_m:
            continue
        name = name_m.group(1).strip()

        # Cell 1: damage per hit (empty string or "200" for Elemental Trap)
        damage_text = parts[1] if len(parts) > 1 else ""

        # Cell 2: effect text (may contain <br/> line breaks)
        effect_raw = parts[2] if len(parts) > 2 else ""
        effect_clean = re.sub(r"<br\s*/?>", " ", effect_raw).strip() or None

        # Determine damage_type and power
        if effect_clean and (parsed := _parse_elemental_trap(effect_clean)):
            damage_type, power = parsed
            effect_out = None
        elif damage_text.strip().lstrip("-").isdigit():
            # Numeric damage but no elemental pattern — store verbatim
            damage_type = None
            power = int(damage_text.strip())
            effect_out = effect_clean
        else:
            damage_type = None
            power = None
            effect_out = effect_clean

        records.append({
            "name": name,
            "damage_type": damage_type,
            "power": power,
            "effect": effect_out,
        })

    records.sort(key=lambda r: r["name"])
    return records


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse raw DAO:A Trap-Making wiki data into structured JSON files"
    )
    ap.add_argument("raw_json", help="Path to trap_making_raw.json (from Awakening scraper)")
    ap.add_argument("recipes_json",
                    help="Output: awakening_trap_making_recipes.json")
    ap.add_argument("ingredient_recipes_json",
                    help="Output: awakening_trap_making_ingredient_recipes.json")
    ap.add_argument("tiers_json", help="Output: awakening_trap_making_tiers.json")
    ap.add_argument("supply_json",
                    help="Output: awakening_trap_making_unlimited_supply.json")
    ap.add_argument("effects_json", help="Output: awakening_trap_making_effects.json")
    args = ap.parse_args()

    raw_path = Path(args.raw_json)
    if not raw_path.exists():
        print(f"ERROR: raw JSON not found: {raw_path}", file=sys.stderr)
        sys.exit(1)

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    # ── Parse recipes ──────────────────────────────────────────────────────────
    recipes: list[dict] = []
    ingredient_recipes: list[dict] = []
    tiers: list[dict] = []

    for entry in raw["plans"]:
        rec = parse_recipe(entry["title"], entry["wikitext"])
        recipes.append(rec)

        if rec["tier"] is not None:
            tiers.append({"recipe": rec["name"], "tier": rec["tier"]})

        for i in range(1, 5):
            ing = rec.get(f"ingredient{i}")
            qty = rec.get(f"quantity{i}")
            if ing is not None:
                ingredient_recipes.append(
                    {"ingredient": ing, "recipe": rec["name"], "quantity": qty}
                )

    recipes.sort(key=lambda r: r["name"])
    ingredient_recipes.sort(key=lambda r: (r["ingredient"], r["recipe"]))
    tiers.sort(key=lambda r: (r["tier"], r["recipe"]))

    # ── Supply: always empty for Awakening trap-making ─────────────────────────
    supply: list[dict] = []

    # ── Parse effects from the Awakening daotable in the Traps section ────────
    effects = parse_awakening_trap_effects(raw["traps_wikitext"])

    # ── Write output files ─────────────────────────────────────────────────────
    def write(path: str, data: list) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    write(args.recipes_json, recipes)
    write(args.ingredient_recipes_json, ingredient_recipes)
    write(args.tiers_json, tiers)
    write(args.supply_json, supply)
    write(args.effects_json, effects)

    print(f"Recipes:             {len(recipes):3d} → {args.recipes_json}")
    print(f"Ingredient→recipe:   {len(ingredient_recipes):3d} → {args.ingredient_recipes_json}")
    print(f"Tiers:               {len(tiers):3d} → {args.tiers_json}")
    print(f"Unlimited supply:    {len(supply):3d} → {args.supply_json}")
    print(f"Effects:             {len(effects):3d} → {args.effects_json}")


if __name__ == "__main__":
    main()
