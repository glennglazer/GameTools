"""Scrape DAO Trap-Making plan data from the Dragon Age Fandom wiki.

Fetches wikitext for all 25 plan pages in the "Dragon Age: Origins Trap-Making plans"
category, plus the Traps section (for the effects table) and the "Locations for
unlimited supplies" section from the main Trap-Making page.

Usage:
    python3 origins_scrape_trap_making.py <output_raw_json>
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

WIKI_API = "https://dragonage.fandom.com/api.php"
CATEGORY = "Category:Dragon Age: Origins Trap-Making plans"
TRAP_MAKING_PAGE = "Trap-Making"
TRAPS_SECTION = 3       # "Traps" on the Trap-Making page
LOCATIONS_SECTION = 2   # "Locations for unlimited supplies"
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


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape DAO Trap-Making plan data from the Fandom wiki"
    )
    ap.add_argument("output", help="Path to write trap_making_raw.json")
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 1. Get all plan page titles from the wiki category ────────────────────
    print("Fetching plan list from category...")
    all_titles = get_category_members(CATEGORY)
    # Filter to pages ending in "Plans" (capital P); excludes "Trap-Making plans" nav page
    plan_pages = sorted(t for t in all_titles if t.endswith("Plans"))
    print(f"  Found {len(plan_pages)} plan pages")

    # ── 2. Fetch wikitext for each plan page ──────────────────────────────────
    plans = []
    for title in plan_pages:
        print(f"  Fetching: {title}")
        try:
            wikitext = get_wikitext(title)
            plans.append({"title": title, "wikitext": wikitext})
        except Exception as exc:
            print(f"  WARNING: could not fetch '{title}': {exc}", file=sys.stderr)
        time.sleep(SLEEP_BETWEEN)

    # ── 3. Fetch Traps section for the effects table ──────────────────────────
    print("Fetching Traps section from Trap-Making page...")
    traps_wikitext = get_section_wikitext(TRAP_MAKING_PAGE, TRAPS_SECTION)

    # ── 4. Fetch Locations section ────────────────────────────────────────────
    print("Fetching locations section from Trap-Making page...")
    locations_wikitext = get_section_wikitext(TRAP_MAKING_PAGE, LOCATIONS_SECTION)

    # ── 5. Save raw output ────────────────────────────────────────────────────
    raw = {
        "plans": plans,
        "traps_wikitext": traps_wikitext,
        "locations_wikitext": locations_wikitext,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(plans)} plans + traps wikitext + locations wikitext → {out_path}")


if __name__ == "__main__":
    main()
