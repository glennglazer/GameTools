"""Parse raw DAO Herbalism wiki data into structured JSON files.

Reads herbalism_raw.json (output of the scraper) and produces five JSON files:
  origins_herbalism_recipes.json         — wide recipe table (4 nullable ingredient cols)
  origins_herbalism_ingredient_recipes.json — ingredient → recipe mapping (reverse lookup)
  origins_herbalism_tiers.json           — recipe → required herbalism tier (1-4)
  origins_herbalism_unlimited_supply.json — unlimited-supply vendor/location table
  origins_herbalism_potion_effects.json  — crafted-item type/power/effects table

Usage:
    python3 origins_parse_herbalism.py <raw_json> \\
        <recipes_json> <ingredient_recipes_json> <tiers_json> <supply_json> <effects_json>
"""
import argparse
import json
import re
import sys
from pathlib import Path


# ─── Wikitext helpers ────────────────────────────────────────────────────────

def strip_wiki_link(text: str) -> str:
    """Convert [[Target|Display]] → Display, [[Target]] → Target."""
    if text is None:
        return None
    return re.sub(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]", r"\1", text).strip()


def strip_all_wiki_markup(text: str) -> str:
    """Strip all wiki links and trim whitespace."""
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
    # Extract the onlyinclude block (the canonical recipe data)
    m = re.search(r"<onlyinclude>(.*?)</onlyinclude>", wikitext, re.DOTALL)
    block = m.group(1) if m else wikitext

    name_raw = get_field("name", block)
    result_raw = get_field("result", block)
    description = get_field("description", block)
    item_id = get_field("item_id", block)
    requires_raw = get_field("requires", block)

    # Tier: "[[Herbalism#Tiers|Herbalism: Rank 3]]" → 3
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

    # Build wide-format recipe record (4 nullable columns)
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

def classify_effect(description: str) -> tuple:
    """Return (type, power) for a crafted item description string.

    Formula-based potions (Health/Mana) have their power computed at SP=0:
      "(50 + SP) * 3" → 150,  "(100 + 0.5 * SP)" → 100.

    Types returned:
      "Health"              — health restoration; power = formula evaluated at SP=0
      "Mana"                — mana restoration; power = formula evaluated at SP=0
      "Mabari"              — mabari-only health/stamina recovery (power=None)
      "Injury"              — health + injury kit (power=integer health restored)
      "Cold Resistance"     — cold resistance (power=integer percentage)
      "Nature Resistance"   — nature resistance (power=integer percentage)
      "Fire Resistance"     — fire resistance (power=integer percentage)
      "Spirit Resistance"   — spirit resistance (power=integer percentage)
      "Electricity Resistance" — electricity resistance (power=integer percentage)
      (None, None)          — buff (Incense of Awareness, Rock Salve, etc.)
    """
    d = description.lower()

    # Mabari: check before health/injury because description mentions both
    if "mabari hound" in d:
        return "Mabari", None

    # Health potions: "(base + ... SP ...) [* mult] health"
    # At SP=0: power = base * mult  (mult defaults to 1 when absent)
    if re.search(r"restores?\s", d) and "health" in d:
        m = re.search(r"\((\d+)\s*\+.*?sp.*?\)\s*(?:\*\s*(\d+))?", d)
        if m:
            base = int(m.group(1))
            mult = int(m.group(2)) if m.group(2) else 1
            return "Health", base * mult
        return "Health", None  # fallback: formula didn't match expected shape

    # Mana/Lyrium potions: "(base + ... SP ...)"
    # At SP=0: power = base  (coefficient of SP vanishes)
    if re.search(r"restores?\s.*mana", d):
        m = re.search(r"\((\d+)\s*\+.*?sp.*?\)", d)
        if m:
            return "Mana", int(m.group(1))
        return "Mana", None  # fallback

    # Injury kits: "regains N health" + mentions injuries
    m = re.search(r"regains?\s+(\d+)\s+health", d)
    if m and "injur" in d:
        return "Injury", int(m.group(1))

    # Resistance types (percentage-based)
    m = re.search(r"\+?(\d+)%\s+cold\s+resistance", d)
    if m:
        return "Cold Resistance", int(m.group(1))

    m = re.search(r"\+?(\d+)%\s+nature\s+resistance", d)
    if m:
        return "Nature Resistance", int(m.group(1))

    m = re.search(r"\+?(\d+)%\s+fire\s+resistance", d)
    if m:
        return "Fire Resistance", int(m.group(1))

    m = re.search(r"\+?(\d+)%\s+spirit\s+resistance", d)
    if m:
        return "Spirit Resistance", int(m.group(1))

    # Electricity has two surface forms on the wiki:
    #   Lesser: "resistance to electricity damage by 30%"
    #   Greater: "+60% electrical resistance"
    m = re.search(r"electricity\s+damage\s+by\s+(\d+)%", d)
    if not m:
        m = re.search(r"\+?(\d+)%\s+electrical\s+resistance", d)
    if m:
        return "Electricity Resistance", int(m.group(1))

    # Buff (Incense of Awareness, Rock Salve, Swift Salve, Dwarven Regicide Antidote, …)
    return None, None


