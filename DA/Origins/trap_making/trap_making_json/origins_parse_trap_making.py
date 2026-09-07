"""Parse raw DAO Trap-Making wiki data into structured JSON files.

Reads trap_making_raw.json (output of the scraper) and produces five JSON files:
  origins_trap_making_recipes.json         — wide recipe table (plan name + result trap name)
  origins_trap_making_ingredient_recipes.json — ingredient → recipe mapping
  origins_trap_making_tiers.json           — recipe → required tier (1-4)
  origins_trap_making_unlimited_supply.json — unlimited-supply vendor/location table
  origins_trap_making_effects.json         — trap name → damage_type/power/effect

Usage:
    python3 origins_parse_trap_making.py <raw_json> \\
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


def get_field(name: str, block: str) -> str | None:
    """Extract a named field value from a RecipeTransformer wikitext block."""
    pattern = rf"\|\s*{re.escape(name)}\s*=\s*(.*?)(?=\n\s*\||\n\s*}}}}|$)"
    m = re.search(pattern, block, re.DOTALL)
    if m:
        return m.group(1).strip() or None
    return None


# ─── Recipe parser ────────────────────────────────────────────────────────────

def parse_recipe(title: str, wikitext: str) -> dict:
    """Parse one RecipeTransformer wikitext block into a structured dict."""
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

_DAMAGE_TYPES = ("physical", "nature", "fire", "cold", "electricity", "spirit")
_DAMAGE_TYPE_PAT = "|".join(_DAMAGE_TYPES)

# Dual damage: "8 physical and 8 nature damage..."
_DUAL_RE = re.compile(
    rf"(-?\d+)\s+({_DAMAGE_TYPE_PAT})\s+and\s+(-?\d+)\s+({_DAMAGE_TYPE_PAT})\s+damage"
)
# Simple damage: "100 fire damage to those nearby"
_SIMPLE_RE = re.compile(rf"(-?\d+)\s+({_DAMAGE_TYPE_PAT})\s+damage")


def _parse_damage_pairs(damage_text: str) -> list[tuple[str | None, int | None]]:
    """Parse damage text into a list of (damage_type, power) tuples.

    Returns two tuples for dual-damage text (e.g. Poisoned Caltrop Trap:
    "8 physical and 8 nature damage..."), one tuple for single-type damage,
    or [(None, None)] for empty or unrecognised text.
    """
    if not damage_text:
        return [(None, None)]
    # Try dual damage first so the simple regex doesn't partially match
    m = _DUAL_RE.search(damage_text)
    if m:
        return [
            (m.group(2), int(m.group(1))),
            (m.group(4), int(m.group(3))),
        ]
    m = _SIMPLE_RE.search(damage_text)
    if m:
        return [(m.group(2), int(m.group(1)))]
    return [(None, None)]


def parse_trap_effects(traps_wikitext: str) -> list[dict]:
    """Parse the DAO Traps section wikitable into a sorted list of effect records.

    Awakening-only Tier Four traps (in a second daotable headed
    'Tier Four Traps (Awakening)') are excluded by truncating the wikitext
    at that string.

    Dual-damage traps (Poisoned Caltrop Trap) produce two records — one row per
    damage type — so the table can be keyed on (name, power, damage_type).

    Each record has:
        name TEXT         — trap name (not plan name; keyed to the result field)
        damage_type TEXT  — nullable; e.g. 'physical', 'nature'
        power INTEGER     — nullable; numeric damage per hit
        effect TEXT       — nullable; verbatim Effect column text
    """
    stop = "Tier Four Traps (Awakening)"
    idx = traps_wikitext.find(stop)
    if idx != -1:
        traps_wikitext = traps_wikitext[:idx]

    records: list[dict] = []
    for line in traps_wikitext.splitlines():
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

        # Cell 1: "Damage per hit" column — may produce multiple (type, power) pairs
        damage_text = parts[1] if len(parts) > 1 else ""
        damage_pairs = _parse_damage_pairs(damage_text)

        # Cell 2: "Effect" column (optional)
        effect: str | None = None
        if len(parts) >= 3:
            eff = parts[2].strip()
            if eff:
                effect = eff

        for damage_type, power in damage_pairs:
            records.append(
                {
                    "name": name,
                    "damage_type": damage_type,
                    "power": power,
                    "effect": effect,
                }
            )

    records.sort(key=lambda r: r["name"])
    return records


# ─── Locations parser ─────────────────────────────────────────────────────────

def _parse_vendor_entry(entry: str) -> tuple[str | None, str | None, str | None]:
    """Parse 'Vendor at/in Location (note)' or bare 'VendorName' → (vendor, location, note).

    Bare names with no preposition (e.g. 'Bodahn Feddic', 'Ruck') are treated
    as vendor names with unknown/NULL location.
    """
    note: str | None = None
    nm = re.search(r"\s*\(([^)]+)\)[.!?]?\s*$", entry)
    if nm:
        note = nm.group(1)
        entry = entry[: nm.start()].strip()

    for prep in (" in ", " at the ", " at "):
        i = entry.find(prep)
        if i != -1:
            vendor: str | None = entry[:i].strip() or None
            location: str | None = entry[i + len(prep):].strip() or None
            for prefix in ("the ", "your "):
                if location and location.lower().startswith(prefix):
                    location = location[len(prefix):]
                    break
            return vendor, location, note

    # No preposition — treat the whole entry as the vendor name
    return entry.strip() or None, None, note


def _split_vendors(text: str) -> list[str]:
    """Split vendor text on ', ' outside parentheses."""
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


def parse_locations(wikitext: str) -> list[dict]:
    """Parse the Locations section into unlimited supply records.

    Handles lines where multiple ingredients share one vendor entry:
        * [[Deathroot (Origins)|Deathroot]] and [[Toxin Extract]]: [[Varathorn]] at the [[Dalish Camp]]
    yields one row per ingredient.

    Bare vendor entries with no location preposition (e.g. '[[Bodahn Feddic]]',
    '[[Ruck]]') produce rows with vendor=name and location=NULL.
    """
    records: list[dict] = []
    for line in wikitext.splitlines():
        if not line.startswith("* "):
            continue
        line = line[2:]

        # Split on the first ":" to separate ingredient(s) from vendor text
        colon_idx = line.find(":")
        if colon_idx == -1:
            continue
        ingredient_part = line[:colon_idx]
        vendor_text = line[colon_idx + 1:].strip()

        # All wiki links in the ingredient part are ingredients
        ingredient_links = re.findall(
            r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]", ingredient_part
        )
        if not ingredient_links:
            continue

        # Strip wiki markup from vendor text
        vendor_text = re.sub(
            r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]", r"\1", vendor_text
        )

        for entry in _split_vendors(vendor_text):
            if not entry:
                continue
            vendor, location, note = _parse_vendor_entry(entry)
            for ingredient in ingredient_links:
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
        description="Parse raw DAO Trap-Making wiki data into structured JSON files"
    )
    ap.add_argument("raw_json", help="Path to trap_making_raw.json (from scraper)")
    ap.add_argument("recipes_json", help="Output: origins_trap_making_recipes.json")
    ap.add_argument(
        "ingredient_recipes_json",
        help="Output: origins_trap_making_ingredient_recipes.json",
    )
    ap.add_argument("tiers_json", help="Output: origins_trap_making_tiers.json")
    ap.add_argument(
        "supply_json", help="Output: origins_trap_making_unlimited_supply.json"
    )
    ap.add_argument("effects_json", help="Output: origins_trap_making_effects.json")
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

    # ── Parse locations ────────────────────────────────────────────────────────
    supply = parse_locations(raw["locations_wikitext"])

    # ── Parse effects ──────────────────────────────────────────────────────────
    effects = parse_trap_effects(raw["traps_wikitext"])

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
