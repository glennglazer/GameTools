#!/usr/bin/env python3
"""
da2_scrape_crafting.py
Scrapes Dragon Age II crafting data from the Fandom Dragon Age wiki.

Fetches:
  - Crafting_(Dragon_Age_II): recipe locations by act and category
  - Supplier: crafting resource locations by act
  - 33 recipe pages (Recipe:/Design:/Formula: prefixed) for ingredients + cost
  - 33 item pages for effects

Total: ~68 HTTP requests, ~0.3 s sleep between each (~21 s total).

Output: da2_crafting_raw.json
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

FANDOM_API = "https://dragonage.fandom.com/api.php"
UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
SLEEP = 0.3  # seconds between requests

# Recipe-page prefix per crafting category
CATEGORY_PREFIX = {
    "potions": "Recipe",
    "runes": "Design",
    "poisons_grenades": "Formula",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def fetch_wikitext(page: str) -> str:
    url = (f"{FANDOM_API}?action=parse"
           f"&page={urllib.parse.quote(page, safe='')}"
           f"&prop=wikitext&format=json")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data["parse"]["wikitext"]["*"]


def wiki_display(link_text: str) -> str:
    """Extract display text from a wiki link token like [[Page|Display]] or [[Page]]."""
    m = re.match(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", link_text.strip())
    if not m:
        return link_text.strip()
    page, display = m.group(1), m.group(2)
    return (display or page).strip()


def parse_item_names_from_crafting(wikitext: str) -> list[dict]:
    """Extract item names and their recipe prefix from the Crafting_(Dragon_Age_II) page."""
    HEADERS = {
        "=== Potions ===": "potions",
        "=== Runes ===": "runes",
        "=== Poisons and grenades ===": "poisons_grenades",
    }
    items = []
    current_category = None
    for line in wikitext.split("\n"):
        stripped = line.strip()
        for header, cat in HEADERS.items():
            if stripped == header:
                current_category = cat
                break
        if current_category is None:
            continue
        if not stripped.startswith("* Act"):
            continue
        # Extract item name from first [[...]] link after the act prefix
        m = re.search(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]", stripped)
        if not m:
            continue
        item_name = m.group(1).strip()
        prefix = CATEGORY_PREFIX[current_category]
        items.append({"name": item_name, "category": current_category, "prefix": prefix})
    return items


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape DA2 crafting data from the Fandom wiki"
    )
    ap.add_argument("output", help="Path for output da2_crafting_raw.json")
    args = ap.parse_args()

    output = Path(args.output)

    # 1. Crafting page (recipe locations by act)
    print("Fetching Crafting_(Dragon_Age_II)...")
    crafting_wikitext = fetch_wikitext("Crafting_(Dragon_Age_II)")
    time.sleep(SLEEP)

    # 2. Supplier page (resource locations by act)
    print("Fetching Supplier...")
    supplier_wikitext = fetch_wikitext("Supplier")
    time.sleep(SLEEP)

    # 3. Inline-parse item names and prefixes
    items_meta = parse_item_names_from_crafting(crafting_wikitext)
    print(f"Found {len(items_meta)} craftable items.")

    # 4. Fetch recipe and item pages for each item
    items = []
    for entry in items_meta:
        name = entry["name"]
        prefix = entry["prefix"]
        recipe_page = f"{prefix}: {name}"

        print(f"  {recipe_page}")
        try:
            recipe_wt = fetch_wikitext(recipe_page)
        except Exception as exc:
            print(f"  WARNING: failed to fetch '{recipe_page}': {exc}", file=sys.stderr)
            recipe_wt = ""
        time.sleep(SLEEP)

        print(f"  {name}")
        try:
            item_wt = fetch_wikitext(name)
        except Exception as exc:
            print(f"  WARNING: failed to fetch '{name}': {exc}", file=sys.stderr)
            item_wt = ""
        time.sleep(SLEEP)

        items.append({
            "name": name,
            "category": entry["category"],
            "prefix": prefix,
            "recipe_wikitext": recipe_wt,
            "item_wikitext": item_wt,
        })

    # 5. Save
    result = {
        "crafting_wikitext": crafting_wikitext,
        "supplier_wikitext": supplier_wikitext,
        "items": items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(items)} items → {output}")


if __name__ == "__main__":
    main()
