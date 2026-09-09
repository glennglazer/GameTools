"""Scrape DAO:A Poison-Making (poisons + grenades) recipe and effects data from the Fandom wiki.

Fetches wikitext for all 4 recipe pages in the "Dragon Age: Origins - Awakening
Poison-Making recipes" category, plus the Awakening section (section 5) of the
main Poison-Making page for effects data and grenade classification.

There is no separate Awakening supply section on the wiki; supply will be empty.

Usage:
    python3 awakening_scrape_poisons_grenades.py <output_raw_json>
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
CATEGORY = "Category:Dragon Age: Origins - Awakening Poison-Making recipes"
POISON_MAKING_PAGE = "Poison-Making"
AWAKENING_SECTION = 5   # "Dragon Age: Origins - Awakening" section
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


def extract_awakening_grenade_results(wikitext: str) -> list[str]:
    """Extract the Tier Four grenade result names from the Awakening section wikitext.

    Looks for the 'Tier Four Grenades' table and pulls all [[Name]] links
    from data rows within it.
    """
    m = re.search(
        r"Tier Four Grenades(.*?)(?:\n\|\}|$)",
        wikitext,
        re.DOTALL,
    )
    block = m.group(1) if m else ""
    return re.findall(r"^\|\s*\[\[([^\]|]+)\]\]", block, re.MULTILINE)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape DAO:A Poison-Making recipe data from the Fandom wiki"
    )
    ap.add_argument("output", help="Path to write poisons_grenades_raw.json")
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 1. Get all recipe page titles from the wiki category ──────────────────
    print("Fetching recipe list from category...")
    all_titles = get_category_members(CATEGORY)
    # Filter to pages ending in "Recipe"; excludes the nav page "Poison-Making recipes"
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

    # ── 3. Fetch Awakening section for effects and grenade classification ──────
    print("Fetching Awakening section from Poison-Making page...")
    awakening_wikitext = get_section_wikitext(POISON_MAKING_PAGE, AWAKENING_SECTION)
    grenade_results = extract_awakening_grenade_results(awakening_wikitext)
    print(f"  Identified {len(grenade_results)} Tier Four grenade results: {grenade_results}")

    # ── 4. Save raw output ────────────────────────────────────────────────────
    raw = {
        "recipes": recipes,
        "grenade_results": grenade_results,
        "awakening_effects_wikitext": awakening_wikitext,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(recipes)} recipes + grenade list + effects wikitext → {out_path}")


if __name__ == "__main__":
    main()
