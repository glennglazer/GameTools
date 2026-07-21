"""Scrape Oblivion creature souls page from UESP and save raw HTML as JSON."""
import argparse
import json
import sys
from pathlib import Path

import requests

API_URL = "https://en.uesp.net/w/api.php"
PAGE = "Oblivion:Souls"
SECTION_CREATURES = "1"   # Souls Alphabetically
SECTION_MAPPING = "3"     # Soul Strengths (name → integer value)
USER_AGENT = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_OUT = str(_SCRIPT_DIR / "oblivion_souls_raw.json")


def fetch(page: str, section: str) -> str:
    resp = requests.get(
        API_URL,
        params={"action": "parse", "page": page, "prop": "text",
                "section": section, "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["parse"]["text"]["*"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape Oblivion souls from UESP.")
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    creatures_html = fetch(PAGE, SECTION_CREATURES)
    mapping_html = fetch(PAGE, SECTION_MAPPING)
    record = {
        "page": PAGE,
        "section_creatures": SECTION_CREATURES,
        "section_mapping": SECTION_MAPPING,
        "creatures_html": creatures_html,
        "mapping_html": mapping_html,
    }
    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(record, f)
    print(f"Saved {args.outfile}", file=sys.stderr)
