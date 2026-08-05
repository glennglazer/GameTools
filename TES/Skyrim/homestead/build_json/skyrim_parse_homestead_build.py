"""Parse homestead, main_hall, cellar, wings, and entryway raw JSON
→ wide build record JSON for skyrim_homestead_build.

Five source files feed the single table:
  homestead_raw.json  → Small House, Wing shell, Exterior sections
  main_hall_raw.json  → Main Hall construction + all furnishing sections
  cellar_raw.json     → Cellar furnishing tables + Divine Shrine sections
  wings_raw.json      → All 9 wing room furnishing subsections (Fandom)
  entryway_raw.json   → Main Hall: Entryway (UESP, Type|Options|Materials table)

Crafted components (Nails, Hinge, Iron Fittings, Lock) are NOT included here;
they have their own skyrim_homestead_crafted_components table.

Wing naming convention (canonical build table locations):
  West Wing  (Tower construction type):
    West_Wing                                — shell construction
    West_Wing_Enchanter's_Tower_<subsection> — Enchanter's Tower furnishings
    West_Wing_Bedrooms_<subsection>          — Bedrooms furnishings
    West_Wing_Greenhouse_<subsection>        — Greenhouse furnishings

  North Wing (Room with Outdoor Patio construction type):
    North_Wing                               — shell construction
    North_Wing_Trophy_Room_<subsection>      — Trophy Room furnishings
    North_Wing_Storage_Room_<subsection>     — Storage Room furnishings
    North_Wing_Alchemy_Laboratory_<subsection> — Alchemy Laboratory furnishings

  East Wing  (Downstairs Room construction type):
    East_Wing                                — shell construction
    East_Wing_Library_<subsection>           — Library furnishings
    East_Wing_Armory_<subsection>            — Armory furnishings
    East_Wing_Kitchen_<subsection>           — Kitchen furnishings
"""
import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

from bs4 import BeautifulSoup

MATERIAL_COLS = [
    "sawn_log", "quarried_stone", "nails", "clay", "iron_fittings", "lock", "hinge",
    "iron_ingot", "steel_ingot", "glass", "quicksilver_ingot", "refined_moonstone",
    "filled_grand_soul_gem", "gold_ingot", "leather_strips", "straw", "goat_horns",
    "vampire_dust", "deer_hide", "large_antlers", "small_antlers", "goat_hide",
    "horker_tusk", "mudcrab_chitin", "slaughterfish_scales", "wolf_pelt",
    "sabre_cat_pelt", "sabre_cat_tooth", "sabre_cat_snow_pelt", "bear_pelt",
    "amulet_of_akatosh", "amulet_of_arkay", "amulet_of_dibella", "amulet_of_julianos",
    "amulet_of_kynareth", "amulet_of_mara", "amulet_of_stendarr", "amulet_of_talos",
    "amulet_of_zenithar", "flawless_amethyst", "flawless_sapphire", "corundum_ingot",
    "orichalcum_ingot", "silver_ingot", "ebony_ingot", "refined_malachite",
    "dragon_bone", "dragon_scales",
]

