"""Parse Morrowind+Tribunal creature souls from UESP raw HTML into JSON records."""
import argparse
import json
import re
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
    Footnote reference markers like [1] are stripped from creature names.
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
                name = re.sub(r"\[\d+\]", "", li.get_text(strip=True)).strip()
                if name and (name, size) not in seen:
                    records.append({"name": name, "soul_size": size})
                    seen.add((name, size))
    return records


def parse(data: dict) -> list:
    """Parse one or more pages of souls data into deduplicated records.

    Handles both single-page format {"page": ..., "html": ...} and the
    multi-page format {"pages": [{"page": ..., "html": ...}, ...]}.
    """
    pages = data["pages"] if "pages" in data else [data]
    seen: set = set()
    combined: list = []
    for page in pages:
        for r in parse_souls(page["html"]):
            key = (r["name"], r["soul_size"])
            if key not in seen:
                combined.append(r)
                seen.add(key)
    return combined


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse Morrowind+Tribunal souls HTML to JSON.")
    ap.add_argument("infile", nargs="?", default=_DEFAULT_IN)
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    records = parse(data)
    if not records:
        print("ERROR: no souls parsed — check raw file", file=sys.stderr)
        sys.exit(1)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"{len(records)} records → {args.outfile}", file=sys.stderr)
