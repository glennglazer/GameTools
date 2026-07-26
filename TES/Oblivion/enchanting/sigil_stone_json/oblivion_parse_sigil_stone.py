"""Parse Oblivion sigil stone data from UESP raw HTML into three JSON record files."""
import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_IN = str(_SCRIPT_DIR.parent / "sigil_stone_parse" / "oblivion_sigil_stone_raw.json")
_DEFAULT_OUT_STONES = str(_SCRIPT_DIR / "sigil_stone_records.json")
_DEFAULT_OUT_WEAPONS = str(_SCRIPT_DIR / "sigil_stone_weapon_magnitudes.json")
_DEFAULT_OUT_ARMOR = str(_SCRIPT_DIR / "sigil_stone_armor_magnitudes.json")

LEVELS = ["descendent", "subjacent", "latent", "ascendent", "transcendent"]


def _extract_name(td) -> str:
    """Return clean effect name from a table cell (strips duration/footnote suffixes)."""
    link = td.find("a")
    if link:
        return link.get_text(strip=True)
    return td.get_text(strip=True)


def _extract_form_id(td) -> str:
    """Return 8-character uppercase Form ID from a Form ID cell (e.g. '00041FB1')."""
    idref = td.find(class_="idref")
    if idref:
        return idref.get_text(separator="", strip=True).upper()
    # Fallback: strip parens from cell text
    text = td.get_text(separator="", strip=True)
    return text.strip("()").replace(" ", "").upper()


def _parse_weapon_cell(td):
    """Return (magnitude, charges) from a weapon magnitude cell.

    Handles formats:
    - "5 pts (880/22=40)"       → (5, 40)
    - "level 2 (=10 pts) ..."   → (2, 45)   [use level, not pts]
    - "5 secs (1200/15=80)"     → (5, 80)
    - "-"                       → (None, None)
    """
    text = td.get_text(separator=" ", strip=True)
    if text == "-" or not re.search(r"\d", text):
        return None, None

    # Magnitude: first integer in cell text (works for both "5 pts" and "level 2")
    m = re.search(r"(\d+)", text)
    magnitude = int(m.group(1)) if m else None

    # Charges: final "=N" inside the <small> tag
    small = td.find("small")
    charges = None
    if small:
        cm = re.search(r"=(\d+)", small.get_text())
        if cm:
            charges = int(cm.group(1))

    return magnitude, charges


def _parse_armor_cell(td):
    """Return magnitude from an armor magnitude cell, or None for '-'."""
    text = td.get_text(strip=True)
    if text == "-":
        return None
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def parse(html: str):
    """Parse the Effects and Magnitudes wikitable.

    Returns (stones, weapon_magnitudes, armor_magnitudes) as lists of dicts.
    Each list has 150 records (30 stone groups × 5 levels).
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if table is None:
        raise ValueError("No wikitable found in HTML")

    rows = table.find_all("tr")
    stones = []
    weapon_mags = []
    armor_mags = []

    i = 0
    while i < len(rows):
        row = rows[i]
        # Skip header rows (contain <th> elements)
        if row.find("th"):
            i += 1
            continue

        tds = row.find_all("td")
        if len(tds) != 11:
            i += 1
            continue

        # Weapon row: tds[0]=effect, tds[1,3,5,7,9]=magnitudes, tds[2,4,6,8,10]=form IDs
        weapon_effect = _extract_name(tds[0])
        form_ids = [_extract_form_id(tds[2 + j * 2]) for j in range(5)]
        weapon_data = [_parse_weapon_cell(tds[1 + j * 2]) for j in range(5)]

        # Armor row must immediately follow
        if i + 1 >= len(rows):
            i += 1
            continue
        armor_tds = rows[i + 1].find_all("td")
        if len(armor_tds) != 6:
            i += 1
            continue

        armor_effect = _extract_name(armor_tds[0])
        armor_data = [_parse_armor_cell(armor_tds[1 + j]) for j in range(5)]

        for j, level in enumerate(LEVELS):
            fid = form_ids[j]
            wm, wc = weapon_data[j]
            am = armor_data[j]

            stones.append({
                "form_id": fid,
                "weapon_effect": weapon_effect,
                "armor_effect": armor_effect,
            })

            wmag = {"form_id": fid}
            for lv in LEVELS:
                wmag[f"{lv}_magnitude"] = None
                wmag[f"{lv}_charges"] = None
            wmag[f"{level}_magnitude"] = wm
            wmag[f"{level}_charges"] = wc
            weapon_mags.append(wmag)

            amag = {"form_id": fid}
            for lv in LEVELS:
                amag[f"{lv}_magnitude"] = None
            amag[f"{level}_magnitude"] = am
            armor_mags.append(amag)

        i += 2  # consumed both weapon and armor rows

    return stones, weapon_mags, armor_mags


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse Oblivion sigil stone HTML to JSON.")
    ap.add_argument("infile", nargs="?", default=_DEFAULT_IN)
    ap.add_argument("--out-stones",  default=_DEFAULT_OUT_STONES)
    ap.add_argument("--out-weapons", default=_DEFAULT_OUT_WEAPONS)
    ap.add_argument("--out-armor",   default=_DEFAULT_OUT_ARMOR)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        data = json.load(f)

    stones, weapon_mags, armor_mags = parse(data["html"])

    if not stones:
        print("ERROR: no sigil stone records parsed — check raw file", file=sys.stderr)
        sys.exit(1)

    for path, records, label in [
        (args.out_stones,  stones,      "stones"),
        (args.out_weapons, weapon_mags, "weapon magnitudes"),
        (args.out_armor,   armor_mags,  "armor magnitudes"),
    ]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        print(f"{len(records)} {label} → {path}", file=sys.stderr)
