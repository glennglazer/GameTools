"""Scrape Homestead_(Hearthfire) wiki page and save specified sections as JSON."""
import argparse
import json
import sys
import urllib.request
from datetime import date

UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
BASE = "https://elderscrolls.fandom.com/api.php"
PAGE = "Homestead_%28Hearthfire%29"

# Sections to fetch by index (determined by prior survey of section list):
# 6=Stage 3 Small House, 24=Tower, 25=Room with Outdoor Patio, 26=Downstairs Room,
# 35=Standard exterior totals, 36=Exclusive exteriors, 41=Trivia
SECTION_INDICES = [6, 24, 25, 26, 35, 36, 41]


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
    parser = argparse.ArgumentParser(description="Scrape Homestead wiki page")
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