HEADER_TO_COL = {
    "Sawn Log": "sawn_log", "Sawn Logs": "sawn_log",
    "Quarried Stone": "quarried_stone",
    "Nails": "nails", "Clay": "clay",
    "Iron Fittings": "iron_fittings", "Lock": "lock", "Hinge": "hinge",
    "Iron Ingot": "iron_ingot", "Iron Ingots": "iron_ingot",
    "Steel Ingot": "steel_ingot", "Steel Ingots": "steel_ingot",
    "Glass": "glass",
    "Quicksilver Ingot": "quicksilver_ingot",
    "Refined Moonstone": "refined_moonstone",
    "Filled Grand Soul Gem": "filled_grand_soul_gem",
    "Grand Soul Gem": "filled_grand_soul_gem",
    "Gold Ingot": "gold_ingot", "Leather Strips": "leather_strips",
    "Straw": "straw", "Goat Horns": "goat_horns",
    "Vampire Dust": "vampire_dust", "Deer Hide": "deer_hide",
    "Large Antlers": "large_antlers", "Small Antlers": "small_antlers",
    "Goat Hide": "goat_hide", "Horker Tusk": "horker_tusk",
    "Mudcrab Chitin": "mudcrab_chitin", "Slaughterfish Scales": "slaughterfish_scales",
    "Wolf Pelt": "wolf_pelt",
    "Sabre Cat Pelt": "sabre_cat_pelt",
    "Sabre Cat Tooth": "sabre_cat_tooth",
    "Sabre Cat Snow Pelt": "sabre_cat_snow_pelt",
    "Bear Pelt": "bear_pelt",
    "Amulet of Akatosh": "amulet_of_akatosh", "Amulet of Arkay": "amulet_of_arkay",
    "Amulet of Dibella": "amulet_of_dibella", "Amulet of Julianos": "amulet_of_julianos",
    "Amulet of Kynareth": "amulet_of_kynareth", "Amulet of Mara": "amulet_of_mara",
    "Amulet of Stendarr": "amulet_of_stendarr", "Amulet of Talos": "amulet_of_talos",
    "Amulet of Zenithar": "amulet_of_zenithar",
    "Flawless Amethyst": "flawless_amethyst", "Flawless Sapphire": "flawless_sapphire",
    "Corundum Ingot": "corundum_ingot", "Orichalcum Ingot": "orichalcum_ingot",
    "Silver Ingot": "silver_ingot", "Ebony Ingot": "ebony_ingot",
    "Refined Malachite": "refined_malachite",
    "Dragon Bone": "dragon_bone", "Dragon Scales": "dragon_scales",
}

