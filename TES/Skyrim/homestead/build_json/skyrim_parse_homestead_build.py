"""Parse homestead, main_hall, and cellar raw JSON → wide build record JSON.

Three source pages feed the single skyrim_homestead_build table:
  homestead_raw.json  → Small House, Wing, Exterior sections
  main_hall_raw.json  → Main Hall construction + all furnishing sections
  cellar_raw.json     → Cellar furnishing tables + Divine Shrine sections
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
    "sabre_cat_tooth", "sabre_cat_snow_pelt", "bear_pelt", "amulet_of_akatosh",
    "amulet_of_arkay", "amulet_of_dibella", "amulet_of_julianos", "amulet_of_kynareth",
    "amulet_of_mara", "amulet_of_stendarr", "amulet_of_talos", "amulet_of_zenithar",
    "flawless_amethyst", "flawless_sapphire", "corundum_ingot", "orichalcum_ingot",
    "silver_ingot", "ebony_ingot", "refined_malachite", "dragon_bone", "dragon_scales",
]

HEADER_TO_COL = {
    "Sawn Log": "sawn_log", "Sawn Logs": "sawn_log",
    "Quarried Stone": "quarried_stone",
    "Nails": "nails", "Clay": "clay",
    "Iron Fittings": "iron_fittings", "Lock": "lock", "Hinge": "hinge",
    "Iron Ingot": "iron_ingot", "Iron Ingots": "iron_ingot",
    "Steel Ingot": "steel_ingot", "Glass": "glass",
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
    "Wolf Pelt": "wolf_pelt", "Sabre Cat Tooth": "sabre_cat_tooth",
    "Sabre Cat Snow Pelt": "sabre_cat_snow_pelt", "Bear Pelt": "bear_pelt",
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
SECTION_CONFIG = [
    # ── Homestead_(Hearthfire) ───────────────────────────────────────────────
    ("homestead", "6",  "Small House",            "construction"),
    ("homestead", "24", "Tower",                  "construction"),
    ("homestead", "25", "Room with Outdoor Patio","construction"),
    ("homestead", "26", "Downstairs Room",        "construction"),
    ("homestead", "35", "Exterior",               "item_table"),   # standard exteriors
    ("homestead", "36", "Exterior",               "item_table"),   # exclusive exteriors

    # ── Main_Hall ───────────────────────────────────────────────────────────
    ("main_hall", "5",  "Main Hall",                               "construction"),
    ("main_hall", "7",  "Main_Hall_Downstairs_Containers",         "item_table"),
    ("main_hall", "8",  "Main_Hall_Downstairs_Furniture",          "item_table"),
    ("main_hall", "9",  "Main_Hall_Downstairs_Weapon_Racks",       "item_table"),
    ("main_hall", "10", "Main_Hall_Downstairs_Shelves",            "item_table"),
    ("main_hall", "11", "Main_Hall_Downstairs_Magical_Workstations","item_table"),
    ("main_hall", "12", "Main_Hall_Downstairs_Illumination",       "item_table"),
    ("main_hall", "13", "Main_Hall_Downstairs_Taxidermy",          "item_table"),
    ("main_hall", "16", "Main_Hall_Upstairs_Containers",           "item_table"),
    ("main_hall", "17", "Main_Hall_Upstairs_Furniture",            "item_table"),
    ("main_hall", "18", "Main_Hall_Upstairs_Weapon_Racks",         "item_table"),
    ("main_hall", "19", "Main_Hall_Upstairs_Shelves",              "item_table"),
    ("main_hall", "20", "Main_Hall_Upstairs_Illumination",         "item_table"),
    ("main_hall", "21", "Main_Hall_Upstairs_Taxidermy",            "item_table"),
    # section 23 (Back Room Furnishings heading) omitted; use subsections 24-28
    ("main_hall", "24", "Main_Hall_Back_Room_Containers",          "item_table"),
    ("main_hall", "25", "Main_Hall_Back_Room_Furniture",           "item_table"),
    ("main_hall", "26", "Main_Hall_Back_Room_Weapon_Racks",        "item_table"),
    ("main_hall", "27", "Main_Hall_Back_Room_Shelves",             "item_table"),
    ("main_hall", "28", "Main_Hall_Back_Room_Miscellaneous",       "item_table"),

    # ── Cellar ──────────────────────────────────────────────────────────────
    ("cellar", "3",  "Cellar_Containers",     "item_table"),
    ("cellar", "4",  "Cellar_Furniture",      "item_table"),
    ("cellar", "5",  "Cellar_Weapon_Racks",   "item_table"),
    ("cellar", "6",  "Cellar_Shelves",        "item_table"),
    ("cellar", "7",  "Cellar_Blacksmith_Items","item_table"),
    ("cellar", "8",  "Cellar_Taxidermy",      "item_table"),
    ("cellar", "9",  "Cellar_Miscellaneous",  "item_table"),
    ("cellar", "10", "Cellar_Divine_Shrines", "shrine_table"),   # Shrine Base wikitable
    ("cellar", "12", "Cellar_Divine_Shrines", "shrine_bullet"),  # Shrine of Akatosh
    ("cellar", "13", "Cellar_Divine_Shrines", "shrine_bullet"),
    ("cellar", "14", "Cellar_Divine_Shrines", "shrine_bullet"),
    ("cellar", "15", "Cellar_Divine_Shrines", "shrine_bullet"),
    ("cellar", "16", "Cellar_Divine_Shrines", "shrine_bullet"),
    ("cellar", "17", "Cellar_Divine_Shrines", "shrine_bullet"),
    ("cellar", "18", "Cellar_Divine_Shrines", "shrine_bullet"),
    ("cellar", "19", "Cellar_Divine_Shrines", "shrine_bullet"),
    ("cellar", "20", "Cellar_Divine_Shrines", "shrine_bullet"),  # Shrine of Zenithar
]


def empty_row(section, location, stage=None):
    row = {"section": section, "location": location, "stage": stage, "batch_size": None}
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
    Enumerates duplicate item names with _1, _2, ... suffixes."""
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
        if item_name.lower() == "total":
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
    Stage column uses rowspan or empty th for continued stages."""
    table = soup.find("table", class_="wikitable")
    if not table:
        return []

    header_tr = table.find("tr")
    header_ths = header_tr.find_all("th") if header_tr else []
    # header_ths[0]=Stage, header_ths[1]=Section, [2:]=materials
    mat_headers = [th.get_text(strip=True) for th in header_ths[2:]]

    current_stage = None
    result = []

    for tr in table.find_all("tr")[1:]:
        all_cells = tr.find_all(["th", "td"])
        if not all_cells:
            continue

        first_text = all_cells[0].get_text(strip=True)
        if first_text.lower() == "total" or all_cells[0].get("colspan"):
            continue

        ths = tr.find_all("th")
        tds = tr.find_all("td")

        if ths:
            stage_text = ths[0].get_text(strip=True)
            if stage_text:
                current_stage = stage_text

        if not tds:
            continue

        # Normalize whitespace before cleanup (get_text(strip=True) removes
        # spaces between inline tags like "<a>Cellar</a>")
        section_text = " ".join(tds[0].get_text().split())
        section_text = re.sub(r"[†*]", "", section_text)
        section_text = re.sub(r"\s*\(optional\)\s*", "", section_text).strip()

        row = empty_row(section_text, location, current_stage)
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


def load_raw(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {s["index"]: s for s in d["sections"]}


def main():
    ap = argparse.ArgumentParser(description="Parse homestead build data to JSON")
    ap.add_argument("homestead_json", help="Path to homestead_raw.json")
    ap.add_argument("main_hall_json", help="Path to main_hall_raw.json")
    ap.add_argument("cellar_json",    help="Path to cellar_raw.json")
    ap.add_argument("output_json",    help="Path to output JSON file")
    args = ap.parse_args()

    for p in (args.homestead_json, args.main_hall_json, args.cellar_json):
        if not Path(p).exists():
            print(f"ERROR: file not found: {p}", file=sys.stderr)
            sys.exit(1)

    sources = {
        "homestead": load_raw(args.homestead_json),
        "main_hall": load_raw(args.main_hall_json),
        "cellar":    load_raw(args.cellar_json),
    }

    all_records = []
    for source_key, section_idx, location, parse_type in SECTION_CONFIG:
        sec_map = sources[source_key]
        if section_idx not in sec_map:
            print(f"WARNING: section {section_idx} not found in {source_key}", file=sys.stderr)
            continue

        sec = sec_map[section_idx]
        soup = BeautifulSoup(sec["html"], "html.parser")

        if parse_type == "construction":
            records = parse_construction_table(soup, location)
        elif parse_type in ("item_table", "shrine_table"):
            records = parse_item_table(soup, location)
        elif parse_type == "shrine_bullet":
            records = parse_shrine_bullet(soup, location, sec["title"])
        else:
            print(f"WARNING: unknown parse_type {parse_type}", file=sys.stderr)
            continue

        all_records.extend(records)
        print(f"  {source_key}/{section_idx} ({location}): {len(records)} records",
              file=sys.stderr)

    # Forge-craftable building components: add recipe rows so queries can compute
    # base material costs (e.g. "how many iron ingots to build the whole house?").
    # batch_size = number of units produced per recipe; None for normal build rows.
    crafted = [
        {**empty_row("Nails",         "Crafted_Component"), "batch_size": 10, "iron_ingot": 1},
        {**empty_row("Hinge",         "Crafted_Component"), "batch_size":  2, "iron_ingot": 1},
        {**empty_row("Iron Fittings", "Crafted_Component"), "batch_size":  1, "iron_ingot": 1},
        {**empty_row("Lock",          "Crafted_Component"), "batch_size":  1,
         "iron_ingot": 1, "corundum_ingot": 1},
    ]
    all_records.extend(crafted)
    print(f"  crafted components: {len(crafted)} records", file=sys.stderr)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"Total: {len(all_records)} records → {args.output_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
