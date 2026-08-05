"""Parse homestead steward costs from the Trivia section of homestead_raw.json.

Room names are mapped to the location-prefix conventions used in
skyrim_homestead_build so that a JOIN on `build.location LIKE cost.room || '%'`
returns all furnishing rows for the steward's coverage area.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# Map wiki Trivia room names → build-table location prefixes.
# The steward cost room names match the common prefix of the location column
# values in skyrim_homestead_build for that room's furnishing rows.
ROOM_NAME_MAP = {
    "Small House":        "Small House",
    "Entry Room Upgrade": "Entryway",
    "Main Hall":          "Main Hall",
    "Enchanter's Tower":  "West_Wing_Enchanter's_Tower",
    "Bedrooms":           "West_Wing_Bedrooms",
    "Greenhouse":         "West_Wing_Greenhouse",
    "Trophy Room":        "North_Wing_Trophy_Room",
    "Storage Room":       "North_Wing_Storage_Room",
    "Alchemy Laboratory": "North_Wing_Alchemy_Laboratory",
    "Library":            "East_Wing_Library",
    "Armory":             "East_Wing_Armory",
    "Kitchen":            "East_Wing_Kitchen",
    "Cellar":             "Cellar",
}


def parse_steward_costs(html):
    """Find the nested steward-cost list in the Trivia section HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Find the <li> whose text mentions paying the steward
    steward_li = None
    for li in soup.find_all("li"):
        if "pay the steward" in li.get_text().lower():
            steward_li = li
            break

    if steward_li is None:
        print("ERROR: could not find steward cost list in Trivia HTML", file=sys.stderr)
        sys.exit(1)

    nested_ul = steward_li.find("ul")
    if nested_ul is None:
        print("ERROR: no nested <ul> found inside steward <li>", file=sys.stderr)
        sys.exit(1)

    records = []
    for cost_li in nested_ul.find_all("li", recursive=False):
        # Text like "Small House: 1,000 Gold" or "Enchanter's Tower: 2,500 ..."
        text = " ".join(cost_li.get_text().split())
        m = re.match(r"^(.+?):\s*([\d,]+)", text)
        if not m:
            continue
        room = m.group(1).strip()
        gold = int(m.group(2).replace(",", ""))
        # Map to build-table location prefix; keep original name if unmapped
        room = ROOM_NAME_MAP.get(room, room)
        records.append({"room": room, "gold_cost": gold})

    return records


def main():
    ap = argparse.ArgumentParser(
        description="Parse homestead steward costs to JSON")
    ap.add_argument("homestead_json", help="Path to homestead_raw.json")
    ap.add_argument("output_json",    help="Path to output JSON file")
    args = ap.parse_args()

    src = Path(args.homestead_json)
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        sys.exit(1)

    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    # Section 41 is Trivia
    trivia_section = next(
        (s for s in data["sections"] if s["index"] == "41"), None
    )
    if trivia_section is None:
        print("ERROR: section 41 (Trivia) not found in homestead_raw.json",
              file=sys.stderr)
        sys.exit(1)

    records = parse_steward_costs(trivia_section["html"])
    if not records:
        print("ERROR: no steward cost records parsed", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output_json)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(records)} steward cost records to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
