"""Scrape Oblivion spell effects from UESP and save raw HTML sections as JSON."""
import argparse
import json
import sys
from pathlib import Path

import requests

API_URL = "https://en.uesp.net/w/api.php"
PAGE = "Oblivion:Spell_Effects"
USER_AGENT = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"

# Sections 1-6 are the six magic schools; section 7 is Special Spell Effects (excluded).
SCHOOL_SECTIONS = {
    "1": "Alteration",
    "2": "Conjuration",
    "3": "Destruction",
    "4": "Illusion",
    "5": "Mysticism",
    "6": "Restoration",
}

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_OUT = str(_SCRIPT_DIR / "oblivion_enchant_effects_raw.json")


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
    ap = argparse.ArgumentParser(description="Scrape Oblivion spell effects from UESP.")
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    sections = {}
    for section_num, school in SCHOOL_SECTIONS.items():
        sections[section_num] = {
            "school": school,
            "html": fetch(PAGE, section_num),
        }
        print(f"Fetched {school} (section {section_num})", file=sys.stderr)

    record = {"page": PAGE, "sections": sections}
    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(record, f)
    print(f"Saved {args.outfile}", file=sys.stderr)
