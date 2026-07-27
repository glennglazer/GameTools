"""Scrape Morrowind creature souls pages from UESP and save raw HTML as JSON."""
import argparse
import json
import sys
from pathlib import Path

import requests

API_URL = "https://en.uesp.net/w/api.php"
PAGES = [
    ("Morrowind:Souls", "0"),
    ("Tribunal:Souls",  "0"),
    ("Bloodmoon:Souls", "0"),
]
USER_AGENT = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_OUT = str(_SCRIPT_DIR / "morrowind_souls_raw.json")


def fetch(page: str, section: str = "0") -> str:
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
    ap = argparse.ArgumentParser(description="Scrape Morrowind+Tribunal+Bloodmoon souls from UESP.")
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    pages = []
    for page, section in PAGES:
        html = fetch(page, section)
        pages.append({"page": page, "section": section, "html": html})
        print(f"  {page}: {len(html)} chars", file=sys.stderr)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump({"pages": pages}, f)
    print(f"Saved {len(pages)} pages → {args.outfile}", file=sys.stderr)
