"""Parse raw DAO:A Poison-Making wiki data into structured JSON files.

Reads poisons_grenades_raw.json (output of the scraper) and produces five JSON files:
  awakening_poisons_grenades_recipes.json         — wide recipe table with `type` column
  awakening_poisons_grenades_ingredient_recipes.json — ingredient → recipe mapping
  awakening_poisons_grenades_tiers.json           — recipe → required tier (all 4)
  awakening_poisons_grenades_unlimited_supply.json — empty (no Awakening supply section)
  awakening_poisons_grenades_effects.json         — item name → damage_type/power/effect

Effects notes:
  - Elemental Coating and Elemental Grenade deal multiple damage types totalling
    10 and 150 respectively.  damage_type is a sorted comma-joined string
    (e.g. "cold, electricity, fire, nature, spirit"); power is the *total* damage.
  - Dispel Coating and Dispel Grenade deal no damage; power and damage_type are NULL,
    effect carries the verbatim description (with "None." prefix stripped).

Usage:
    python3 awakening_parse_poisons_grenades.py <raw_json> \\
        <recipes_json> <ingredient_recipes_json> <tiers_json> <supply_json> <effects_json>
"""
import argparse
import json
import re
import sys
from pathlib import Path


# ─── Wikitext helpers ────────────────────────────────────────────────────────

def strip_wiki_link(text: str) -> str | None:
    """Convert [[Target|Display]] → Display, [[Target]] → Target."""
    if text is None:
        return None
    return re.sub(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]", r"\1", text).strip()


def get_field(name: str, block: str) -> str | None:
    """Extract a named field value from a RecipeTransformer wikitext block."""
    pattern = rf"\|\s*{re.escape(name)}\s*=\s*(.*?)(?=\n\s*\||\n\s*}}}}|$)"
    m = re.search(pattern, block, re.DOTALL)
    if m:
        return m.group(1).strip() or None
    return None


# ─── Recipe parser ───────────────────────────────────────────────────────────

