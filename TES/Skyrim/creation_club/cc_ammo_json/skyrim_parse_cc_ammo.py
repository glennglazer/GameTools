"""Parse CC ammo from UESP raw JSON → cc_ammo_records.json.

Sources:
  Rare Curios (arrows sec2, bolts sec3): stats in table, crafting in Notes text.
    All material quantities stored as 0 (not specified in table).
  Arcane Archer (sec1): standard material columns + 'Other' column with qty+mat+batch.
    Bound Arrow is excluded (it's a spell, not craftable).

Output matches the skyrim_smithing_ammo table schema.
"""
import argparse
import json
import re
import sys
from pathlib import Path

AMMO_MAT_COLS = [
    "firewood", "void_salts", "fire_salts", "frost_salts",
    "soul_gem_arrowhead", "dragon_bone", "corkbulb_root", "bonemeal",
]

OTHER_MAT_MAP = {
    "Void Salts":        "void_salts",
    "Fire Salts":        "fire_salts",
    "Frost Salts":       "frost_salts",
    "Soul Gem Arrowheads": "soul_gem_arrowhead",
    "Dragon Bones":      "dragon_bone",
    "Dragon Bone":       "dragon_bone",
    "Corkbulb Root":     "corkbulb_root",
    "Bonemeal":          "bonemeal",
}

PERK_FROM_NOTES = {
    "Dragon Smithing": ["dragon smithing"],
    "Steel Smithing":  ["steel smithing"],
    "Orcish Smithing": ["orcish smithing"],
}

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed", file=sys.stderr)
    sys.exit(1)


def _parse_idref(idall_span):
    idref = idall_span.find("span", class_="idref")
    if idref:
        return idref.get_text(strip=True)
    return idall_span.get_text(strip=True).strip("()")


def _parse_name_id_cell(cell):
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


def _empty_ammo_record(ammo_type):
    rec = {"piece": "", "type": ammo_type,
           "damage": None, "weight": None, "value": None,
           "id": "", "batch_size": None, "material_perk": None}
    for col in AMMO_MAT_COLS:
        rec[col] = 0
    return rec


def _perk_from_notes_text(notes):
    notes_lower = notes.lower()
    for perk, keywords in PERK_FROM_NOTES.items():
        if any(k in notes_lower for k in keywords):
            return perk
    return None


def parse_rare_curios_ammo(html, ammo_type):
    """Parse Rare Curios arrows or bolts section."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    rows = table.find_all("tr")
    records = []
    for row in rows[1:]:  # skip header row 0
        cells = row.find_all(["th", "td"])
        if len(cells) < 5:
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
            damage = int(cells[4].get_text(strip=True).replace(",", ""))
        except ValueError:
            damage = None
        notes = cells[5].get_text(separator=" ", strip=True) if len(cells) > 5 else ""
        material_perk = _perk_from_notes_text(notes)

        for name, id_str in pieces:
            rec = _empty_ammo_record(ammo_type)
            rec["piece"] = name
            rec["id"] = id_str
            rec["damage"] = damage
            rec["weight"] = weight
            rec["value"] = value
            rec["material_perk"] = material_perk
            records.append(rec)
    return records


def parse_arcane_archer_ammo(html):
    """Parse Arcane Archer Pack arrows section."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 3:
        return []

    records = []
    for row in rows[2:]:  # skip 2 header rows
        cells = row.find_all(["th", "td"])
        if len(cells) < 6:
            continue
        pieces = _parse_name_id_cell(cells[1])

        # Exclude Bound Arrow (spell, not craftable)
        pieces = [(n, i) for n, i in pieces if "bound" not in n.lower()]
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

        firewood_qty = 0
        try:
            firewood_qty = int(cells[5].get_text(strip=True))
        except ValueError:
            pass

        # 'Other' column: "qty|material|Makes N arrows" (pipe-separated from BS4)
        other_text = cells[6].get_text(separator="|", strip=True) if len(cells) > 6 else ""
        other_mat_col = None
        other_mat_qty = 0
        batch_size = None

        parts = [p.strip() for p in other_text.split("|") if p.strip()]
        if parts:
            # First part is the quantity
            try:
                other_mat_qty = int(parts[0])
            except ValueError:
                pass
            # Find the material name (second token, sometimes the link text)
            if len(parts) > 1:
                mat_name = parts[1]
                other_mat_col = OTHER_MAT_MAP.get(mat_name)
            # Find "Makes N arrows"
            for part in parts:
                m = re.search(r"Makes\s+(\d+)\s+arrow", part, re.IGNORECASE)
                if m:
                    batch_size = int(m.group(1))
                    break

        # Notes column for material_perk (e.g. "Requires Dragon Smithing perk")
        notes = cells[7].get_text(separator=" ", strip=True) if len(cells) > 7 else ""
        material_perk = _perk_from_notes_text(notes)

        for name, id_str in pieces:
            rec = _empty_ammo_record("arrow")
            rec["piece"] = name
            rec["id"] = id_str
            rec["damage"] = damage
            rec["weight"] = weight
            rec["value"] = value
            rec["batch_size"] = batch_size
            rec["material_perk"] = material_perk
            rec["firewood"] = firewood_qty
            if other_mat_col and other_mat_qty:
                rec[other_mat_col] = other_mat_qty
            records.append(rec)

    return records


def main():
    ap = argparse.ArgumentParser(
        description="Parse CC ammo from raw JSON → records JSON")
    ap.add_argument("cc_parse_dir", help="Directory containing *_raw.json files")
    ap.add_argument("out_file", help="Output JSON file path")
    args = ap.parse_args()

    parse_dir = Path(args.cc_parse_dir)
    if not parse_dir.exists():
        print(f"ERROR: directory not found: {parse_dir}", file=sys.stderr)
        sys.exit(1)

    all_records = []

    rare_path = parse_dir / "rare_curios_items_raw.json"
    if rare_path.exists():
        with open(rare_path) as f:
            rare_data = json.load(f)
        for sec, ammo_type in [("2", "arrow"), ("3", "bolt")]:
            if sec in rare_data.get("sections", {}):
                recs = parse_rare_curios_ammo(
                    rare_data["sections"][sec]["html"], ammo_type)
                all_records.extend(recs)
                print(f"  rare_curios/sec{sec} ({ammo_type}s): {len(recs)} items",
                      file=sys.stderr)
    else:
        print("WARNING: rare_curios_items_raw.json not found", file=sys.stderr)

    arcane_path = parse_dir / "arcane_archer_pack_items_raw.json"
    if arcane_path.exists():
        with open(arcane_path) as f:
            arcane_data = json.load(f)
        if "1" in arcane_data.get("sections", {}):
            recs = parse_arcane_archer_ammo(arcane_data["sections"]["1"]["html"])
            all_records.extend(recs)
            print(f"  arcane_archer/sec1 (arrows): {len(recs)} items", file=sys.stderr)
    else:
        print("WARNING: arcane_archer_pack_items_raw.json not found", file=sys.stderr)

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{len(all_records)} total ammo records → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
