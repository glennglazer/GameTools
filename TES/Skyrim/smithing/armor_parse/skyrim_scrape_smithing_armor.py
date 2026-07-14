#!/usr/bin/env python3
"""
Scrape Skyrim smithing armor data from all material-specific armor pages.

Produces a single combined raw file skyrim_smithing_armor_raw.txt with
fixed column order (26 pipe-delimited fields per row).

Column order:
  piece|material_perk|armor_rating|weight|value|id|
  bone_meal|chitin_plate|corundum_ingot|daedra_heart|dragon_bone|
  dragon_scales|dwarven_metal_ingot|ebony_ingot|iron_ingot|leather|
  leather_strips|netch_jelly|netch_leather|orichalcum_ingot|
  quicksilver_ingot|refined_malachite|refined_moonstone|stalhrim|
  steel_ingot|void_salts
"""

import argparse
import os.path as op
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API_URL = 'https://elderscrolls.fandom.com/api.php'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'

_SCRIPT_DIR = Path(__file__).parent.resolve()

# Fixed material column order (alphabetical)
ARMOR_MATERIAL_COLS = [
    'bone_meal', 'chitin_plate', 'corundum_ingot', 'daedra_heart',
    'dragon_bone', 'dragon_scales', 'dwarven_metal_ingot', 'ebony_ingot',
    'iron_ingot', 'leather', 'leather_strips', 'netch_jelly', 'netch_leather',
    'orichalcum_ingot', 'quicksilver_ingot', 'refined_malachite',
    'refined_moonstone', 'stalhrim', 'steel_ingot', 'void_salts',
]

ARMOR_FIXED_COLS = ['piece', 'material_perk', 'armor_rating', 'weight', 'value', 'id']
ARMOR_ALL_COLS = ARMOR_FIXED_COLS + ARMOR_MATERIAL_COLS

# Maps wiki column header text → DB column name
ARMOR_COL_MAP = {
    'Bone Meal': 'bone_meal',
    'Chitin Plate': 'chitin_plate',
    'Corundum Ingot': 'corundum_ingot',
    'Daedra Heart': 'daedra_heart',
    'Dragon Bone': 'dragon_bone',
    'Dragon Bones': 'dragon_bone',
    'Dragon Scales': 'dragon_scales',
    'Dwarven Metal Ingot': 'dwarven_metal_ingot',
    'Ebony Ingot': 'ebony_ingot',
    'Ebony Ingots': 'ebony_ingot',
    'Iron Ingot': 'iron_ingot',
    'Leather': 'leather',
    'Leather Strips': 'leather_strips',
    'Netch Jelly': 'netch_jelly',
    'Netch Leather': 'netch_leather',
    'Orichalcum Ingot': 'orichalcum_ingot',
    'Quicksilver Ingot': 'quicksilver_ingot',
    'Refined Malachite': 'refined_malachite',
    'Refined Moonstone': 'refined_moonstone',
    'Stalhrim': 'stalhrim',
    'Steel Ingot': 'steel_ingot',
    'Void Salts': 'void_salts',
}

# Maps img alt text → DB column name for icon-based headers
ARMOR_ICON_MAP = {
    'ArmorIcon': 'armor_rating',
    'Iron Shield SK': 'armor_rating',
    'WeightIcon': 'weight',
    'Skyrim-knapsack': 'weight',
    'Gold': 'value',
}

# (page_title, section_index, material_perk)
ARMOR_PAGES = [
    ('Steel_Armor_(Skyrim)',       3, 'Steel Smithing'),
    ('Elven_Armor_(Skyrim)',       7, 'Elven Smithing'),
    ('Scaled_Armor_(Skyrim)',      6, 'Advanced Armors'),
    ('Steel_Plate_Armor',          7, 'Advanced Armors'),
    ('Glass_Armor_(Skyrim)',       4, 'Glass Smithing'),
    ('Dwarven_Armor_(Skyrim)',     4, 'Dwarven Smithing'),
    ('Orcish_Armor_(Skyrim)',      4, 'Orcish Smithing'),
    ('Ebony_Armor_(Skyrim)',       5, 'Ebony Smithing'),
    ('Daedric_Armor_(Skyrim)',     5, 'Daedric Smithing'),
    ('Dragonplate_Armor_(Skyrim)', 6, 'Dragon Armor'),
    ('Dragonscale_Armor_(Skyrim)', 4, 'Dragon Armor'),
    ('Bonemold_Armor_(Dragonborn)', 5, 'Steel Smithing'),
    ('Chitin_Armor_(Dragonborn)',   3, 'Elven Smithing'),
    ('Nordic_Carved_Armor',        3, 'Advanced Armors'),
    ('Stalhrim_Armor_(Skyrim)',    4, 'Ebony Smithing'),
]


