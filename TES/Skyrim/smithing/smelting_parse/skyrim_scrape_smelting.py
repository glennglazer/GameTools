#!/usr/bin/env python3
"""
Scrape Skyrim smelting recipes and material/ingot stats from the Elder Scrolls Wiki.

Sources:
  Smelting          – https://elderscrolls.fandom.com/wiki/Smelting (sections 1+2)
  Individual pages  – one page per material and ingot for weight/value
  CC item pages     – Amber_(Skyrim_Creation_Club), Madness_Ore, Refined_Amber, Madness_Ingot

Output: smelting_raw.json with:
  {
    "recipes":        [{source, source_to_ingot, ingot, ingots_produced}, ...],
    "material_stats": {"Iron Ore": {"weight": 1, "value": 2}, ...},
    "ingot_stats":    {"Iron Ingot": {"weight": 1, "value": 7}, ...}
  }
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API_URL    = 'https://elderscrolls.fandom.com/api.php'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_OUT = str(_SCRIPT_DIR / 'smelting_raw.json')

# display name → wiki page title for source materials
SOURCE_PAGES = {
    'Iron Ore':                    'Iron_Ore_(Skyrim)',
    'Corundum Ore':                'Corundum_Ore',
    'Silver Ore':                  'Silver_Ore',
    'Gold Ore':                    'Gold_Ore',
    'Ebony Ore':                   'Ebony_Ore_(Skyrim)',
    'Malachite Ore':               'Malachite_Ore',
    'Moonstone Ore':               'Moonstone_Ore_(Skyrim)',
    'Orichalcum Ore':              'Orichalcum_Ore_(Skyrim)',
    'Quicksilver Ore':             'Quicksilver_Ore_(Skyrim)',
    'Bent Dwemer Scrap Metal':     'Bent_Dwemer_Scrap_Metal',
    'Large Decorative Dwemer Strut': 'Large_Decorative_Dwemer_Strut',
    'Large Dwemer Plate Metal':    'Large_Dwemer_Plate_Metal',
    'Large Dwemer Strut':          'Large_Dwemer_Strut',
    'Small Dwemer Plate Metal':    'Small_Dwemer_Plate_Metal',
    'Solid Dwemer Metal':          'Solid_Dwemer_Metal',
    # CC sources
    'Amber':                       'Amber_(Skyrim_Creation_Club)',
    'Madness Ore':                 'Madness_Ore',
}

# display name → wiki page title for ingots
INGOT_PAGES = {
    'Corundum Ingot':     'Corundum_Ingot',
    'Dwarven Metal Ingot': 'Dwarven_Metal_Ingot',
    'Ebony Ingot':        'Ebony_Ingot_(Skyrim)',
    'Gold Ingot':         'Gold_Ingot',
    'Iron Ingot':         'Iron_Ingot_(Skyrim)',
    'Refined Malachite':  'Refined_Malachite',
    'Refined Moonstone':  'Refined_Moonstone',
    'Orichalcum Ingot':   'Orichalcum_Ingot_(Skyrim)',
    'Quicksilver Ingot':  'Quicksilver_Ingot_(Skyrim)',
    'Silver Ingot':       'Silver_Ingot',
    'Steel Ingot':        'Steel_Ingot_(Skyrim)',
    # CC ingots
    'Refined Amber':      'Refined_Amber',
    'Madness Ingot':      'Madness_Ingot',
}


def fetch_section(page: str, section: int, session: requests.Session) -> BeautifulSoup:
    resp = session.get(
        API_URL,
        params={'action': 'parse', 'page': page, 'prop': 'text',
                'section': section, 'format': 'json'},
        headers={'User-Agent': USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'parse' not in data:
        raise ValueError(f'No parse result for {page} section {section}')
    return BeautifulSoup(data['parse']['text']['*'], 'html.parser')


def fetch_page(page: str, session: requests.Session) -> BeautifulSoup:
    resp = session.get(
        API_URL,
        params={'action': 'parse', 'page': page, 'prop': 'text', 'format': 'json'},
        headers={'User-Agent': USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'parse' not in data:
        raise ValueError(f'No parse result for {page}')
    return BeautifulSoup(data['parse']['text']['*'], 'html.parser')


def cell_text(td) -> str:
    return td.get_text(separator=' ', strip=True)


def parse_recipe_table(soup: BeautifulSoup) -> list:
    """Parse the main Smelting Ingots table (section 1)."""
    rows = []
    for table in soup.find_all('table'):
        for tr in table.find_all('tr'):
            cells = tr.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            src_cell = cell_text(cells[0])
            ing_cell = cell_text(cells[1])
            # skip header rows
            if src_cell.lower() in ('source (ore)', 'material', 'source'):
                continue
            # parse ingots produced from trailing parenthetical, e.g. "Dwarven Metal Ingot (3)"
            ingots_produced = 1
            m = re.search(r'\((\d+)\)$', ing_cell)
            if m:
                ingots_produced = int(m.group(1))
                ingot_name = ing_cell[:m.start()].strip()
            else:
                ingot_name = ing_cell.strip()

            # parse source qty from trailing parenthetical, e.g. "Corundum Ore (2)"
            source_to_ingot = 1
            m2 = re.search(r'\((\d+)\)$', src_cell)
            if m2:
                source_to_ingot = int(m2.group(1))
                source_name = src_cell[:m2.start()].strip()
            else:
                source_name = src_cell.strip()

            # skip the combined "Iron Ore, Corundum Ore" steel row — parser handles it
            if ',' in source_name:
                continue

            if source_name and ingot_name:
                rows.append({
                    'source': source_name,
                    'source_to_ingot': source_to_ingot,
                    'ingot': ingot_name,
                    'ingots_produced': ingots_produced,
                })
    return rows


def extract_weight_value(soup: BeautifulSoup) -> dict:
    """Extract weight and base value from an item's infobox table."""
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for i, tr in enumerate(rows):
            headers = [cell_text(c).lower() for c in tr.find_all(['td', 'th'])]
            if 'weight' in headers and i + 1 < len(rows):
                values = [cell_text(c) for c in rows[i + 1].find_all(['td', 'th'])]
                w_idx = next((j for j, h in enumerate(headers) if h == 'weight'), None)
                v_idx = next((j for j, h in enumerate(headers)
                              if h in ('base value', 'value', 'gold')), None)
                if w_idx is not None and v_idx is not None:
                    try:
                        w = int(float(values[w_idx]))
                        v = int(float(values[v_idx]))
                        return {'weight': w, 'value': v}
                    except (ValueError, IndexError):
                        pass
    return {}


