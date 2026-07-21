"""Parse Oblivion creature souls from UESP raw HTML into JSON records."""
import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "souls_parse" / "oblivion_souls_raw.json")
_DEFAULT_OUT = str(_SCRIPT_DIR / "oblivion_souls_records.json")

# Fixed soul levels: anything not in this set is leveled or undefined and skipped.
FIXED_LEVELS = {"Petty", "Lesser", "Common", "Greater", "Grand", "Black"}


def parse_mapping(html: str) -> dict:
    """Return {soul_level_name: integer_value} from the Soul Strengths table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if table is None:
        raise ValueError("No wikitable found in mapping HTML")
    mapping = {}
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        level = cells[0].get_text(strip=True)
        try:
            value = int(cells[1].get_text(strip=True))
        except ValueError:
            continue
        mapping[level] = value
    return mapping


def parse_souls(html: str, mapping: dict) -> list:
    """Return [{name, soul_size}] from all four wikitables in the creatures HTML.

    Covers: standard A-N, standard N-Z/NPCs, location-specific, quest creatures.
    Rows whose soul level is not in FIXED_LEVELS (leveled, 'none', etc.) are skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    records = []
    seen = set()
    for table in soup.find_all("table", class_="wikitable"):
        for row in table.find_all("tr")[1:]:
            tds = row.find_all("td")
            if len(tds) < 2:
                continue
            name = tds[0].get_text(strip=True)
            soul_label = tds[1].get_text(strip=True)
            if soul_label not in FIXED_LEVELS:
                continue
            soul_size = mapping[soul_label]
            if (name, soul_size) not in seen:
                records.append({"name": name, "soul_size": soul_size})
                seen.add((name, soul_size))
    return records


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse Oblivion souls HTML to JSON.")
    ap.add_argument("infile", nargs="?", default=_DEFAULT_IN)
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    mapping = parse_mapping(data["mapping_html"])
    records = parse_souls(data["creatures_html"], mapping)
    if not records:
        print("ERROR: no souls parsed — check raw file", file=sys.stderr)
        sys.exit(1)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"{len(records)} records → {args.outfile}", file=sys.stderr)
