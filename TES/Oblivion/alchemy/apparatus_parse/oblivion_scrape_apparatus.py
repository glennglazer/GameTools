"""Scrape Oblivion:Miscellaneous_Items §Alchemy Equipment from UESP → oblivion_apparatus_raw.json."""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

UESP_API = "https://en.uesp.net/w/api.php"
USER_AGENT = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
PAGE = "Oblivion:Miscellaneous_Items"
SECTION = "2"  # Alchemy Equipment section

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_OUT = str(_SCRIPT_DIR / "oblivion_apparatus_raw.json")


def fetch_section(page: str, section: str) -> str:
    url = (f"{UESP_API}?action=parse&page={urllib.request.quote(page)}"
           f"&prop=text&section={section}&format=json")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["parse"]["text"]["*"]


def main():
    ap = argparse.ArgumentParser(
        description="Scrape Oblivion alchemy apparatus section → raw JSON")
    ap.add_argument("out_file", nargs="?", default=_DEFAULT_OUT,
                    help="Output JSON file (default: oblivion_apparatus_raw.json)")
    args = ap.parse_args()

    print(f"Fetching {PAGE} section {SECTION} …", file=sys.stderr)
    html = fetch_section(PAGE, SECTION)

    out = {"page": PAGE, "section": SECTION, "html": html}
    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"→ {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
