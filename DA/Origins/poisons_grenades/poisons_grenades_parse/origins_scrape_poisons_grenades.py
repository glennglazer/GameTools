"""Scrape DAO Poison-Making (poisons + grenades) recipe and location data from the Fandom wiki.

Fetches wikitext for all 25 recipe pages in the "Dragon Age: Origins Poison-Making recipes"
category, plus the Grenades section (to identify which results are grenades) and the
"Locations for unlimited supplies" section from the main Poison-Making page.

Usage:
    python3 origins_scrape_poisons_grenades.py <output_raw_json>
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

WIKI_API = "https://dragonage.fandom.com/api.php"
CATEGORY = "Category:Dragon Age: Origins Poison-Making recipes"
POISON_MAKING_PAGE = "Poison-Making"
GRENADES_SECTION = 4       # "Grenades" on the Poison-Making page
LOCATIONS_SECTION = 2      # "Locations for unlimited supplies"
UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
SLEEP_BETWEEN = 0.3


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


def extract_tier2_grenade_results(grenades_wikitext: str) -> list[str]:
    """Extract the Tier Two grenade result names from the Grenades section.

    Tier Four grenades belong to Dragon Age: Origins - Awakening and are excluded.
    """
    # Isolate the Tier Two block (between "Tier Two Grenades" and "Tier Four Grenades")
    m = re.search(
        r"Tier Two Grenades(.*?)(?:Tier Four Grenades|$)",
        grenades_wikitext,
        re.DOTALL,
    )
    block = m.group(1) if m else grenades_wikitext

    # Each grenade appears as: | [[Name]] || ...
    return re.findall(r"^\|\s*\[\[([^\]|]+)\]\]", block, re.MULTILINE)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape DAO Poison-Making recipe data from the Fandom wiki"
    )
    ap.add_argument("output", help="Path to write poisons_grenades_raw.json")
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 1. Get all recipe page titles from the wiki category ──────────────────
    print("Fetching recipe list from category...")
    all_titles = get_category_members(CATEGORY)
    # Filter to pages ending in "Recipe"; excludes the "Poison-Making recipes" nav page
    recipe_pages = sorted(t for t in all_titles if t.endswith("Recipe"))
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

    # ── 3. Fetch Grenades section to identify grenade result names ────────────
    print("Fetching Grenades section from Poison-Making page...")
    grenades_wikitext = get_section_wikitext(POISON_MAKING_PAGE, GRENADES_SECTION)
    grenade_results = extract_tier2_grenade_results(grenades_wikitext)
    print(f"  Identified {len(grenade_results)} Tier Two grenade results: {grenade_results}")

    # ── 4. Fetch Locations section ────────────────────────────────────────────
    print("Fetching locations section from Poison-Making page...")
    locations_wikitext = get_section_wikitext(POISON_MAKING_PAGE, LOCATIONS_SECTION)

    # ── 5. Save raw output ────────────────────────────────────────────────────
    raw = {
        "recipes": recipes,
        "grenade_results": grenade_results,
        "locations_wikitext": locations_wikitext,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(recipes)} recipes + grenade list + locations → {out_path}")


if __name__ == "__main__":
    main()
