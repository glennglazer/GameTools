"""Parse CC Aquarium furnishings from UESP raw JSON → cc_homestead_records.json.

Reads the Aquarium section (Main_Hall page, section 9) which has an unusual
Type | Options | Materials | Notes table format.  Materials are free-text
comma-separated lists like "2 Sawn Log, 4 Nails, Iron Fittings".

Output is appended to skyrim_homestead_build via its SQL loader.
"""
import argparse
import json
import re
import sys
from pathlib import Path

LOCATION = "Main_Hall_Aquarium"

# Material text → DB column name (subset relevant to Aquarium)
MAT_COL = {
    "Sawn Log":       "sawn_log",
    "Quarried Stone": "quarried_stone",
    "Nails":          "nails",
    "Clay":           "clay",
    "Iron Fittings":  "iron_fittings",
    "Iron Ingot":     "iron_ingot",
    "Glass":          "glass",
    "Leather Strips": "leather_strips",
    "Mudcrab Chitin": "mudcrab_chitin",
    "Goat Horns":     "goat_horns",
}

# All material columns in skyrim_homestead_build (must be complete for zero-fill)
ALL_MAT_COLS = [
    "sawn_log", "quarried_stone", "nails", "clay", "iron_fittings", "lock",
    "hinge", "iron_ingot", "steel_ingot", "glass", "quicksilver_ingot",
    "refined_moonstone", "filled_grand_soul_gem", "gold_ingot", "leather_strips",
    "straw", "goat_horns", "vampire_dust", "deer_hide", "large_antlers",
    "small_antlers", "goat_hide", "horker_tusk", "mudcrab_chitin",
    "slaughterfish_scales", "wolf_pelt", "sabre_cat_tooth", "sabre_cat_snow_pelt",
    "bear_pelt", "amulet_of_akatosh", "amulet_of_arkay", "amulet_of_dibella",
    "amulet_of_julianos", "amulet_of_kynareth", "amulet_of_mara",
    "amulet_of_stendarr", "amulet_of_talos", "amulet_of_zenithar",
    "flawless_amethyst", "flawless_sapphire", "corundum_ingot",
    "orichalcum_ingot", "silver_ingot", "ebony_ingot", "refined_malachite",
    "dragon_bone", "dragon_scales",
]

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed", file=sys.stderr)
    sys.exit(1)


def _empty_record(section):
    rec = {"section": section, "location": LOCATION, "stage": None, "batch_size": None}
    for col in ALL_MAT_COLS:
        rec[col] = 0
    return rec


def _parse_materials_text(text):
    """Parse "qty Material, qty Material" into {col: qty} dict."""
    mat_vals = {}
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        m = re.match(r"^(\d+)\s+(.+)", item)
        if m:
            qty = int(m.group(1))
            mat_name = m.group(2).strip()
        else:
            qty = 1
            mat_name = item
        col = MAT_COL.get(mat_name)
        if col:
            mat_vals[col] = qty
    return mat_vals


def parse_aquarium_section(html):
    """Parse Aquarium furnishings table, return list of records."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    rows = table.find_all("tr")
    # Skip row 0 (title colspan), row 1 (column headers)
    data_rows = rows[2:]

    # Track seen section names to enumerate duplicates
    name_counts = {}

    records = []
    for row in data_rows:
        cells = row.find_all(["th", "td"])
        n = len(cells)
        if n < 2:
            continue

        # Skip total row (last row with "Total" text)
        if cells[0].get_text(strip=True).lower().startswith("total"):
            continue

        # Identify Name and Materials columns from right:
        # last cell = Notes, second-to-last = Materials, third-to-last = Name
        if n >= 3:
            notes_cell = cells[-1]
            materials_cell = cells[-2]
            name_cell = cells[-3]
        else:
            materials_cell = cells[-1]
            name_cell = cells[-2] if n >= 2 else cells[0]

        raw_name = name_cell.get_text(strip=True)
        materials_text = materials_cell.get_text(separator=", ", strip=True)

        # Skip header-like or placeholder rows
        if not raw_name or raw_name.lower() in ("type", "options", "materials", "notes"):
            continue
        if raw_name.lower() in ("need icon",):
            continue

        # Enumerate duplicate names
        name_counts[raw_name] = name_counts.get(raw_name, 0) + 1
        section = (f"{raw_name}_{name_counts[raw_name]}"
                   if name_counts[raw_name] > 1 else raw_name)
        # Retroactively rename first occurrence if we see a second
        if name_counts[raw_name] == 2:
            # rename existing record
            for r in records:
                if r["section"] == raw_name and r["location"] == LOCATION:
                    r["section"] = f"{raw_name}_1"
                    break

        mat_vals = _parse_materials_text(materials_text)

        rec = _empty_record(section)
        for col, qty in mat_vals.items():
            rec[col] = qty
        records.append(rec)

    return records


def main():
    ap = argparse.ArgumentParser(
        description="Parse CC Aquarium furnishings from raw JSON → records JSON")
    ap.add_argument("cc_parse_dir", help="Directory containing *_raw.json files")
    ap.add_argument("out_file", help="Output JSON file path")
    args = ap.parse_args()

    parse_dir = Path(args.cc_parse_dir)
    if not parse_dir.exists():
        print(f"ERROR: directory not found: {parse_dir}", file=sys.stderr)
        sys.exit(1)

    raw_path = parse_dir / "main_hall_raw.json"
    if not raw_path.exists():
        print(f"ERROR: main_hall_raw.json not found in {parse_dir}", file=sys.stderr)
        sys.exit(1)

    with open(raw_path) as f:
        data = json.load(f)

    if "9" not in data.get("sections", {}):
        print("ERROR: section 9 (Aquarium) not found in main_hall_raw.json",
              file=sys.stderr)
        sys.exit(1)

    records = parse_aquarium_section(data["sections"]["9"]["html"])
    print(f"  aquarium: {len(records)} furnishing records", file=sys.stderr)

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"{len(records)} Aquarium records → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
