"""Scrape Skyrim creature souls from UESP Skyrim:Souls and save raw HTML as JSON."""
import argparse
import json
import sys
from pathlib import Path

import requests

API_URL = "https://en.uesp.net/w/api.php"
PAGE = "Skyrim:Souls"
USER_AGENT = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_OUT = str(_SCRIPT_DIR / "skyrim_creature_souls_uesp_raw.json")


def fetch(page: str) -> str:
    resp = requests.get(
        API_URL,
        params={"action": "parse", "page": page, "prop": "text", "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["parse"]["text"]["*"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape Skyrim creature souls from UESP.")
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    html = fetch(PAGE)
    record = {"page": PAGE, "html": html}
    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(record, f)
    print(f"Saved {len(html)} chars → {args.outfile}", file=sys.stderr)
