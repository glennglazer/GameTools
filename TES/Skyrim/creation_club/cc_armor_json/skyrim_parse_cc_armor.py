"""Parse CC armor sections from UESP raw JSON → cc_armor_records.json.

Reads raw JSON files produced by skyrim_scrape_cc.py and outputs records
compatible with the skyrim_smithing_armor table schema.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ── section config ─────────────────────────────────────────────────────────────
# (page_key, section_id, material_perk)
ARMOR_SECTIONS = [
    ("chitin",       "4",  "Advanced Armors"),
    ("chitin",       "7",  "Advanced Armors"),
    ("chitin",       "8",  "Advanced Armors"),
    ("silver",       "4",  "Advanced Armors"),
    ("orcish",       "5",  "Orcish Smithing"),
    ("orcish",       "6",  "Orcish Smithing"),
    ("animal_hides", "8",  None),
    ("iron",         "5",  None),
    ("dwarven",      "5",  "Dwarven Smithing"),
    ("dwarven",      "6",  "Dwarven Smithing"),
    ("dragon_items", "3",  "Dragon Smithing"),
    ("dragon_items", "6",  "Dragon Smithing"),
    ("steel",        "6",  "Steel Smithing"),
    ("steel",        "10", "Steel Smithing"),
    ("elven",        "5",  "Elven Smithing"),
    ("ebony",        "6",  "Ebony Smithing"),
    ("daedric",      "4",  "Daedric Smithing"),
    ("daedric",      "6",  "Daedric Smithing"),
    ("stalhrim",     "6",  "Ebony Smithing"),
    ("vigil_armor",  "0",  "Steel Smithing"),
    ("amber",        "3",  "Glass Smithing"),
    ("dark",         "2",  "Daedric Smithing"),
    ("madness_ore",  "3",  "Ebony Smithing"),
    ("golden",       "2",  "Daedric Smithing"),
]

# Material columns in skyrim_smithing_armor (alphabetical order as in DB)
ARMOR_MAT_COLS = [
    "bone_meal", "chitin_plate", "corundum_ingot", "daedra_heart",
    "dragon_bone", "dragon_scales", "dwarven_metal_ingot", "ebony_ingot",
    "iron_ingot", "leather", "leather_strips", "netch_jelly", "netch_leather",
    "orichalcum_ingot", "quicksilver_ingot", "refined_malachite",
    "refined_moonstone", "stalhrim", "steel_ingot", "void_salts",
    "refined_amber", "madness_ingot", "gold_ingot", "silver_ingot",
]

# ── material header text → DB column name ─────────────────────────────────────
MAT_COL = {
    # abbreviated headers (text in header row 2)
    "Iron":            "iron_ingot",
    "Corundum":        "corundum_ingot",
    "Steel":           "steel_ingot",
    "Orichalcum":      "orichalcum_ingot",
    "Dwarven":         "dwarven_metal_ingot",
    "Quicksilver":     "quicksilver_ingot",
    "Moonstone":       "refined_moonstone",
    "Malachite":       "refined_malachite",
    "Gold":            "gold_ingot",
    "Ebony":           "ebony_ingot",
    "Silver":          "silver_ingot",
    "Madness":         "madness_ingot",
    "Amber":           "refined_amber",
    "Chitin":          "chitin_plate",
    "Dragon Scales":   "dragon_scales",
    "Dragon Bone":     "dragon_bone",
    "Stalhrim":        "stalhrim",
    "Leather":         "leather",
    "Strips":          "leather_strips",
    "N Leather":       "netch_leather",
    "Daedra Heart":    "daedra_heart",
    "Bone Meal":       "bone_meal",
    # full names (from img alt text in icon-only headers)
    "Leather Strips":      "leather_strips",
    "Netch Leather":       "netch_leather",
    "Iron Ingot":          "iron_ingot",
    "Ebony Ingot":         "ebony_ingot",
    "Steel Ingot":         "steel_ingot",
    "Corundum Ingot":      "corundum_ingot",
    "Orichalcum Ingot":    "orichalcum_ingot",
    "Quicksilver Ingot":   "quicksilver_ingot",
    "Gold Ingot":          "gold_ingot",
    "Silver Ingot":        "silver_ingot",
    "Refined Moonstone":   "refined_moonstone",
    "Refined Malachite":   "refined_malachite",
    "Dwarven Metal Ingot": "dwarven_metal_ingot",
}

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed", file=sys.stderr)
    sys.exit(1)


# ── HTML parsing helpers ───────────────────────────────────────────────────────

def _header_name(cell):
    """Extract material name from a header cell (text or img alt)."""
    txt = cell.get_text(strip=True)
    if txt:
        return txt
    img = cell.find("img")
    if img and img.get("alt"):
        return img["alt"]
    a = cell.find("a")
    if a and a.get("title"):
        return a["title"]
    return ""


def _parse_idref(idall_span):
    """Extract the ID string from <span class='idall'>...</span>."""
    idref = idall_span.find("span", class_="idref")
    if idref:
        return idref.get_text(strip=True)
    return idall_span.get_text(strip=True).strip("()")


def _parse_name_id_cell(cell):
    """Return list of (name, id) tuples from a name+id table cell."""
    anchor_spans = cell.find_all("span", id=True)
    idall_spans = cell.find_all("span", class_="idall")

    if anchor_spans:
        results = []
        for anchor, idall in zip(anchor_spans, idall_spans):
            ns = anchor.next_sibling
            name = ns.strip() if isinstance(ns, str) else anchor["id"].replace("_", " ")
            results.append((name, _parse_idref(idall)))
        return results

    # Daedric-style: plain text before <br>, no anchor span
    parts = []
    for child in cell.children:
        if hasattr(child, "name") and child.name == "br":
            break
        if isinstance(child, str):
            parts.append(child.strip())
    name = "".join(parts).strip()
    id_str = _parse_idref(idall_spans[0]) if idall_spans else ""
    return [(name, id_str)]


def _parse_qty(text):
    t = text.strip().replace(",", "")
    if not t or t in ("-", "—", "(?)", ""):
        return 0
    try:
        return int(float(t))
    except (ValueError, TypeError):
        return 0


def _empty_armor_record(material_perk):
    rec = {"piece": "", "material_perk": material_perk,
           "armor_rating": None, "weight": None, "value": None, "id": ""}
    for col in ARMOR_MAT_COLS:
        rec[col] = 0
    return rec


# ── section parser ─────────────────────────────────────────────────────────────

def parse_armor_section(html, material_perk):
    """Parse one armor wikitable section, return list of records."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 3:
        return []

    # Determine material count and column names from header rows
    row0_cells = rows[0].find_all(["th", "td"])
    n_mats = 0
    for cell in row0_cells:
        if "Raw" in cell.get_text(strip=True):
            n_mats = int(cell.get("colspan", 0))
            break

    row1_cells = rows[1].find_all(["th", "td"])
    mat_headers = [_header_name(row1_cells[i]) for i in range(n_mats)]
    mat_db_cols = [MAT_COL.get(h) for h in mat_headers]

    # Armor fixed columns: 0=icon, 1=name+id, 2=weight, 3=value, 4=armor_rating
    FIXED = 5

    records = []
    for row in rows[2:]:
        if "sortbottom" in row.get("class", []):
            continue
        cells = row.find_all(["th", "td"])
        if len(cells) < FIXED:
            continue

        pieces = _parse_name_id_cell(cells[1])
        try:
            weight = float(cells[2].get_text(strip=True).replace(",", ""))
        except ValueError:
            weight = None
        try:
            value = int(cells[3].get_text(strip=True).replace(",", ""))
        except ValueError:
            value = None
        try:
            armor_rating = int(cells[4].get_text(strip=True).replace(",", ""))
        except ValueError:
            armor_rating = None

        mat_vals = {}
        for i, col in enumerate(mat_db_cols):
            if col and FIXED + i < len(cells):
                mat_vals[col] = _parse_qty(cells[FIXED + i].get_text(strip=True))

        for name, id_str in pieces:
            rec = _empty_armor_record(material_perk)
            rec["piece"] = name
            rec["id"] = id_str
            rec["weight"] = weight
            rec["value"] = value
            rec["armor_rating"] = armor_rating
            for col, qty in mat_vals.items():
                rec[col] = qty
            records.append(rec)

    return records


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Parse CC armor sections from raw JSON → records JSON")
    ap.add_argument("cc_parse_dir", help="Directory containing *_raw.json files")
    ap.add_argument("out_file", help="Output JSON file path")
    args = ap.parse_args()

    parse_dir = Path(args.cc_parse_dir)
    if not parse_dir.exists():
        print(f"ERROR: directory not found: {parse_dir}", file=sys.stderr)
        sys.exit(1)

    all_records = []
    seen_pages = {}  # page_key → loaded data

    for page_key, section_id, material_perk in ARMOR_SECTIONS:
        raw_path = parse_dir / f"{page_key}_raw.json"
        if not raw_path.exists():
            print(f"WARNING: {raw_path.name} not found, skipping", file=sys.stderr)
            continue

        if page_key not in seen_pages:
            with open(raw_path) as f:
                seen_pages[page_key] = json.load(f)

        data = seen_pages[page_key]
        if section_id not in data.get("sections", {}):
            print(f"WARNING: section {section_id} not in {raw_path.name}", file=sys.stderr)
            continue

        html = data["sections"][section_id]["html"]
        records = parse_armor_section(html, material_perk)
        all_records.extend(records)
        print(f"  {page_key}/{section_id}: {len(records)} pieces", file=sys.stderr)

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{len(all_records)} total armor records → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
