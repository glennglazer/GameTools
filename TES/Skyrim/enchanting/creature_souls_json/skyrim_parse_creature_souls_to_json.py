"""Parse Skyrim creature souls from UESP raw HTML into JSON records.

Source: Skyrim:Souls page (fetched by souls_parse/skyrim_scrape_creature_souls.py).
Produces integer soul sizes from the page's mapping table.
Handles rowspan rows (creatures with multiple soul levels).
Skips leveled souls and 'No soul' entries. Adds a generic NPC entry (Black/3000).
"""
import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "souls_parse" / "skyrim_creature_souls_uesp_raw.json")
_DEFAULT_OUT = str(_SCRIPT_DIR / "skyrim_enchant_souls.json")

_SKIP_PREFIXES = ("Leveled", "No soul")


def _is_fixed(level: str) -> bool:
    return not any(level.startswith(p) for p in _SKIP_PREFIXES)


def parse_mapping(soup: BeautifulSoup) -> dict:
    """Return {soul_level_name: int} from the Charge Capacity mapping table."""
    for table in soup.find_all("table", class_="wikitable"):
        headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
        if "Charge Capacity" not in headers:
            continue
        mapping = {}
        cap_idx = headers.index("Charge Capacity")
        level_idx = headers.index("Soul Level") if "Soul Level" in headers else 0
        for row in table.find_all("tr")[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) <= cap_idx:
                continue
            level = cells[level_idx].get_text(strip=True)
            try:
                capacity = int(cells[cap_idx].get_text(strip=True))
            except ValueError:
                continue
            mapping[level] = capacity
        if mapping:
            return mapping
    raise ValueError("No Charge Capacity mapping table found in Skyrim:Souls HTML")


def parse_souls(soup: BeautifulSoup, mapping: dict) -> list:
    """Return [{name, soul_size}] from the creature table, handling rowspan.

    Creatures with multiple soul levels (e.g., Draugr Deathlord: Common/Greater/Grand)
    produce one record per fixed soul level.  Parenthetical qualifiers like
    '(Shaman)' and '(Other)' are stripped before mapping.
    """
    creature_table = None
    for table in soup.find_all("table", class_="wikitable"):
        headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
        if "Creature" in headers and "Soul Level" in headers:
            creature_table = table
            break
    if creature_table is None:
        raise ValueError("No creature/soul-level table found in Skyrim:Souls HTML")

    records = []
    seen = set()
    current_name = None

    for row in creature_table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        if len(cells) >= 2:
            # New creature row: first cell is name (may have rowspan), second is level.
            name_cell = cells[0]
            for sup in name_cell.find_all("sup"):
                sup.decompose()
            current_name = name_cell.get_text(strip=True)
            level_text = cells[1].get_text(strip=True)
        else:
            # Continuation row for a rowspan creature: single cell is the level.
            level_text = cells[0].get_text(strip=True)

        if not current_name or not _is_fixed(level_text):
            continue

        level_clean = re.sub(r"\s*\(.*?\)", "", level_text).strip()
        if level_clean not in mapping:
            continue

        soul_size = mapping[level_clean]
        key = (current_name, soul_size)
        if key not in seen:
            records.append({"name": current_name, "soul_size": soul_size})
            seen.add(key)

    # NPCs have Black souls; Black soul gems share Grand capacity.
    black_size = mapping.get("Grand", 3000)
    records.append({"name": "NPC", "soul_size": black_size})
    return records


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse Skyrim creature souls to JSON.")
    ap.add_argument("infile", nargs="?", default=_DEFAULT_IN)
    ap.add_argument("outfile", nargs="?", default=_DEFAULT_OUT)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    soup = BeautifulSoup(data["html"], "html.parser")
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    if not records:
        print("ERROR: no souls parsed — check raw file", file=sys.stderr)
        sys.exit(1)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"{len(records)} records → {args.outfile}", file=sys.stderr)