# (source_key, section_index_str, location, parse_type)
# parse_type: 'construction' | 'item_table' | 'shrine_table' | 'shrine_bullet'
#             | 'type_options_table'
SECTION_CONFIG = [
    # ── Homestead_(Hearthfire) ───────────────────────────────────────────────
    ("homestead", "6",  "Small House",  "construction"),
    ("homestead", "24", "West_Wing",    "construction"),
    ("homestead", "25", "North_Wing",   "construction"),
    ("homestead", "26", "East_Wing",    "construction"),
    ("homestead", "35", "Exterior",     "item_table"),   # standard exteriors
    ("homestead", "36", "Exterior",     "item_table"),   # exclusive exteriors

    # ── Main_Hall ───────────────────────────────────────────────────────────
    ("main_hall", "5",  "Main Hall",                                "construction"),
    ("main_hall", "7",  "Main_Hall_Downstairs_Containers",          "item_table"),
    ("main_hall", "8",  "Main_Hall_Downstairs_Furniture",           "item_table"),
    ("main_hall", "9",  "Main_Hall_Downstairs_Weapon_Racks",        "item_table"),
    ("main_hall", "10", "Main_Hall_Downstairs_Shelves",             "item_table"),
    ("main_hall", "11", "Main_Hall_Downstairs_Magical_Workstations","item_table"),
    ("main_hall", "12", "Main_Hall_Downstairs_Illumination",        "item_table"),
    ("main_hall", "13", "Main_Hall_Downstairs_Taxidermy",           "item_table"),
    ("main_hall", "16", "Main_Hall_Upstairs_Containers",            "item_table"),
    ("main_hall", "17", "Main_Hall_Upstairs_Furniture",             "item_table"),
    ("main_hall", "18", "Main_Hall_Upstairs_Weapon_Racks",          "item_table"),
    ("main_hall", "19", "Main_Hall_Upstairs_Shelves",               "item_table"),
    ("main_hall", "20", "Main_Hall_Upstairs_Illumination",          "item_table"),
    ("main_hall", "21", "Main_Hall_Upstairs_Taxidermy",             "item_table"),
    # section 23 (Back Room Furnishings heading) omitted; use subsections 24-28
    ("main_hall", "24", "Main_Hall_Back_Room_Containers",           "item_table"),
    ("main_hall", "25", "Main_Hall_Back_Room_Furniture",            "item_table"),
    ("main_hall", "26", "Main_Hall_Back_Room_Weapon_Racks",         "item_table"),
    ("main_hall", "27", "Main_Hall_Back_Room_Shelves",              "item_table"),
    ("main_hall", "28", "Main_Hall_Back_Room_Miscellaneous",        "item_table"),

    # ── Cellar ──────────────────────────────────────────────────────────────
    ("cellar", "3",  "Cellar_Containers",      "item_table"),
    ("cellar", "4",  "Cellar_Furniture",       "item_table"),
    ("cellar", "5",  "Cellar_Weapon_Racks",    "item_table"),
    ("cellar", "6",  "Cellar_Shelves",         "item_table"),
    ("cellar", "7",  "Cellar_Blacksmith_Items","item_table"),
    ("cellar", "8",  "Cellar_Taxidermy",       "item_table"),
    ("cellar", "9",  "Cellar_Miscellaneous",   "item_table"),
    ("cellar", "10", "Cellar_Divine_Shrines",  "shrine_table"),   # Shrine Base wikitable
    ("cellar", "12", "Cellar_Divine_Shrines",  "shrine_bullet"),  # Shrine of Akatosh
    ("cellar", "13", "Cellar_Divine_Shrines",  "shrine_bullet"),
    ("cellar", "14", "Cellar_Divine_Shrines",  "shrine_bullet"),
    ("cellar", "15", "Cellar_Divine_Shrines",  "shrine_bullet"),
    ("cellar", "16", "Cellar_Divine_Shrines",  "shrine_bullet"),
    ("cellar", "17", "Cellar_Divine_Shrines",  "shrine_bullet"),
    ("cellar", "18", "Cellar_Divine_Shrines",  "shrine_bullet"),
    ("cellar", "19", "Cellar_Divine_Shrines",  "shrine_bullet"),
    ("cellar", "20", "Cellar_Divine_Shrines",  "shrine_bullet"),  # Shrine of Zenithar

    # ── Entryway (UESP Main_Hall section 2) ─────────────────────────────────
    ("entryway", "2", "Entryway", "type_options_table"),

    # ── West Wing furnishings ────────────────────────────────────────────────
    ("enchanters_tower", "4", "West_Wing_Enchanter's_Tower_Containers",    "item_table"),
    ("enchanters_tower", "5", "West_Wing_Enchanter's_Tower_Furniture",     "item_table"),
    ("enchanters_tower", "6", "West_Wing_Enchanter's_Tower_Weapon_Racks",  "item_table"),
    ("enchanters_tower", "7", "West_Wing_Enchanter's_Tower_Shelves",       "item_table"),
    ("enchanters_tower", "8", "West_Wing_Enchanter's_Tower_Exterior",      "item_table"),
    ("enchanters_tower", "9", "West_Wing_Enchanter's_Tower_Miscellaneous", "item_table"),

    ("bedrooms", "4", "West_Wing_Bedrooms_Containers",    "item_table"),
    ("bedrooms", "5", "West_Wing_Bedrooms_Furniture",     "item_table"),
    ("bedrooms", "6", "West_Wing_Bedrooms_Weapon_Racks",  "item_table"),
    ("bedrooms", "7", "West_Wing_Bedrooms_Shelves",       "item_table"),
    ("bedrooms", "8", "West_Wing_Bedrooms_Exterior",      "item_table"),
    ("bedrooms", "9", "West_Wing_Bedrooms_Miscellaneous", "item_table"),

    ("greenhouse", "5", "West_Wing_Greenhouse_Containers",    "item_table"),
    ("greenhouse", "6", "West_Wing_Greenhouse_Furniture",     "item_table"),
    ("greenhouse", "7", "West_Wing_Greenhouse_Shelves",       "item_table"),
    ("greenhouse", "8", "West_Wing_Greenhouse_Horticulture",  "item_table"),
    ("greenhouse", "9", "West_Wing_Greenhouse_Miscellaneous", "item_table"),

    # ── North Wing furnishings ───────────────────────────────────────────────
    ("trophy_room", "4", "North_Wing_Trophy_Room_Containers",    "item_table"),
    ("trophy_room", "5", "North_Wing_Trophy_Room_Furniture",     "item_table"),
    ("trophy_room", "6", "North_Wing_Trophy_Room_Shelves",       "item_table"),
    ("trophy_room", "7", "North_Wing_Trophy_Room_Trophy_Bases",  "item_table"),
    ("trophy_room", "8", "North_Wing_Trophy_Room_Miscellaneous", "item_table"),

    ("storage_room", "4", "North_Wing_Storage_Room_Containers",    "item_table"),
    ("storage_room", "5", "North_Wing_Storage_Room_Furniture",     "item_table"),
    ("storage_room", "6", "North_Wing_Storage_Room_Shelves",       "item_table"),
    ("storage_room", "7", "North_Wing_Storage_Room_Exterior",      "item_table"),
    ("storage_room", "8", "North_Wing_Storage_Room_Miscellaneous", "item_table"),

    ("alchemy_laboratory", "4", "North_Wing_Alchemy_Laboratory_Containers",    "item_table"),
    ("alchemy_laboratory", "5", "North_Wing_Alchemy_Laboratory_Furniture",     "item_table"),
    ("alchemy_laboratory", "6", "North_Wing_Alchemy_Laboratory_Shelves",       "item_table"),
    ("alchemy_laboratory", "7", "North_Wing_Alchemy_Laboratory_Exterior",      "item_table"),
    ("alchemy_laboratory", "8", "North_Wing_Alchemy_Laboratory_Illumination",  "item_table"),
    ("alchemy_laboratory", "9", "North_Wing_Alchemy_Laboratory_Miscellaneous", "item_table"),

    # ── East Wing furnishings ────────────────────────────────────────────────
    ("library", "4", "East_Wing_Library_Containers",    "item_table"),
    ("library", "5", "East_Wing_Library_Furniture",     "item_table"),
    ("library", "6", "East_Wing_Library_Shelves",       "item_table"),
    ("library", "7", "East_Wing_Library_Exterior",      "item_table"),
    ("library", "8", "East_Wing_Library_Miscellaneous", "item_table"),

    ("armory", "4", "East_Wing_Armory_Containers",    "item_table"),
    ("armory", "5", "East_Wing_Armory_Furniture",     "item_table"),
    ("armory", "6", "East_Wing_Armory_Weapon_Racks",  "item_table"),
    ("armory", "7", "East_Wing_Armory_Exterior",      "item_table"),
    ("armory", "8", "East_Wing_Armory_Taxidermy",     "item_table"),
    ("armory", "9", "East_Wing_Armory_Miscellaneous", "item_table"),

    ("kitchen", "4", "East_Wing_Kitchen_Containers",    "item_table"),
    ("kitchen", "5", "East_Wing_Kitchen_Furniture",     "item_table"),
    ("kitchen", "6", "East_Wing_Kitchen_Shelves",       "item_table"),
    ("kitchen", "7", "East_Wing_Kitchen_Miscellaneous", "item_table"),
]