def fetch_section(page_title, section, session):
    """Fetch a wiki page section via the MediaWiki API; return BeautifulSoup."""
    params = {
        'action': 'parse',
        'page': page_title,
        'prop': 'text',
        'section': section,
        'format': 'json',
    }
    resp = session.get(API_URL, params=params,
                       headers={'User-Agent': USER_AGENT}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    html = data['parse']['text']['*']
    return BeautifulSoup(html, 'html.parser')


def _header_col_name(th):
    """Return the DB column name for a header <th> cell, or None if unknown."""
    img = th.find('img')
    if img:
        return ARMOR_ICON_MAP.get(img.get('alt', ''))
    text = th.get_text(separator=' ', strip=True)
    return ARMOR_COL_MAP.get(text)


def _parse_int(text):
    """Parse an integer cell value; return 0 for dashes and empty strings."""
    text = text.strip().replace(',', '')
    if text in ('–', '-', '—', ''):
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _parse_float(text):
    """Parse a float cell value; return 0.0 for dashes."""
    text = text.strip().replace(',', '')
    if text in ('–', '-', '—', ''):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _strip_dlc(name):
    """Remove trailing DLC marker words (DG, DR, DB, HF, CC)."""
    dlc = frozenset(['DG', 'DR', 'DB', 'HF', 'CC'])
    words = name.split()
    while words and words[-1] in dlc:
        words.pop()
    return ' '.join(words)


def parse_armor_tables(soup, material_perk):
    """Parse all armor attribute tables from soup; return list of row dicts."""
    rows = []
    for table in soup.find_all('table'):
        header_row = table.find('tr')
        if not header_row:
            continue
        header_cells = header_row.find_all(['th', 'td'])
        if not header_cells:
            continue

        # Build column index → DB column name mapping
        col_map = {}
        # First column is always piece name (regardless of header text or blank)
        col_map[0] = 'piece'
        for i, th in enumerate(header_cells[1:], start=1):
            db_col = _header_col_name(th)
            if db_col:
                col_map[i] = db_col
            else:
                text = th.get_text(separator=' ', strip=True)
                if text.lower() in ('id', 'item id', 'itemid'):
                    col_map[i] = 'id'

        # Skip tables with no material columns
        if not any(v in ARMOR_MATERIAL_COLS for v in col_map.values()):
            continue

        for tr in table.find_all('tr')[1:]:
            cells = tr.find_all(['th', 'td'])
            if not cells:
                continue
            # First cell is always the piece name (in a <th>)
            piece = _strip_dlc(cells[0].get_text(separator=' ', strip=True))
            if not piece or piece.lower().startswith('total'):
                continue

            rec = {col: 0 for col in ARMOR_MATERIAL_COLS}
            rec['piece'] = piece
            rec['material_perk'] = material_perk
            rec['armor_rating'] = 0
            rec['weight'] = 0.0
            rec['value'] = 0
            rec['id'] = ''

            for i, cell in enumerate(cells[1:], start=1):
                db_col = col_map.get(i)
                if db_col is None:
                    continue
                raw = cell.get_text(separator=' ', strip=True)
                if db_col == 'weight':
                    rec[db_col] = _parse_float(raw)
                elif db_col == 'id':
                    rec[db_col] = raw.strip()
                elif db_col in ARMOR_MATERIAL_COLS or db_col in ('armor_rating', 'value'):
                    rec[db_col] = _parse_int(raw)

            # Exclude non-craftable items (all material quantities 0)
            if all(rec[m] == 0 for m in ARMOR_MATERIAL_COLS):
                continue

            rows.append(rec)

    return rows


def write_raw_file(records, outfile):
    """Write pipe-delimited records to outfile with fixed column order."""
    with open(outfile, 'w', encoding='utf-8') as fh:
        for rec in records:
            line = '|'.join(str(rec[col]) for col in ARMOR_ALL_COLS)
            fh.write(line + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim smithing armor data from the wiki.')
    parser.add_argument('--out-dir', default=str(_SCRIPT_DIR),
                        help='Directory for raw output files')
    args = parser.parse_args()

    out_dir = args.out_dir
    if not op.isdir(out_dir):
        print(f'ERROR: output directory does not exist: {out_dir}', file=sys.stderr)
        sys.exit(1)

    outfile = op.join(out_dir, 'skyrim_smithing_armor_raw.txt')
    session = requests.Session()
    all_rows = []

    for page_title, section, material_perk in ARMOR_PAGES:
        print(f'Fetching {page_title} section {section}...', file=sys.stderr)
        try:
            soup = fetch_section(page_title, section, session)
        except Exception as e:
            print(f'  ERROR fetching {page_title}: {e}', file=sys.stderr)
            sys.exit(1)
        rows = parse_armor_tables(soup, material_perk)
        print(f'  {len(rows)} craftable items', file=sys.stderr)
        all_rows.extend(rows)
        time.sleep(0.3)

    if not all_rows:
        print('ERROR: No armor rows parsed.', file=sys.stderr)
        sys.exit(1)

    write_raw_file(all_rows, outfile)
    print(f'\n{len(all_rows)} total armor items → {outfile}', file=sys.stderr)


if __name__ == '__main__':
    main()
