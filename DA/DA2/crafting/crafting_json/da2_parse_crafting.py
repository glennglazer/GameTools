#!/usr/bin/env python3
"""
da2_parse_crafting.py
Parses da2_crafting_raw.json into four structured JSON files:

    da2_crafting_recipe_locations.json
    da2_crafting_resources.json
    da2_crafting_recipes.json
    da2_crafting_item_effects.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

# All 12 ingredient material names as they appear in the DB schema (column names).
# wiki display text must map to exactly one of these.
INGREDIENTS = [
    "Ambrosia", "Deathroot", "Deep Mushroom", "Dragon's Blood",
    "Elfroot", "Embrium", "Felandaris", "Glitterdust",
    "Lyrium", "Orichalcum", "Silverite", "Spindleweed",
]

# Disambiguation: wiki link page names that differ from the canonical DB name.
# "Lyrium (crafting resource)" → "Lyrium", etc.
_DISPLAY_CLEANUP = re.compile(r"\s*\(.*?\)\s*$")


# ── wiki-markup helpers ───────────────────────────────────────────────────────

def strip_links(text: str) -> str:
    """Remove or flatten wiki links: [[Page|Display]] → Display, [[Page]] → Page."""
    text = re.sub(r"\[\[File:[^\]]+\]\]", "", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'{2,3}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def extract_link_display(cell: str) -> str:
    """Return display text of the first [[...]] link in a cell, or the stripped cell text."""
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", cell)
    if m:
        page, display = m.group(1), m.group(2)
        return (display or page).strip()
    return strip_links(cell).strip()


def canonical_ingredient(raw_display: str) -> str | None:
    """Map a wiki display/page name to its canonical DB ingredient name, or None."""
    # Strip disambiguation suffix: "Elfroot (Dragon Age II)" → "Elfroot"
    clean = _DISPLAY_CLEANUP.sub("", raw_display.strip()).strip()
    if clean in INGREDIENTS:
        return clean
    # Additional aliases
    aliases = {
        "Lyrium": "Lyrium",  # from "Lyrium (crafting resource)"
    }
    return aliases.get(clean)


def value_to_currency(bronze_str: str) -> tuple[int, int, int]:
    """Convert a bronze integer string → (gold, silver, bronze)."""
    v = int(float(bronze_str))  # handle rare non-integer from wiki
    return v // 10000, (v % 10000) // 100, v % 100


# ── depth-counting template extractor ────────────────────────────────────────

def extract_template_block(wikitext: str, template_name: str) -> str:
    """Return the inner content of {{template_name ...}} using depth-counting.

    Handles nested templates (including {{{style|}}} triple-brace arguments)
    by tracking {{ / }} depth rather than a simple non-greedy regex.
    Returns an empty string if the template is not found.
    """
    marker = "{{" + template_name
    start = wikitext.find(marker)
    if start < 0:
        return ""
    pos = start + 2  # skip the opening {{
    depth = 1
    length = len(wikitext)
    while pos < length:
        two = wikitext[pos: pos + 2]
        if two == "{{":
            depth += 1
            pos += 2
        elif two == "}}":
            depth -= 1
            if depth == 0:
                break
            pos += 2
        else:
            pos += 1
    if depth != 0:
        return ""
    return wikitext[start + len(marker): pos]


def parse_template_fields(block: str) -> dict[str, str]:
    """Parse |key = value ... pairs from the inside of a template block.

    Uses [ \\t]* (not \\s*) around the = so that a trailing newline after
    an empty-value field is NOT consumed, keeping (.*?) anchored to the
    actual value rather than to the next field's name.
    """
    fields: dict[str, str] = {}
    for m in re.finditer(
        r"\|[ \t]*(\w+)[ \t]*=[ \t]*(.*?)(?=\n[ \t]*\|[a-zA-Z]|\Z)", block, re.DOTALL
    ):
        fields[m.group(1).strip()] = m.group(2).strip()
    return fields


# ── per-table parsers ─────────────────────────────────────────────────────────

def parse_recipe_locations(crafting_wikitext: str) -> list[dict]:
    """Parse the recipe list from Crafting_(Dragon_Age_II) wikitext.

    Each bullet has the form:
        * Act N[-M]: [[Item Name]] <location text>.

    Returns records: {"name": str, "act": str (JSON), "location": str}
    """
    HEADERS = {
        "=== Potions ===": "potions",
        "=== Runes ===": "runes",
        "=== Poisons and grenades ===": "poisons_grenades",
    }
    records = []
    current_category = None

    for line in crafting_wikitext.split("\n"):
        stripped = line.strip()
        # Track section
        for header in HEADERS:
            if stripped == header:
                current_category = header
                break
        # Stop after the crafting recipes section
        if stripped.startswith("== Crafting resource"):
            break
        if current_category is None or not stripped.startswith("* Act"):
            continue

        # Extract act string
        m_act = re.match(r"\* Act ([\d]+(?:-[\d]+)?)\s*:", stripped)
        if not m_act:
            continue
        act_str = m_act.group(1)
        if "-" in act_str:
            lo, hi = act_str.split("-")
            acts = list(range(int(lo), int(hi) + 1))
        else:
            acts = [int(act_str)]
        act_json = json.dumps({"acts": acts})

        # Extract item name: first [[...]] after the act prefix
        after_act = stripped[m_act.end():].strip()
        m_link = re.match(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]", after_act)
        if not m_link:
            continue
        item_name = m_link.group(1).strip()

        # Location: text after the item link, wiki-stripped, trailing period removed
        remainder = after_act[m_link.end():].strip()
        location = strip_links(remainder).rstrip(".")
        # Remove "(DLC)" annotations
        location = location.replace("(DLC)", "").strip()

        records.append({"name": item_name, "act": act_json, "location": location})

    return records


def parse_resources(supplier_wikitext: str) -> list[dict]:
    """Parse crafting resource rows from the Supplier page.

    Tables are inside Act 1/2/3 sections.
    Columns per row: Location | Quest | Resource | Description
    Returns records: {name, location, quest, description, act}
    """
    records = []
    current_act = None

    for line in supplier_wikitext.split("\n"):
        stripped = line.strip()

        # Track act sections
        m_act = re.match(r"=== Act (\d+) ===", stripped)
        if m_act:
            current_act = int(m_act.group(1))
            continue

        # Stop at Summaries section
        if stripped.startswith("== Summaries") or stripped.startswith("== Bugs"):
            break

        if current_act is None:
            continue

        # Only process data rows (starting with |, not header ! rows or table wrappers)
        if not stripped.startswith("|") or stripped.startswith("|}") or stripped.startswith("|!") or stripped.startswith("|-"):
            continue
        if stripped.startswith("|style=") or stripped.startswith("|class="):
            continue

        # Split by || to get cells
        cells = [c.strip() for c in stripped.split("||")]
        if len(cells) < 4:
            continue

        location_raw = cells[0].lstrip("|").strip()
        quest_raw = cells[1].strip()
        resource_raw = cells[2].strip()
        description_raw = cells[3].strip()

        location = extract_link_display(location_raw) if location_raw else None
        quest = extract_link_display(quest_raw) if quest_raw else None
        resource = extract_link_display(resource_raw)
        # Clean up disambiguation from resource name
        resource = _DISPLAY_CLEANUP.sub("", resource).strip()
        description = strip_links(description_raw)

        if not resource:
            continue

        records.append({
            "name": resource,
            "location": location,
            "quest": quest if quest else None,
            "description": description,
            "act": current_act,
        })

    return records


def parse_recipes(items: list[dict]) -> list[dict]:
    """Parse recipe pages for ingredients and crafting cost.

    Returns records with columns matching the da2_crafting_recipes schema:
    Name, Ambrosia, Deathroot, Deep Mushroom, Dragon's Blood, Elfroot,
    Embrium, Felandaris, Glitterdust, Lyrium, Orichalcum, Silverite,
    Spindleweed, Gold, Silver, Bronze
    """
    records = []
    for entry in items:
        name = entry["name"]
        wt = entry.get("recipe_wikitext", "")
        if not wt:
            print(f"  WARNING: no recipe wikitext for '{name}'", file=sys.stderr)
            continue

        block = extract_template_block(wt, "RecipeTransformer")
        if not block:
            print(f"  WARNING: no RecipeTransformer for '{name}'", file=sys.stderr)
            continue

        fields = parse_template_fields(block)

        # Build ingredient → quantity map
        ingredient_qty: dict[str, int] = {}
        i = 1
        while f"ingredient{i}" in fields:
            raw_ing = fields[f"ingredient{i}"]
            raw_qty = fields.get(f"quantity{i}", "0")
            display = extract_link_display(raw_ing)
            canonical = canonical_ingredient(display)
            if canonical:
                try:
                    ingredient_qty[canonical] = int(raw_qty)
                except ValueError:
                    pass
            else:
                print(f"  WARNING: unknown ingredient '{display}' in '{name}'",
                      file=sys.stderr)
            i += 1

        # Parse crafting cost from "It costs {{Currency|N}}" line
        m_cost = re.search(r"It costs \{\{Currency\|(\d+(?:\.\d+)?)\}\}", wt)
        gold, silver, bronze = (0, 0, 0)
        if m_cost:
            gold, silver, bronze = value_to_currency(m_cost.group(1))
        else:
            print(f"  WARNING: no crafting cost for '{name}'", file=sys.stderr)

        record: dict = {"name": name}
        for ing in INGREDIENTS:
            record[ing] = ingredient_qty.get(ing, 0)
        record["Gold"] = gold
        record["Silver"] = silver
        record["Bronze"] = bronze
        records.append(record)

    return records


def parse_item_effects(items: list[dict]) -> list[dict]:
    """Parse item pages for effect text.

    Returns records: {name: str, effects: str}
    """
    records = []
    for entry in items:
        name = entry["name"]
        wt = entry.get("item_wikitext", "")
        if not wt:
            print(f"  WARNING: no item wikitext for '{name}'", file=sys.stderr)
            records.append({"name": name, "effects": ""})
            continue

        block = extract_template_block(wt, "ItemTransformer")
        if not block:
            print(f"  WARNING: no ItemTransformer for '{name}'", file=sys.stderr)
            records.append({"name": name, "effects": ""})
            continue

        fields = parse_template_fields(block)
        raw_effects = fields.get("effects", "")

        # Extract text from each {{ColorPositiveStat|text}} call
        # Multiple effects separated by <br>
        effect_parts = re.findall(r"\{\{ColorPositiveStat\|([^}]+)\}\}", raw_effects)
        if effect_parts:
            effects = "; ".join(p.strip() for p in effect_parts)
        else:
            # Fallback: strip all markup
            effects = strip_links(
                re.sub(r"\{\{[^}]+\}\}", "", raw_effects)
            )

        records.append({"name": name, "effects": effects})

    return records


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse da2_crafting_raw.json into 4 structured JSON files"
    )
    ap.add_argument("raw_json",      help="Input: da2_crafting_raw.json")
    ap.add_argument("locations_json", help="Output: da2_crafting_recipe_locations.json")
    ap.add_argument("resources_json", help="Output: da2_crafting_resources.json")
    ap.add_argument("recipes_json",   help="Output: da2_crafting_recipes.json")
    ap.add_argument("effects_json",   help="Output: da2_crafting_item_effects.json")
    args = ap.parse_args()

    raw_path = Path(args.raw_json)
    if not raw_path.exists():
        print(f"ERROR: raw JSON not found: {raw_path}", file=sys.stderr)
        sys.exit(1)

    with open(raw_path, encoding="utf-8") as fh:
        raw = json.load(fh)

    locations = parse_recipe_locations(raw["crafting_wikitext"])
    resources = parse_resources(raw["supplier_wikitext"])
    recipes   = parse_recipes(raw["items"])
    effects   = parse_item_effects(raw["items"])

    outputs = [
        (args.locations_json, locations, "Recipe locations"),
        (args.resources_json, resources, "Resources"),
        (args.recipes_json,   recipes,   "Recipes"),
        (args.effects_json,   effects,   "Item effects"),
    ]
    for path_str, records, label in outputs:
        p = Path(path_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        print(f"  {label:20s}: {len(records):3d} → {p}")


if __name__ == "__main__":
    main()
