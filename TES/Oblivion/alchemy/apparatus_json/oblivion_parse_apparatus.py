"""Parse Oblivion alchemy apparatus from UESP raw HTML → oblivion_apparatus_records.json.

Reads oblivion_apparatus_raw.json produced by oblivion_scrape_apparatus.py and
outputs records for oblivion_alchemy_apparatus.

Table structure: first wikitable in section 2 (Alchemy Equipment).
Each item spans multiple rows via rowspan on the image, name, and notes cells.

First row of each item: 8 td cells
  c0: image (rowspan, skip)
  c1: name with span id (rowspan)
  c2: grade
  c3: id (idall/idref span)
  c4: weight
  c5: cost
  c6: strength
  c7: notes (rowspan, skip)

Subsequent rows: 5 td cells
  c0: grade
  c1: id (idall/idref span)
  c2: weight
  c3: cost
  c4: strength

The second table in this section (level progression chart) is ignored.
"""
import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "apparatus_parse" / "oblivion_apparatus_raw.json")
_DEFAULT_OUT = str(_SCRIPT_DIR / "oblivion_apparatus_records.json")


def parse_apparatus(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")  # first table only
    if table is None:
        raise ValueError("No wikitable found in HTML")

    records = []
    current_name = None

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue  # header row (th cells only)

        if len(cells) == 8:
            current_name = " ".join(cells[1].get_text().split())
            grade = cells[2].get_text(strip=True)
            item_id = cells[3].get_text(strip=True)
            weight = float(cells[4].get_text(strip=True))
            cost = int(cells[5].get_text(strip=True))
            strength = float(cells[6].get_text(strip=True))
        elif len(cells) == 5:
            grade = cells[0].get_text(strip=True)
            item_id = cells[1].get_text(strip=True)
            weight = float(cells[2].get_text(strip=True))
            cost = int(cells[3].get_text(strip=True))
            strength = float(cells[4].get_text(strip=True))
        else:
            continue

        if current_name is None:
            continue  # safety guard

        records.append({
            "name": current_name,
            "grade": grade,
            "id": item_id,
            "weight": weight,
            "cost": cost,
            "strength": strength,
        })

    return records


def main():
    ap = argparse.ArgumentParser(
        description="Parse Oblivion apparatus raw JSON → records JSON")
    ap.add_argument("in_file", nargs="?", default=_DEFAULT_IN,
                    help="Input raw JSON file")
    ap.add_argument("out_file", nargs="?", default=_DEFAULT_OUT,
                    help="Output records JSON file")
    args = ap.parse_args()

    in_path = Path(args.in_file)
    if not in_path.exists():
        print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    with open(in_path, encoding="utf-8") as f:
        raw = json.load(f)

    records = parse_apparatus(raw["html"])

    out_path = Path(args.out_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(records)} apparatus records → {out_path}")


if __name__ == "__main__":
    main()
