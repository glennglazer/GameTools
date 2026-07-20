"""Parse Morrowind alchemy apparatus from UESP raw HTML → morrowind_apparatus_records.json.

Reads morrowind_apparatus_raw.json produced by morrowind_scrape_apparatus.py and
outputs records for morrowind_alchemy_apparatus.

Table structure: rows with exactly 8 td cells are data rows.
  c0: item image (skip)
  c1: Object ID (e.g. apparatus_a_mortar_01)
  c2: Name (may contain decorated spans; whitespace-normalised)
  c3: Type (skip)
  c4: Weight
  c5: Value
  c6: Quality
  c7: Count (skip)
Rows with fewer cells are collapsible location rows (skip).
"""
import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "apparatus_parse" / "morrowind_apparatus_raw.json")
_DEFAULT_OUT = str(_SCRIPT_DIR / "morrowind_apparatus_records.json")


def parse_apparatus(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if table is None:
        raise ValueError("No wikitable found in HTML")

    records = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 8:
            continue  # header row or collapsible location row
        item_id = cells[1].get_text(strip=True)
        name = " ".join(cells[2].get_text().split())
        weight = float(cells[4].get_text(strip=True))
        value = int(cells[5].get_text(strip=True))
        quality = float(cells[6].get_text(strip=True))
        records.append({
            "id": item_id,
            "name": name,
            "weight": weight,
            "value": value,
            "quality": quality,
        })
    return records


def main():
    ap = argparse.ArgumentParser(
        description="Parse Morrowind apparatus raw JSON → records JSON")
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
