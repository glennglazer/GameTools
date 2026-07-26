"""Parse Oblivion spell effects from UESP raw HTML into JSON records."""
import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN  = str(_SCRIPT_DIR.parent / "enchant_effects_parse" / "oblivion_enchant_effects_raw.json")
_DEFAULT_OUT = str(_SCRIPT_DIR / "oblivion_enchant_effects.json")


def _clean_description(td) -> str:
    """Return the description text with inline link words space-separated and trimmed."""
    raw = td.get_text(separator=" ", strip=True)
    text = re.sub(r" +", " ", raw).strip()
    # Remove spaces inserted before punctuation by the separator (e.g. "word ." → "word.")
    return re.sub(r" +([.,;:!?])", r"\1", text)


def parse_section(html: str, school: str) -> list:
    """Parse one school's wikitable into a list of effect dicts."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if table is None:
        raise ValueError(f"No wikitable found in HTML for school '{school}'")

    records = []
    for row in table.find_all("tr"):
        tds = row.find_all("td")
        # Data rows: Effect Name in <th scope="row">, then 4 td cells:
        # Effect ID, Base Cost, Barter Factor, Description.
        if len(tds) < 4:
            continue

        name_th      = row.find(attrs={"scope": "row"})
        name         = name_th.get_text(separator=" ", strip=True) if name_th else ""
        effect_id    = tds[0].get_text(strip=True)
        raw_cost     = tds[1].get_text(strip=True)
        raw_barter   = tds[2].get_text(strip=True)
        description  = _clean_description(tds[3])

        try:
            base_cost = float(raw_cost)
        except ValueError:
            base_cost = None

        try:
            barter_factor = float(raw_barter)
        except ValueError:
            barter_factor = None

        if not effect_id:
            continue

        records.append({
            "name":          name,
            "effect_id":     effect_id,
            "base_cost":     base_cost,
            "barter_factor": barter_factor,
            "school":        school,
            "description":   description,
        })

    return records


def parse(data: dict) -> list:
    """Parse all school sections and return a flat list of effect records."""
    all_records = []
    for section_num, section in data["sections"].items():
        records = parse_section(section["html"], section["school"])
        all_records.extend(records)
    return all_records


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse Oblivion enchant effects HTML to JSON.")
    ap.add_argument("infile",  nargs="?", default=_DEFAULT_IN)
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    records = parse(data)
    if not records:
        print("ERROR: no records parsed — check raw file", file=sys.stderr)
        sys.exit(1)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"{len(records)} records → {args.outfile}", file=sys.stderr)
