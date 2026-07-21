"""Parse Morrowind creature souls from UESP raw HTML into JSON records."""
import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "souls_parse" / "morrowind_souls_raw.json")
_DEFAULT_OUT = str(_SCRIPT_DIR / "morrowind_souls_records.json")


def parse_souls(html: str) -> list:
    """Extract (name, soul_size) pairs from all wikitables on the page.

    The page groups creatures by the soul gem type that best fits them.
    Each table has header rows (colspan th = gem name) and data rows
    (numeric th = soul strength, td cells = creature name lists).
    """
    soup = BeautifulSoup(html, "html.parser")
    records = []
    seen = set()
    for table in soup.find_all("table", class_="wikitable"):
        for row in table.find_all("tr"):
            th = row.find("th")
            if not th or th.get("colspan"):
                continue
            try:
                size = int(th.get_text(strip=True))
            except ValueError:
                continue
            for li in row.find_all("li"):
                name = li.get_text(strip=True)
                if name and (name, size) not in seen:
                    records.append({"name": name, "soul_size": size})
                    seen.add((name, size))
    return records


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse Morrowind souls HTML to JSON.")
    ap.add_argument("infile", nargs="?", default=_DEFAULT_IN)
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    records = parse_souls(data["html"])
    if not records:
        print("ERROR: no souls parsed — check raw file", file=sys.stderr)
        sys.exit(1)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"{len(records)} records → {args.outfile}", file=sys.stderr)
