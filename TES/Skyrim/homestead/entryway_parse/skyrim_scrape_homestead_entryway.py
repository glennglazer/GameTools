"""Scrape the Main Hall: Entryway section from UESP wiki.

The Fandom wiki does not cover the optional step of converting the Small House
into an Entryway after the Main Hall is built.  The UESP wiki has this data
at Skyrim:Main_Hall section 2 ("Main Hall: Entryway").

Output: entryway_raw.json with a single section entry (index "2").
"""
import argparse
import json
import sys
import urllib.request
from datetime import date

UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
BASE = "https://en.uesp.net/w/api.php"
PAGE = "Skyrim:Main_Hall"
SECTION_INDEX = 2   # "Main Hall: Entryway"


def fetch_json(params):
    url = BASE + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Main Hall: Entryway section from UESP wiki")
    parser.add_argument("output", help="Absolute path to output entryway_raw.json")
    args = parser.parse_args()

    # Fetch section metadata
    meta_data = fetch_json({"action": "parse", "page": PAGE,
                            "prop": "sections", "format": "json"})
    meta = {int(s["index"]): s for s in meta_data["parse"]["sections"]}

    # Fetch entryway section HTML
    html_data = fetch_json({"action": "parse", "page": PAGE, "prop": "text",
                            "section": str(SECTION_INDEX), "format": "json"})
    html = html_data["parse"]["text"]["*"]

    m = meta.get(SECTION_INDEX, {})
    print(f"  fetched section {SECTION_INDEX}: {m.get('line', '')}", file=sys.stderr)

    output = {
        "page": PAGE,
        "source": "UESP",
        "fetched": str(date.today()),
        "sections": [{
            "index": str(SECTION_INDEX),
            "number": m.get("number", ""),
            "title": m.get("line", ""),
            "html": html,
        }],
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved entryway section to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
