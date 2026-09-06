"""Parse raw DAO Poison-Making wiki data into structured JSON files.

Reads poisons_grenades_raw.json (output of the scraper) and produces four JSON files:
  origins_poisons_grenades_recipes.json         — wide recipe table with `type` column
  origins_poisons_grenades_ingredient_recipes.json — ingredient → recipe mapping
  origins_poisons_grenades_tiers.json           — recipe → required tier (1-4)
  origins_poisons_grenades_unlimited_supply.json — unlimited-supply vendor/location table

Usage:
    python3 origins_parse_poisons_grenades.py <raw_json> \\
        <recipes_json> <ingredient_recipes_json> <tiers_json> <supply_json>
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


# ─── Locations parser ─────────────────────────────────────────────────────────

def _split_vendor_entries(text: str) -> list[str]:
    """Split a vendor text string on ' and ' and ', ' outside of parentheses."""
    text = re.sub(r",\s+and\s+", " and ", text)

    entries: list[str] = []
    depth = 0
    current = ""
    i = 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
            current += c
        elif c == ")":
            depth -= 1
            current += c
        elif depth == 0 and text[i:].startswith(" and "):
            if current.strip():
                entries.append(current.strip())
            current = ""
            i += 5
            continue
        elif depth == 0 and text[i:].startswith(", "):
            if current.strip():
                entries.append(current.strip())
            current = ""
            i += 2
            continue
        else:
            current += c
        i += 1
    if current.strip():
        entries.append(current.strip())
    return entries


def _parse_vendor_entry(entry: str) -> tuple[str | None, str, str | None]:
    """Parse 'Vendor in/at Location (optional note)' → (vendor, location, note)."""
    note: str | None = None
    nm = re.search(r"\s*\(([^)]+)\)[.!?]?\s*$", entry)
    if nm:
        note = nm.group(1)
        entry = entry[: nm.start()].strip()

    for prep in (" in ", " at the ", " at "):
        idx = entry.find(prep)
        if idx != -1:
            vendor: str | None = entry[:idx].strip() or None
            location = entry[idx + len(prep) :].strip()
            # Strip common leading articles/possessives from location
            for prefix in ("the ", "your "):
                if location.lower().startswith(prefix):
                    location = location[len(prefix):]
                    break
            return vendor, location, note

    return None, entry, note


def parse_locations(wikitext: str) -> list[dict]:
    """Parse the Locations section wikitext into a list of supply records."""
    records: list[dict] = []
    for line in wikitext.split("\n"):
        if not line.startswith("* "):
            continue
        line = line[2:]

        # Ingredient is the first wiki link; handle plural forms ("Flasks:" → "Flask")
        ing_match = re.match(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]s?:", line)
        if not ing_match:
            continue
        ingredient = ing_match.group(1)
        vendor_text = line[ing_match.end() :].strip()

        vendor_text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]", r"\1", vendor_text)

        for entry in _split_vendor_entries(vendor_text):
            if not entry:
                continue
            vendor, location, note = _parse_vendor_entry(entry)
            records.append(
                {
                    "ingredient": ingredient,
                    "vendor": vendor,
                    "location": location,
                    "note": note,
                }
            )
    return records


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse raw DAO Poison-Making wiki data into structured JSON files"
    )
    ap.add_argument("raw_json", help="Path to poisons_grenades_raw.json (from scraper)")
    ap.add_argument("recipes_json", help="Output: origins_poisons_grenades_recipes.json")
    ap.add_argument(
        "ingredient_recipes_json",
        help="Output: origins_poisons_grenades_ingredient_recipes.json",
    )
    ap.add_argument("tiers_json", help="Output: origins_poisons_grenades_tiers.json")
    ap.add_argument(
        "supply_json", help="Output: origins_poisons_grenades_unlimited_supply.json"
    )
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

    # ── Parse locations ────────────────────────────────────────────────────────
    supply = parse_locations(raw["locations_wikitext"])

    # ── Write output files ─────────────────────────────────────────────────────
    def write(path: str, data: list) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    write(args.recipes_json, recipes)
    write(args.ingredient_recipes_json, ingredient_recipes)
    write(args.tiers_json, tiers)
    write(args.supply_json, supply)

    poison_count = sum(1 for r in recipes if r["type"] == "poison")
    grenade_count = sum(1 for r in recipes if r["type"] == "grenade")
    print(f"Recipes:             {len(recipes):3d} ({poison_count} poisons, {grenade_count} grenades) → {args.recipes_json}")
    print(f"Ingredient→recipe:   {len(ingredient_recipes):3d} → {args.ingredient_recipes_json}")
    print(f"Tiers:               {len(tiers):3d} → {args.tiers_json}")
    print(f"Unlimited supply:    {len(supply):3d} → {args.supply_json}")


if __name__ == "__main__":
    main()