def empty_row(section, location):
    row = {"section": section, "location": location, "batch_size": None}
    for col in MATERIAL_COLS:
        row[col] = 0
    return row


def parse_int(text):
    text = text.strip()
    if not text or text == "-":
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def parse_item_table(soup, location):
    """Wikitable where first cell = item name (th), rest = values (th or td).
    Enumerates duplicate item names with _1, _2, ... suffixes.
    Skips Total and Totals summary rows."""
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    header_tr = table.find("tr")
    header_cells = header_tr.find_all(["th", "td"]) if header_tr else []
    mat_headers = [c.get_text(strip=True) for c in header_cells[1:]]

    seen = OrderedDict()
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        item_name = cells[0].get_text(strip=True)
        if item_name.lower() in ("total", "totals"):
            continue

        row = empty_row(item_name, location)
        for i, hdr in enumerate(mat_headers, 1):
            col = HEADER_TO_COL.get(hdr)
            if col and i < len(cells):
                row[col] = parse_int(cells[i].get_text(strip=True))

        if item_name not in seen:
            seen[item_name] = []
        seen[item_name].append(row)

    result = []
    for item_name, rows in seen.items():
        if len(rows) == 1:
            result.append(rows[0])
        else:
            for i, r in enumerate(rows, 1):
                r["section"] = f"{item_name}_{i}"
                result.append(r)
    return result