def fetch_stats(name_to_page: dict, session: requests.Session, label: str) -> dict:
    stats = {}
    for display_name, page_title in name_to_page.items():
        soup = fetch_page(page_title, session)
        wv = extract_weight_value(soup)
        if not wv:
            print(f'Warning: no weight/value found for {display_name} ({page_title})',
                  file=sys.stderr)
        stats[display_name] = wv
        print(f'  {label}: {display_name} → {wv}', file=sys.stderr)
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Skyrim smelting data from the wiki.')
    parser.add_argument('outfile', nargs='?', default=_DEFAULT_OUT,
                        help='Path to write smelting_raw.json')
    parser.add_argument('--out-dir', default=None,
                        help='Directory for output (overrides outfile; used by update_tes.py)')
    args = parser.parse_args()

    if args.out_dir:
        out_path = Path(args.out_dir) / 'smelting_raw.json'
    else:
        out_path = Path(args.outfile)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    print('Fetching Smelting page (section 1)…', file=sys.stderr)
    soup1 = fetch_section('Smelting', 1, session)
    recipes = parse_recipe_table(soup1)
    print(f'  Found {len(recipes)} base recipes', file=sys.stderr)

    print('Fetching material stats…', file=sys.stderr)
    material_stats = fetch_stats(SOURCE_PAGES, session, 'source')

    print('Fetching ingot stats…', file=sys.stderr)
    ingot_stats = fetch_stats(INGOT_PAGES, session, 'ingot')

    raw = {
        'recipes':        recipes,
        'material_stats': material_stats,
        'ingot_stats':    ingot_stats,
    }

    out_path.write_text(json.dumps(raw, indent=2))
    print(f'Wrote {out_path}', file=sys.stderr)