def parse_recipe(title: str, wikitext: str, grenade_results: set) -> dict:
    """Parse one RecipeTransformer wikitext block into a structured dict."""
    m = re.search(r"<onlyinclude>(.*?)</onlyinclude>", wikitext, re.DOTALL)
    block = m.group(1) if m else wikitext

    name_raw = get_field("name", block)
    result_raw = get_field("result", block)
    description = get_field("description", block)
    item_id = get_field("item_id", block)
    requires_raw = get_field("requires", block)

    # Tier: "Poison-Making: Rank N" → N
    tier = None
    if requires_raw:
        tm = re.search(r"Rank\s+(\d+)", requires_raw)
        if tm:
            tier = int(tm.group(1))

    result_name = strip_wiki_link(result_raw) if result_raw else None

    # Type: grenade if result is in the grenade_results set, otherwise poison
    item_type = "grenade" if result_name in grenade_results else "poison"

    # Up to 4 ingredient/quantity pairs
    ingredients = []
    for i in range(1, 5):
        ing_raw = get_field(f"ingredient{i}", block)
        qty_raw = get_field(f"quantity{i}", block)
        if ing_raw:
            ing_name = strip_wiki_link(ing_raw)
            qty = int(qty_raw) if qty_raw and qty_raw.isdigit() else 1
            ingredients.append({"ingredient": ing_name, "quantity": qty})

    record = {
        "name": strip_wiki_link(name_raw) if name_raw else title,
        "type": item_type,
        "result": result_name,
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

_ELEMENTAL_RE = re.compile(
    r"(\d+)\s+(.*?)\s+damage\s+for\s+a\s+total\s+of\s+(\d+)",
    re.IGNORECASE,
)


def _parse_elemental(cell: str) -> tuple[str, int] | None:
    """Parse 'N type1, type2, and type3 damage for a total of M' → (types_str, total).

    Returns None if the cell does not match the elemental damage pattern.
    """
    m = _ELEMENTAL_RE.search(cell)
    if not m:
        return None
    raw_types = m.group(2)
    # Normalise: collapse ", and " / " and " → ", " before splitting
    raw_types = re.sub(r",?\s*and\s+", ", ", raw_types)
    types = [t.strip() for t in raw_types.split(",") if t.strip()]
    types.sort()
    return ", ".join(types), int(m.group(3))


def _parse_dispel_effect(cell1: str, cell2: str) -> str | None:
    """Combine cell1 and cell2; strip leading 'None.' prefix; return None if empty."""
    text = (cell1 + " " + cell2).strip()
    text = re.sub(r"^None\.\s*", "", text).strip()
    # Remove trailing period that is part of the "None." sentence structure
    return text or None


def parse_awakening_effects(wikitext: str) -> list[dict]:
    """Parse the Awakening section wikitext (section 5 of Poison-Making) into effect records.

    Handles two wikitables:
      - Tier Four Poisons  (columns: Name | Damage Per Hit | Effect)
      - Tier Four Grenades (columns: Name | Damage)

    Returns a list sorted by name.
    """
    records: list[dict] = []
    for line in wikitext.splitlines():
        line = line.strip()
        if not re.match(r"^\|\s*\[\[", line):
            continue

        parts = [p.strip() for p in line.split("||")]
        if len(parts) < 2:
            continue

        name_m = re.search(r"\[\[([^\]|]+)\]\]", parts[0])
        if not name_m:
            continue
        name = name_m.group(1).strip()

        cell1 = parts[1] if len(parts) > 1 else ""
        cell2 = parts[2] if len(parts) > 2 else ""

        elemental = _parse_elemental(cell1)
        if elemental is not None:
            damage_type, power = elemental
            effect: str | None = None
        else:
            # Dispel item: no numeric damage, carry description as effect
            damage_type = None
            power_val = None
            effect = _parse_dispel_effect(cell1, cell2)
            records.append({
                "name": name,
                "damage_type": damage_type,
                "power": power_val,
                "effect": effect,
            })
            continue

        records.append({
            "name": name,
            "damage_type": damage_type,
            "power": power,
            "effect": effect,
        })

    records.sort(key=lambda r: r["name"])
    return records


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse raw DAO:A Poison-Making wiki data into structured JSON files"
    )
    ap.add_argument("raw_json", help="Path to poisons_grenades_raw.json (from scraper)")
    ap.add_argument("recipes_json",
                    help="Output: awakening_poisons_grenades_recipes.json")
    ap.add_argument("ingredient_recipes_json",
                    help="Output: awakening_poisons_grenades_ingredient_recipes.json")
    ap.add_argument("tiers_json",
                    help="Output: awakening_poisons_grenades_tiers.json")
    ap.add_argument("supply_json",
                    help="Output: awakening_poisons_grenades_unlimited_supply.json")
    ap.add_argument("effects_json",
                    help="Output: awakening_poisons_grenades_effects.json")
    args = ap.parse_args()

    raw_path = Path(args.raw_json)
    if not raw_path.exists():
        print(f"ERROR: raw JSON not found: {raw_path}", file=sys.stderr)
        sys.exit(1)

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    grenade_results = set(raw.get("grenade_results", []))

    # ── Parse recipes ──────────────────────────────────────────────────────────
    recipes: list[dict] = []
    ingredient_recipes: list[dict] = []
    tiers: list[dict] = []

    for entry in raw["recipes"]:
        rec = parse_recipe(entry["title"], entry["wikitext"], grenade_results)
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

    # ── Supply (always empty for Awakening) ────────────────────────────────────
    supply: list[dict] = []

    # ── Parse effects ──────────────────────────────────────────────────────────
    effects = parse_awakening_effects(raw["awakening_effects_wikitext"])

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

    poison_count = sum(1 for r in recipes if r["type"] == "poison")
    grenade_count = sum(1 for r in recipes if r["type"] == "grenade")
    print(f"Recipes:             {len(recipes):3d} ({poison_count} poisons, {grenade_count} grenades) → {args.recipes_json}")
    print(f"Ingredient→recipe:   {len(ingredient_recipes):3d} → {args.ingredient_recipes_json}")
    print(f"Tiers:               {len(tiers):3d} → {args.tiers_json}")
    print(f"Unlimited supply:    {len(supply):3d} → {args.supply_json}")
    print(f"Effects:             {len(effects):3d} → {args.effects_json}")


if __name__ == "__main__":
    main()
