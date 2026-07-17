"""Scrape Cellar wiki page and save specified sections as JSON."""
import argparse
import json
import sys
import urllib.request
from datetime import date

UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
BASE = "https://elderscrolls.fandom.com/api.php"
PAGE = "Cellar"

# Sections to fetch:
# 3-10=Cellar furnishing tables (Containers, Furniture, Weapon Racks, etc.)
# 12-20=Individual shrine sections (Akatosh through Zenithar)
# Section 11 ("Per Shrine") is empty — skip
# Section 21 ("All Shrines") is a summary/total table — skip
SECTION_INDICES = [3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20]


def fetch_json(params):
    url = BASE + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def fetch_sections():
    data = fetch_json({"action": "parse", "page": PAGE, "prop": "sections", "format": "json"})
    return data["parse"]["sections"]


def fetch_section_html(idx):
    data = fetch_json({"action": "parse", "page": PAGE, "prop": "text",
                       "section": str(idx), "format": "json"})
    return data["parse"]["text"]["*"]


def main():
    parser = argparse.ArgumentParser(description="Scrape Cellar wiki page")
    parser.add_argument("output", help="Absolute path to output JSON file")
    args = parser.parse_args()

    all_sections = fetch_sections()
    index_to_meta = {int(s["index"]): s for s in all_sections}

    sections = []
    for idx in SECTION_INDICES:
        meta = index_to_meta.get(idx, {})
        html = fetch_section_html(idx)
        sections.append({
            "index": str(idx),
            "number": meta.get("number", ""),
            "title": meta.get("line", ""),
            "html": html,
        })
        print(f"  fetched section {idx}: {meta.get('line', '')}", file=sys.stderr)

    output = {
        "page": PAGE,
        "fetched": str(date.today()),
        "sections": sections,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(sections)} sections to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
