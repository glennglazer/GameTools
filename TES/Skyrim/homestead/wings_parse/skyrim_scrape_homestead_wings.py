"""Scrape all 9 wing furnishing pages from the Fandom Elder Scrolls wiki.

Fetches the furnishing subsection HTML for each wing room and saves the
combined result as wings_raw.json, keyed by source name.

Wing rooms and their Fandom pages:
  West Wing  (Tower construction type):
    enchanters_tower  → Enchanter%27s_Tower_%28Skyrim%29  sections 4-9
    bedrooms          → Bedrooms                           sections 4-9
    greenhouse        → Greenhouse                         sections 5-9 (section 4 is heading only)

  North Wing (Room with Outdoor Patio construction type):
    trophy_room       → Trophy_Room                        sections 4-8
    storage_room      → Storage_Room                       sections 4-8
    alchemy_laboratory→ Alchemy_Laboratory_%28Skyrim%29    sections 4-9

  East Wing  (Downstairs Room construction type):
    library           → Library                            sections 4-8
    armory            → Armory_%28Hearthfire%29            sections 4-9
    kitchen           → Kitchen                            sections 4-7
"""
import argparse
import json
import sys
import urllib.request
from datetime import date

UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
BASE = "https://elderscrolls.fandom.com/api.php"

# (source_key, fandom_page_title, furnishing_section_indices)
WING_PAGES = [
    # West Wing
    ("enchanters_tower",   "Enchanter%27s_Tower_%28Skyrim%29",  [4, 5, 6, 7, 8, 9]),
    ("bedrooms",           "Bedrooms",                           [4, 5, 6, 7, 8, 9]),
    ("greenhouse",         "Greenhouse",                         [5, 6, 7, 8, 9]),
    # North Wing
    ("trophy_room",        "Trophy_Room",                        [4, 5, 6, 7, 8]),
    ("storage_room",       "Storage_Room",                       [4, 5, 6, 7, 8]),
    ("alchemy_laboratory", "Alchemy_Laboratory_%28Skyrim%29",    [4, 5, 6, 7, 8, 9]),
    # East Wing
    ("library",            "Library",                            [4, 5, 6, 7, 8]),
    ("armory",             "Armory_%28Hearthfire%29",            [4, 5, 6, 7, 8, 9]),
    ("kitchen",            "Kitchen",                            [4, 5, 6, 7]),
]


def fetch_json(params):
    url = BASE + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def fetch_section_meta(page):
    data = fetch_json({"action": "parse", "page": page, "prop": "sections", "format": "json"})
    return {int(s["index"]): s for s in data["parse"]["sections"]}


def fetch_section_html(page, idx):
    data = fetch_json({"action": "parse", "page": page,
                       "prop": "text", "section": str(idx), "format": "json"})
    return data["parse"]["text"]["*"]


def main():
    parser = argparse.ArgumentParser(
        description="Scrape wing furnishing pages from Fandom wiki")
    parser.add_argument("output", help="Absolute path to output wings_raw.json")
    args = parser.parse_args()

    rooms = {}
    for source_key, page, section_indices in WING_PAGES:
        print(f"  scraping {source_key} ({page})...", file=sys.stderr)
        meta = fetch_section_meta(page)
        sections = []
        for idx in section_indices:
            html = fetch_section_html(page, idx)
            m = meta.get(idx, {})
            sections.append({
                "index": str(idx),
                "number": m.get("number", ""),
                "title": m.get("line", ""),
                "html": html,
            })
            print(f"    section {idx}: {m.get('line', '')}", file=sys.stderr)
        rooms[source_key] = {
            "page": page,
            "sections": sections,
        }

    output = {
        "source": "Fandom Elder Scrolls wiki",
        "fetched": str(date.today()),
        "rooms": rooms,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(rooms)} wing rooms to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
