"""Parse raw DAO:A Herbalism wiki data into structured JSON files.

Reads herbalism_raw.json (output of the Awakening scraper) and produces five JSON files:
  awakening_herbalism_recipes.json         — wide recipe table (4 nullable ingredient cols)
  awakening_herbalism_ingredient_recipes.json — ingredient → recipe mapping (reverse lookup)
  awakening_herbalism_tiers.json           — recipe → required herbalism tier (all Tier 4)
  awakening_herbalism_unlimited_supply.json — empty list (no Awakening supply section on wiki)
  awakening_herbalism_potion_effects.json  — crafted-item type/power/effects table

All 10 Awakening herbalism recipes are Tier 4. The three item types are Health, Mana,
and Stamina (Stamina is new in Awakening). All use the formula (50 + SP) * N, evaluated
at SP=0 to produce the stored power value.

Usage:
    python3 awakening_parse_herbalism.py <raw_json> \\
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

def parse_recipe(title: str, wikitext: str) -> dict:
    """Parse one RecipeTransformer wikitext block into a structured dict."""
    m = re.search(r"<onlyinclude>(.*?)</onlyinclude>", wikitext, re.DOTALL)
    block = m.group(1) if m else wikitext

    name_raw = get_field("name", block)
    result_raw = get_field("result", block)
    description = get_field("description", block)
    item_id = get_field("item_id", block)
    requires_raw = get_field("requires", block)

    # Tier: "[[Herbalism#Tiers|Herbalism: Rank 4]]" → 4
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


# ─── Potion effects parser ───────────────────────────────────────────────────

def classify_effect(description: str) -> tuple[str | None, float | None]:
    """Return (type, power) for a crafted item description string.

    All DAO:A herbalism items use the formula (50 + SP) * N, evaluated at SP=0:
      power = 50 * N   (N defaults to 1 when the '* N' part is absent)

    Types:
      "Health"  — health restoration (Superb/Master Health Poultice)
      "Mana"    — mana restoration (Superb/Master Lyrium Potion)
      "Stamina" — stamina restoration (Lesser through Master Stamina Draught, new in Awakening)
      (None, None) — unrecognised description (defensive fallback)
    """
    d = description.lower()

    # Shared regex: (base + ... SP ...) [* mult]
    _FORMULA_RE = re.compile(r"\((\d+)\s*\+.*?sp.*?\)\s*(?:\*\s*(\d+))?")

    def _eval_formula(text: str) -> float | None:
        m = _FORMULA_RE.search(text)
        if m:
            base = int(m.group(1))
            mult = int(m.group(2)) if m.group(2) else 1
            return float(base * mult)
        return None

    if re.search(r"restores?\s", d) and "health" in d:
        return "Health", _eval_formula(d)

    if re.search(r"restores?\s.*mana", d):
        return "Mana", _eval_formula(d)

    if re.search(r"restores?\s.*stamina", d):
        return "Stamina", _eval_formula(d)

    return None, None


def parse_crafted_item_effects(wikitext: str) -> list[dict]:
    """Parse the crafted-items wikitable into a list of effect records.

    Each data row in the wikitable has the form:
        |[[Item Name]] || Description text
    Header rows (starting with '!') and section headings are skipped.
    """
    records: list[dict] = []
    for m in re.finditer(
        r"^\|\s*\[\[([^\]|]+)\]\]\s*\|\|\s*(.+)$",
        wikitext,
        re.MULTILINE,
    ):
        name = m.group(1).strip()
        description = m.group(2).strip()
        item_type, power = classify_effect(description)
        records.append(
            {
                "name": name,
                "type": item_type,
                "power": power,
                "effects": description,
            }
        )
    return records


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse raw DAO:A Herbalism wiki data into structured JSON files"
    )
    ap.add_argument("raw_json", help="Path to herbalism_raw.json (from Awakening scraper)")
    ap.add_argument("recipes_json", help="Output: awakening_herbalism_recipes.json")
    ap.add_argument(
        "ingredient_recipes_json",
        help="Output: awakening_herbalism_ingredient_recipes.json",
    )
    ap.add_argument("tiers_json", help="Output: awakening_herbalism_tiers.json")
    ap.add_argument("supply_json", help="Output: awakening_herbalism_unlimited_supply.json")
    ap.add_argument("effects_json", help="Output: awakening_herbalism_potion_effects.json")
    args = ap.parse_args()

    raw_path = Path(args.raw_json)
    if not raw_path.exists():
        print(f"ERROR: raw JSON not found: {raw_path}", file=sys.stderr)
        sys.exit(1)

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    # ── Parse recipes ─────────────────────────────────────────────────────────
    recipes: list[dict] = []
    ingredient_recipes: list[dict] = []
    tiers: list[dict] = []

    for entry in raw["recipes"]:
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

    # ── Supply (empty — no Awakening-specific section on the wiki) ────────────
    supply: list[dict] = []

    # ── Parse crafted item effects ────────────────────────────────────────────
    effects = parse_crafted_item_effects(raw["crafted_items_wikitext"])

    # ── Write output files ────────────────────────────────────────────────────
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
    print(f"Potion effects:      {len(effects):3d} → {args.effects_json}")


if __name__ == "__main__":
    main()
