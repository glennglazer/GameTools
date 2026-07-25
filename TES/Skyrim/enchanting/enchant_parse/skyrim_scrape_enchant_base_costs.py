#!/usr/bin/python3
"""
Scrape Skyrim apparel and weapon enchantment base costs from UESP Skyrim:Enchanting_Effects.

Section 2 (Apparel Effects) and section 3 (Weapon Effects) each contain a
wikitable where every data row has an effect name link in a <th> cell and a
Base Cost value in the <td> immediately before the collapsible Disenchant <td>.

Produces two raw JSON files ({name: base_cost} dicts):
  apparel_base_costs_raw.json
  weapons_base_costs_raw.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UESP_API = 'https://en.uesp.net/w/api.php'
PAGE = 'Skyrim:Enchanting_Effects'
APPAREL_SECTION = 2
WEAPONS_SECTION = 3
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_APPAREL_OUT = str(_SCRIPT_DIR / 'apparel_base_costs_raw.json')
_DEFAULT_WEAPONS_OUT = str(_SCRIPT_DIR / 'weapons_base_costs_raw.json')

# UESP canonical name → DB canonical name (only where they differ)
APPAREL_NAME_MAP = {
    'Regenerate Health': 'Fortify Healing Rate',
    'Regenerate Magicka': 'Fortify Magicka Regen',
    'Regenerate Stamina': 'Fortify Stamina Regen',
    'Fortify One-handed': 'Fortify One-Handed',
    'Fortify Two-handed': 'Fortify Two-Handed',
    'Fortify Unarmed Damage': 'Fortify Unarmed',
    'Waterbreathing': 'Water Breathing',
}

WEAPONS_NAME_MAP = {
    'Damage Magicka': 'Magicka Damage',
    'Damage Stamina': 'Stamina Damage',
}

# UESP entries that are not in the DB — skip them
APPAREL_SKIP = {'Dark Moon', 'Empower Necromancy'}
WEAPONS_SKIP = {'Briarheart Geis', 'Smithing Expertise'}


def fetch_section(section: int, session=None) -> BeautifulSoup:
    s = session or requests.Session()
    params = {
        'action': 'parse',
        'page': PAGE,
        'prop': 'text',
        'section': section,
        'format': 'json',
    }
    resp = s.get(UESP_API, params=params,
                 headers={'User-Agent': USER_AGENT}, timeout=30)
    resp.raise_for_status()
    html = resp.json()['parse']['text']['*']
    return BeautifulSoup(html, 'html.parser')


def _effect_name_from_row(row) -> str | None:
    """Extract canonical effect name from the th link in a data row."""
    for th in row.find_all('th'):
        a = th.find('a', href=lambda h: h and '/wiki/Skyrim:' in h and 'File:' not in h)
        if a:
            href = a['href']
            name = href.split('/wiki/Skyrim:')[1]
            name = name.replace('%27', "'").replace('%22', '"').replace('%26', '&')
            name = name.replace('_', ' ')
            name = re.sub(r'\s*\(effect\)\s*$', '', name, flags=re.IGNORECASE)
            return name
    return None


def _base_cost_from_row(row) -> int | None:
    """Extract base cost from the td immediately before the collapsible Disenchant td."""
    tds = row.find_all('td')
    for i, td in enumerate(tds):
        if td.find('div', class_='mw-collapsible'):
            if i > 0:
                text = tds[i - 1].get_text(strip=True)
                try:
                    return int(text)
                except ValueError:
                    pass
            break
    return None


def parse_section(soup, name_map: dict, skip: set) -> dict:
    """Return {db_name: base_cost} dict parsed from a wikitable."""
    result = {}
    table = soup.find('table', class_='wikitable')
    if not table:
        return result
    for row in table.find_all('tr'):
        base_cost = _base_cost_from_row(row)
        if base_cost is None:
            continue
        uesp_name = _effect_name_from_row(row)
        if not uesp_name or uesp_name in skip:
            continue
        db_name = name_map.get(uesp_name, uesp_name)
        result[db_name] = base_cost
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim enchantment base costs from UESP.')
    parser.add_argument('--apparel-out', default=_DEFAULT_APPAREL_OUT,
                        help='Output path for apparel_base_costs_raw.json')
    parser.add_argument('--weapons-out', default=_DEFAULT_WEAPONS_OUT,
                        help='Output path for weapons_base_costs_raw.json')
    args = parser.parse_args()

    for path in [args.apparel_out, args.weapons_out]:
        parent = Path(path).parent
        if not parent.exists():
            print(f'ERROR: output directory does not exist: {parent}', file=sys.stderr)
            sys.exit(1)

    session = requests.Session()

    print('Fetching Skyrim:Enchanting_Effects section 2 (Apparel)...', file=sys.stderr)
    apparel_soup = fetch_section(APPAREL_SECTION, session=session)
    apparel_costs = parse_section(apparel_soup, APPAREL_NAME_MAP, APPAREL_SKIP)
    with open(args.apparel_out, 'w', encoding='utf-8') as f:
        json.dump(apparel_costs, f, indent=2, sort_keys=True)
    print(f'  {len(apparel_costs)} apparel base costs → {args.apparel_out}', file=sys.stderr)

    print('Fetching Skyrim:Enchanting_Effects section 3 (Weapons)...', file=sys.stderr)
    weapons_soup = fetch_section(WEAPONS_SECTION, session=session)
    weapons_costs = parse_section(weapons_soup, WEAPONS_NAME_MAP, WEAPONS_SKIP)
    with open(args.weapons_out, 'w', encoding='utf-8') as f:
        json.dump(weapons_costs, f, indent=2, sort_keys=True)
    print(f'  {len(weapons_costs)} weapon base costs → {args.weapons_out}', file=sys.stderr)


if __name__ == '__main__':
    main()
