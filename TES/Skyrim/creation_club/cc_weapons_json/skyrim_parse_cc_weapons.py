"""Parse CC weapons sections from UESP raw JSON → cc_weapons_records.json.

Reads raw JSON files produced by skyrim_scrape_cc.py and outputs records
compatible with the skyrim_smithing_weapons table schema.

For Elven and Daedric pages only crossbow items are included.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ── section config ─────────────────────────────────────────────────────────────
# (page_key, section_id, material_perk, crossbow_only)
WEAPONS_SECTIONS = [
    ("elven",       "6",  "Elven Smithing",    True),   # crossbows only
    ("daedric",     "7",  "Daedric Smithing",  True),   # crossbows only
    ("amber",       "4",  "Glass Smithing",    False),
    ("dark",        "3",  "Daedric Smithing",  False),
    ("madness_ore", "4",  "Ebony Smithing",    False),
    ("golden",      "3",  "Daedric Smithing",  False),
]

WEAPONS_MAT_COLS = [
    "corundum_ingot", "crossbow", "daedra_heart", "dragon_bone",
    "dwarven_crossbow", "dwarven_metal_ingot", "ebony_ingot", "firewood",
    "iron_ingot", "leather_strips", "orichalcum_ingot", "quicksilver_ingot",
    "refined_malachite", "refined_moonstone", "stalhrim", "steel_ingot",
    "refined_amber", "madness_ingot", "gold_ingot",
    "elven_crossbow", "daedric_crossbow",
]

MAT_COL = {
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
    "Strips":          "leather_strips",
    "Daedra Heart":    "daedra_heart",
    "Firewood":        "firewood",
    "Dragon Bone":     "dragon_bone",
    "Leather Strips":  "leather_strips",
    "Iron Ingot":      "iron_ingot",
    "Ebony Ingot":     "ebony_ingot",
    "Elven Crossbow":  "elven_crossbow",
    "Daedric Crossbow": "daedric_crossbow",
}

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed", file=sys.stderr)
    sys.exit(1)


# ── HTML parsing helpers (shared pattern, see cc_armor_json parser) ─────────────

def _header_name(cell):
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
    idref = idall_span.find("span", class_="idref")
    if idref:
        return idref.get_text(strip=True)
    return idall_span.get_text(strip=True).strip("()")


def _parse_name_id_cell(cell):
    """Return list of (name, id) from a standard name+id cell."""
    anchor_spans = cell.find_all("span", id=True)
    idall_spans = cell.find_all("span", class_="idall")

    if anchor_spans:
        results = []
        for anchor, idall in zip(anchor_spans, idall_spans):
            ns = anchor.next_sibling
            name = ns.strip() if isinstance(ns, str) else anchor["id"].replace("_", " ")
            results.append((name, _parse_idref(idall)))
        return results

    parts = []
    for child in cell.children:
        if hasattr(child, "name") and child.name == "br":
            break
        if isinstance(child, str):
            parts.append(child.strip())
    name = "".join(parts).strip()
    id_str = _parse_idref(idall_spans[0]) if idall_spans else ""
    return [(name, id_str)]


def _parse_id_only_cell(cell):
    """Parse an ID-only cell (split-format tables like Madness/Golden)."""
    idall = cell.find("span", class_="idall")
    if idall:
        return _parse_idref(idall)
    return cell.get_text(strip=True).strip("()")


def _parse_qty(text):
    t = text.strip().replace(",", "")
    if not t or t in ("-", "—", "(?)"):
        return 0
    try:
        return int(float(t))
    except (ValueError, TypeError):
        return 0


def _parse_other_col(text, mat_vals):
    """Parse the free-text 'Other' material column into mat_vals dict."""
    text = text.strip()
    if not text:
        return
    m = re.match(r"^(\d+)\s*(.+)", text)
    if m:
        qty = int(m.group(1))
        mat_name = m.group(2).strip()
        col = MAT_COL.get(mat_name)
        if col:
            mat_vals[col] = qty


def _empty_weapons_record(material_perk):
    rec = {"piece": "", "material_perk": material_perk,
           "damage": None, "weight": None, "value": None, "id": ""}
    for col in WEAPONS_MAT_COLS:
        rec[col] = 0
    return rec


# ── section parser ─────────────────────────────────────────────────────────────

def parse_weapons_section(html, material_perk, crossbow_only=False):
    """Parse one weapons wikitable section, return list of records."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 3:
        return []

    row0_cells = rows[0].find_all(["th", "td"])

    # Detect split format (Madness/Golden): first header cell text = 'Name'
    split_format = row0_cells[0].get_text(strip=True) == "Name"

    # Count material columns from colspan of 'Raw Materials' cell
    n_mats = 0
    for cell in row0_cells:
        if "Raw" in cell.get_text(strip=True):
            n_mats = int(cell.get("colspan", 0))
            break

    row1_cells = rows[1].find_all(["th", "td"])
    mat_headers = [_header_name(row1_cells[i]) for i in range(n_mats)]

    # Last mat header may be 'Other' — handle separately
    has_other = mat_headers and mat_headers[-1] == "Other"
    regular_mat_headers = mat_headers[:-1] if has_other else mat_headers
    mat_db_cols = [MAT_COL.get(h) for h in regular_mat_headers]

    # Fixed columns: 8 (icon, name+id, weight, value, damage, crit, speed, reach)
    # For split format: (name, id, weight, value, damage, crit, speed, reach)
    FIXED = 8

    records = []
    for row in rows[2:]:
        if "sortbottom" in row.get("class", []):
            continue
        cells = row.find_all(["th", "td"])
        if len(cells) < FIXED:
            continue

        if split_format:
            name = cells[0].get_text(strip=True)
            id_str = _parse_id_only_cell(cells[1])
            pieces = [(name, id_str)]
        else:
            pieces = _parse_name_id_cell(cells[1])

        if crossbow_only:
            pieces = [(n, i) for n, i in pieces if "crossbow" in n.lower()]
        if not pieces:
            continue

        try:
            weight = float(cells[2].get_text(strip=True).replace(",", ""))
        except ValueError:
            weight = None
        try:
            value = int(cells[3].get_text(strip=True).replace(",", ""))
        except ValueError:
            value = None
        try:
            damage = int(cells[4].get_text(strip=True).replace(",", ""))
        except ValueError:
            damage = None

        # Material columns start at index 8
        mat_vals = {}
        for i, col in enumerate(mat_db_cols):
            idx = FIXED + i
            if col and idx < len(cells):
                mat_vals[col] = _parse_qty(cells[idx].get_text(strip=True))

        # 'Other' column (if present) is the last regular mat column
        if has_other:
            other_idx = FIXED + len(regular_mat_headers)
            if other_idx < len(cells):
                _parse_other_col(cells[other_idx].get_text(strip=True), mat_vals)

        for name, id_str in pieces:
            rec = _empty_weapons_record(material_perk)
            rec["piece"] = name
            rec["id"] = id_str
            rec["weight"] = weight
            rec["value"] = value
            rec["damage"] = damage
            for col, qty in mat_vals.items():
                rec[col] = qty
            records.append(rec)

    return records


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Parse CC weapons sections from raw JSON → records JSON")
    ap.add_argument("cc_parse_dir", help="Directory containing *_raw.json files")
    ap.add_argument("out_file", help="Output JSON file path")
    args = ap.parse_args()

    parse_dir = Path(args.cc_parse_dir)
    if not parse_dir.exists():
        print(f"ERROR: directory not found: {parse_dir}", file=sys.stderr)
        sys.exit(1)

    all_records = []
    seen_pages = {}

    for page_key, section_id, material_perk, crossbow_only in WEAPONS_SECTIONS:
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
        records = parse_weapons_section(html, material_perk, crossbow_only)
        all_records.extend(records)
        label = f" (crossbows only)" if crossbow_only else ""
        print(f"  {page_key}/{section_id}{label}: {len(records)} pieces", file=sys.stderr)

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{len(all_records)} total weapons records → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