def parse_crafted_item_effects(wikitext: str) -> list[dict]:
    """Parse the crafted-items wikitable into a list of effect records.

    Each row in the wikitable has the form:
        |[[Item Name]] || Description text
    Header rows start with '!' and are skipped.
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


# ─── Locations parser ─────────────────────────────────────────────────────────

def _split_vendor_entries(text: str) -> list[str]:
    """Split a vendor text string on ' and ' and ', ' outside of parentheses."""
    # Normalize ", and " → " and " so three-entry lists parse uniformly
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
    # Extract trailing parenthetical note (e.g. "(cheapest)", "(if you kill him...)")
    note: str | None = None
    nm = re.search(r"\s*\(([^)]+)\)\s*$", entry)
    if nm:
        note = nm.group(1)
        entry = entry[: nm.start()].strip()

    # Try prepositions in order: shorter ' in ' first to correctly handle
    # "Ruck in Ruck's Cave in the …" (vendor=Ruck, not "Ruck's Cave").
    for prep in (" in ", " at the ", " at "):
        idx = entry.find(prep)
        if idx != -1:
            vendor: str | None = entry[:idx].strip() or None
            location = entry[idx + len(prep) :].strip()
            # Strip leading "the " (e.g. "the Circle Tower" → "Circle Tower")
            if location.lower().startswith("the "):
                location = location[4:]
            return vendor, location, note

    # No preposition found: the whole string is the location (vendor implicit)
    return None, entry, note


def parse_locations(wikitext: str) -> list[dict]:
    """Parse the Locations section wikitext into a list of supply records."""
    records: list[dict] = []
    for line in wikitext.split("\n"):
        if not line.startswith("* "):
            continue
        line = line[2:]

        # Ingredient is the first wiki link; handle plural "Flasks:" → "Flask"
        ing_match = re.match(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]s?:", line)
        if not ing_match:
            continue
        ingredient = ing_match.group(1)
        vendor_text = line[ing_match.end() :].strip()

        # Convert all remaining wiki links to plain text
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
        description="Parse raw DAO Herbalism wiki data into structured JSON files"
    )
    ap.add_argument("raw_json", help="Path to herbalism_raw.json (from scraper)")
    ap.add_argument("recipes_json", help="Output: origins_herbalism_recipes.json")
    ap.add_argument(
        "ingredient_recipes_json",
        help="Output: origins_herbalism_ingredient_recipes.json",
    )
    ap.add_argument("tiers_json", help="Output: origins_herbalism_tiers.json")
    ap.add_argument("supply_json", help="Output: origins_herbalism_unlimited_supply.json")
    ap.add_argument("effects_json", help="Output: origins_herbalism_potion_effects.json")
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

        # Expand ingredient columns to normalised join records
        for i in range(1, 5):
            ing = rec.get(f"ingredient{i}")
            qty = rec.get(f"quantity{i}")
            if ing is not None:
                ingredient_recipes.append(
                    {"ingredient": ing, "recipe": rec["name"], "quantity": qty}
                )

    # Sort for stable output
    recipes.sort(key=lambda r: r["name"])
    ingredient_recipes.sort(key=lambda r: (r["ingredient"], r["recipe"]))
    tiers.sort(key=lambda r: (r["tier"], r["recipe"]))

    # ── Parse locations ───────────────────────────────────────────────────────
    supply = parse_locations(raw["locations_wikitext"])

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