def parse_construction_table(soup, location):
    """Wikitable with Stage | Section | mat_col... columns.
    Stage column uses rowspan or empty th for continued stages.
    Stage values are not stored (column dropped); only section names and
    material quantities are recorded."""
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    header_tr = table.find("tr")
    header_ths = header_tr.find_all("th") if header_tr else []
    # header_ths[0]=Stage, header_ths[1]=Section, [2:]=materials
    mat_headers = [th.get_text(strip=True) for th in header_ths[2:]]

    result = []

    for tr in table.find_all("tr")[1:]:
        all_cells = tr.find_all(["th", "td"])
        if not all_cells:
            continue

        first_text = all_cells[0].get_text(strip=True)
        if first_text.lower() in ("total", "totals") or all_cells[0].get("colspan"):
            continue

        tds = tr.find_all("td")
        if not tds:
            continue

        # Normalize whitespace before cleanup (get_text(strip=True) removes
        # spaces between inline tags like "<a>Cellar</a>")
        section_text = " ".join(tds[0].get_text().split())
        section_text = re.sub(r"[†*]", "", section_text)
        section_text = re.sub(r"\s*\(optional\)\s*", "", section_text).strip()

        row = empty_row(section_text, location)
        for i, hdr in enumerate(mat_headers):
            col = HEADER_TO_COL.get(hdr)
            if col and i + 1 < len(tds):
                row[col] = parse_int(tds[i + 1].get_text(strip=True))

        result.append(row)
    return result


def parse_shrine_table(soup, location):
    """Shrine Base wikitable in section 10 — delegate to item_table parser."""
    return parse_item_table(soup, location)


def parse_shrine_bullet(soup, location, section_title):
    """Shrine ingredients from bullet-list: N x Item Name."""
    ul = soup.find("ul")
    if not ul:
        return []

    row = empty_row(section_title, location)
    for li in ul.find_all("li", recursive=False):
        text = li.get_text(strip=True)
        m = re.match(r"^(\d+)\s*x\s*(.+)$", text)
        if m:
            count = int(m.group(1))
            item = m.group(2).strip()
            col = HEADER_TO_COL.get(item)
            if col:
                row[col] = count
    return [row]


