"""Scrape DAO Herbalism recipe and location data from the Fandom wiki.

Fetches wikitext for all 27 herbalism recipe pages from the wiki category,
plus the "Locations for unlimited supplies" section of the main Herbalism page,
and saves everything as a single raw JSON file for the parser to consume.

Usage:
    python3 origins_scrape_herbalism.py <output_raw_json>
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

WIKI_API = "https://dragonage.fandom.com/api.php"
CATEGORY = "Category:Dragon_Age:_Origins_Herbalism_recipes"
HERBALISM_PAGE = "Herbalism"
LOCATIONS_SECTION = 2      # "Locations for unlimited supplies"
CRAFTED_ITEMS_SECTION = 4  # "Herbalism Crafted Items → Dragon Age: Origins"
UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
SLEEP_BETWEEN = 0.3  # seconds; polite rate limiting


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_category_members(category: str) -> list[str]:
    url = (
        f"{WIKI_API}?action=query&list=categorymembers"
        f"&cmtitle={urllib.parse.quote(category)}&cmlimit=500&format=json"
    )
    data = fetch_json(url)
    return [m["title"] for m in data["query"]["categorymembers"]]


def get_wikitext(page: str) -> str:
    url = (
        f"{WIKI_API}?action=parse&page={urllib.parse.quote(page)}"
        f"&prop=wikitext&format=json"
    )
    data = fetch_json(url)
    return data["parse"]["wikitext"]["*"]


def get_section_wikitext(page: str, section: int) -> str:
    url = (
        f"{WIKI_API}?action=parse&page={urllib.parse.quote(page)}"
        f"&prop=wikitext&section={section}&format=json"
    )
    data = fetch_json(url)
    return data["parse"]["wikitext"]["*"]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape DAO Herbalism data from the Fandom wiki"
    )
    ap.add_argument("output", help="Path to write herbalism_raw.json")
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 1. Get all recipe page titles from the wiki category ──────────────────
    print("Fetching recipe list from category...")
    all_titles = get_category_members(CATEGORY)
    recipe_pages = sorted(t for t in all_titles if t.endswith(" Recipe"))
    print(f"  Found {len(recipe_pages)} recipe pages")

    # ── 2. Fetch wikitext for each recipe page ────────────────────────────────
    recipes = []
    for title in recipe_pages:
        print(f"  Fetching: {title}")
        try:
            wikitext = get_wikitext(title)
            recipes.append({"title": title, "wikitext": wikitext})
        except Exception as exc:
            print(f"  WARNING: could not fetch '{title}': {exc}", file=sys.stderr)
        time.sleep(SLEEP_BETWEEN)

    # ── 3. Fetch the Locations section wikitext from the main Herbalism page ──
    print("Fetching locations section from main Herbalism page...")
    locations_wikitext = get_section_wikitext(HERBALISM_PAGE, LOCATIONS_SECTION)

    # ── 4. Fetch the Crafted Items section (DAO subsection) ───────────────────
    print("Fetching crafted items section from main Herbalism page...")
    crafted_items_wikitext = get_section_wikitext(HERBALISM_PAGE, CRAFTED_ITEMS_SECTION)

    # ── 5. Save raw output ────────────────────────────────────────────────────
    raw = {
        "recipes": recipes,
        "locations_wikitext": locations_wikitext,
        "crafted_items_wikitext": crafted_items_wikitext,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(recipes)} recipes + locations + crafted items wikitext → {out_path}")


if __name__ == "__main__":
    main()
