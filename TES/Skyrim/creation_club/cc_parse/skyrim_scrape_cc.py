"""Scrape Creation Club content from UESP wiki via MediaWiki JSON API.

Fetches the specific sections listed in PAGE_CONFIG and saves one JSON file
per page to the output directory.  Each file has the form:
    {
        "page": "Skyrim:Amber",
        "sections": {
            "3": {"title": "Amber Armor", "html": "<div>..."},
            "4": {"title": "Amber Weapons", "html": "<div>..."}
        }
    }

Section "0" fetches the intro content (before the first heading).
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

UESP_API = "https://en.uesp.net/w/api.php"
USER_AGENT = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"

# (page, sections, notes)
# sections: list of section indices as strings; "0" = intro/pre-heading content
PAGE_CONFIG = [
    # ── armor ────────────────────────────────────────────────────────────────
    ("Skyrim:Chitin",        {"armor":       ["4", "7", "8"]}),
    ("Skyrim:Silver",        {"armor":       ["4"]}),
    ("Skyrim:Orcish",        {"armor":       ["5", "6"]}),
    ("Skyrim:Animal_Hides",  {"armor":       ["8"]}),
    ("Skyrim:Iron",          {"armor":       ["5"]}),
    ("Skyrim:Dwarven",       {"armor":       ["5", "6"]}),
    ("Skyrim:Dragon_Items",  {"armor":       ["3", "6"]}),
    ("Skyrim:Steel",         {"armor":       ["6", "10"]}),
    ("Skyrim:Elven",         {"armor":       ["5"],  "weapons": ["6"]}),
    ("Skyrim:Ebony",         {"armor":       ["6"]}),
    ("Skyrim:Daedric",       {"armor":       ["4", "6"], "weapons": ["7"]}),
    ("Skyrim:Stalhrim",      {"armor":       ["6"]}),
    ("Skyrim:Vigil_Armor",   {"armor":       ["0"]}),   # table is in intro
    # ── armor + weapons (new material sets) ──────────────────────────────────
    ("Skyrim:Amber",         {"armor":       ["3"],  "weapons": ["4"]}),
    ("Skyrim:Dark",          {"armor":       ["2"],  "weapons": ["3"]}),
    ("Skyrim:Madness_Ore",   {"armor":       ["3"],  "weapons": ["4"]}),
    ("Skyrim:Golden",        {"armor":       ["2"],  "weapons": ["3"]}),
    # ── ammo + ingredients ────────────────────────────────────────────────────
    ("Skyrim:Rare_Curios_Items",        {"ammo": ["2", "3"], "ingredients": ["4"]}),
    ("Skyrim:Arcane_Archer_Pack_Items", {"ammo": ["1"]}),
    # ── ingredients ───────────────────────────────────────────────────────────
    ("Skyrim:Fishing_Items",   {"ingredients": ["5", "6", "7"]}),
    ("Skyrim:Bittercup_Items", {"ingredients": ["3", "4"]}),
    # ── homestead ─────────────────────────────────────────────────────────────
    ("Skyrim:Main_Hall", {"homestead": ["9"]}),
]

# Derive all needed section numbers per page (union of all target lists)
def _all_sections(targets: dict) -> list[str]:
    seen, out = set(), []
    for secs in targets.values():
        for s in secs:
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


def _page_key(page: str) -> str:
    """Convert 'Skyrim:Chitin' → 'chitin' for use as filename stem."""
    return re.sub(r"[^a-z0-9_]", "_", page.split(":")[-1].lower()).strip("_")


def _fetch(page: str, section: str) -> dict:
    if section == "0":
        url = (f"{UESP_API}?action=parse&page={urllib.request.quote(page)}"
               f"&prop=text&section=0&format=json")
    else:
        url = (f"{UESP_API}?action=parse&page={urllib.request.quote(page)}"
               f"&prop=text&section={section}&format=json")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _section_title(data: dict) -> str:
    return data.get("parse", {}).get("title", "")


def scrape_page(page: str, sections: list[str], out_dir: Path,
                delay: float = 0.5) -> Path:
    """Fetch all requested sections of *page* and write <key>_raw.json."""
    result: dict = {"page": page, "sections": {}}

    for i, sec in enumerate(sections):
        if i > 0:
            time.sleep(delay)
        print(f"  fetching {page} section {sec} …", file=sys.stderr)
        data = _fetch(page, sec)
        html = data["parse"]["text"]["*"]
        # Section title is embedded in the HTML; extract it for reference
        m = re.search(r'class="mw-headline"[^>]*>([^<]+)', html)
        title = m.group(1).strip() if m else f"section_{sec}"
        result["sections"][sec] = {"title": title, "html": html}

    key = _page_key(page)
    out_path = out_dir / f"{key}_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  → {out_path.name} ({len(result['sections'])} sections)",
          file=sys.stderr)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape UESP CC pages → raw JSON files")
    ap.add_argument("out_dir", help="Directory to write raw JSON files into")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="Seconds between API calls (default 0.5)")
    ap.add_argument("--page", metavar="PAGE",
                    help="Scrape only this page (e.g. Skyrim:Amber)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.exists():
        print(f"ERROR: output directory not found: {out_dir}", file=sys.stderr)
        sys.exit(1)

    config = PAGE_CONFIG
    if args.page:
        config = [(p, t) for p, t in PAGE_CONFIG if p == args.page]
        if not config:
            print(f"ERROR: page '{args.page}' not in PAGE_CONFIG",
                  file=sys.stderr)
            sys.exit(1)

    total = 0
    for page, targets in config:
        sections = _all_sections(targets)
        print(f"scraping {page} (sections {sections}) …", file=sys.stderr)
        scrape_page(page, sections, out_dir, delay=args.delay)
        total += 1

    print(f"\nDone. {total} page(s) scraped → {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