def parse_type_options_table(soup, location):
    """Type | Options | Materials | Notes wikitable (entryway / aquarium style).

    Columns vary due to rowspans; the last cell is Notes, second-to-last is
    Materials, third-to-last is the item name (Options column).  Duplicate
    item names are enumerated with _1, _2, ... suffixes.
    """
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    rows = table.find_all("tr")
    # Detect whether row 0 is a colspan title row
    first_row_cells = rows[0].find_all(["th", "td"]) if rows else []
    data_start = 2 if (first_row_cells and first_row_cells[0].get("colspan")) else 1

    name_counts = {}
    records = []

    for row in rows[data_start:]:
        cells = row.find_all(["th", "td"])
        n = len(cells)
        if n < 2:
            continue

        first_text = cells[0].get_text(strip=True).lower()
        if first_text.startswith(("total", "type", "options")):
            continue

        # cells[-3] = name, cells[-2] = materials, cells[-1] = notes
        if n >= 3:
            name_cell = cells[-3]
            materials_cell = cells[-2]
        else:
            name_cell = cells[-2] if n >= 2 else cells[0]
            materials_cell = cells[-1]

        raw_name = re.sub(r"[†*]", "", name_cell.get_text(strip=True)).strip()
        if not raw_name or raw_name.lower() in ("type", "options", "materials", "notes"):
            continue

        mats_text = materials_cell.get_text(strip=True)

        # Enumerate duplicates
        name_counts[raw_name] = name_counts.get(raw_name, 0) + 1
        if name_counts[raw_name] == 2:
            # Retroactively rename the first occurrence
            for r in records:
                if r["section"] == raw_name and r["location"] == location:
                    r["section"] = f"{raw_name}_1"
                    break
        section = (f"{raw_name}_{name_counts[raw_name]}"
                   if name_counts[raw_name] > 1 else raw_name)

        row_rec = empty_row(section, location)
        for item in mats_text.split(","):
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
            col = HEADER_TO_COL.get(mat_name)
            if col:
                row_rec[col] = qty

        records.append(row_rec)

    return records


def load_raw(path):
    """Load a standard {page, fetched, sections:[{index,html,...}]} raw JSON."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {s["index"]: s for s in d["sections"]}


def load_wings_raw(path):
    """Load wings_raw.json → {source_key: {section_index: section_data}}."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    result = {}
    for room_key, room_data in d["rooms"].items():
        result[room_key] = {s["index"]: s for s in room_data["sections"]}
    return result


def main():
    ap = argparse.ArgumentParser(description="Parse homestead build data to JSON")
    ap.add_argument("homestead_json", help="Path to homestead_raw.json")
    ap.add_argument("main_hall_json", help="Path to main_hall_raw.json")
    ap.add_argument("cellar_json",    help="Path to cellar_raw.json")
    ap.add_argument("wings_json",     help="Path to wings_raw.json")
    ap.add_argument("entryway_json",  help="Path to entryway_raw.json")
    ap.add_argument("output_json",    help="Path to output JSON file")
    args = ap.parse_args()

    for p in (args.homestead_json, args.main_hall_json, args.cellar_json,
              args.wings_json, args.entryway_json):
        if not Path(p).exists():
            print(f"ERROR: file not found: {p}", file=sys.stderr)
            sys.exit(1)

    sources = {
        "homestead": load_raw(args.homestead_json),
        "main_hall": load_raw(args.main_hall_json),
        "cellar":    load_raw(args.cellar_json),
        "entryway":  load_raw(args.entryway_json),
    }
    # Merge per-room wing sources into the top-level sources dict
    sources.update(load_wings_raw(args.wings_json))

    all_records = []
    for source_key, section_idx, location, parse_type in SECTION_CONFIG:
        sec_map = sources.get(source_key)
        if sec_map is None:
            print(f"WARNING: source '{source_key}' not found", file=sys.stderr)
            continue
        if section_idx not in sec_map:
            print(f"WARNING: section {section_idx} not found in {source_key}",
                  file=sys.stderr)
            continue

        sec = sec_map[section_idx]
        soup = BeautifulSoup(sec["html"], "html.parser")

        if parse_type == "construction":
            records = parse_construction_table(soup, location)
        elif parse_type in ("item_table", "shrine_table"):
            records = parse_item_table(soup, location)
        elif parse_type == "shrine_bullet":
            records = parse_shrine_bullet(soup, location, sec["title"])
        elif parse_type == "type_options_table":
            records = parse_type_options_table(soup, location)
        else:
            print(f"WARNING: unknown parse_type {parse_type}", file=sys.stderr)
            continue

        all_records.extend(records)
        print(f"  {source_key}/{section_idx} ({location}): {len(records)} records",
              file=sys.stderr)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"Total: {len(all_records)} records → {args.output_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
