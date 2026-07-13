#!/usr/bin/env python3
"""
Scrape soul gem data from the Elder Scrolls Wiki via the MediaWiki JSON API.

Produces two raw pipe-delimited files:
  skyrim_soul_gem_types_raw.txt   — name|weight|value|capacity|trappable_souls
  skyrim_creature_souls_raw.txt   — creature|soul_size
"""

import argparse
import os.path as op
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API_URL = 'https://elderscrolls.fandom.com/api.php'
SOUL_GEM_PAGE = 'Soul_Gem_(Skyrim)'
RACES_PAGE = 'Races_(Skyrim)'
RACES_SECTION = 1

SOUL_SIZE_MAP = {
    'petty_souls': 'petty',
    'lesser_souls': 'lesser',
    'common_souls': 'common',
    'greater_souls': 'greater',
    'grand_souls': 'grand',
}

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_TYPES_OUT = str(_SCRIPT_DIR / 'skyrim_soul_gem_types_raw.txt')
_DEFAULT_SOULS_OUT = str(_SCRIPT_DIR / 'skyrim_creature_souls_raw.txt')

USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'


def fetch_page(page_title, session=None, section=None):
    """Fetch a wiki page (or section) via the MediaWiki API; return BeautifulSoup."""
    s = session or requests.Session()
    params = {
        'action': 'parse',
        'page': page_title,
        'prop': 'text',
        'format': 'json',
    }
    if section is not None:
        params['section'] = section

    resp = s.get(API_URL, params=params,
                 headers={'User-Agent': USER_AGENT}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    html = data['parse']['text']['*']
    return BeautifulSoup(html, 'html.parser')


def parse_types_table(soup):
    """Return list of dicts from the soul gem Types table."""
    for table in soup.find_all('table', class_='wikitable'):
        first_th = table.find('th')
        if not first_th or first_th.get_text(strip=True) != 'Name':
            continue
        rows = []
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 5:
                continue
            try:
                rows.append({
                    'name': tds[0].get_text(strip=True),
                    'weight': float(tds[1].get_text(strip=True)),
                    'value': int(tds[2].get_text(strip=True)),
                    'capacity': int(tds[3].get_text(strip=True)),
                    'trappable_souls': tds[4].get_text(strip=True),
                })
            except (ValueError, IndexError):
                continue
        if rows:
            return rows
    raise ValueError('No soul gem types wikitable found')


def extract_creature_name(td):
    """Extract creature name from a souls table cell, ignoring DLC sup markers."""
    for a in td.find_all('a'):
        if not a.find_parent('sup'):
            return a.get_text(strip=True)
    return td.get_text(strip=True).strip()


def parse_souls_tables(soup):
    """Return list of {creature, soul_size} dicts from the creature souls table."""
    souls_table = None
    for table in soup.find_all('table', class_='wikitable'):
        for th in table.find_all('th'):
            headline = th.find('span', class_='mw-headline')
            if not headline:
                continue
            span_id = headline.get('id', '').lower()
            if any(span_id == key for key in SOUL_SIZE_MAP):
                souls_table = table
                break
        if souls_table:
            break

    if not souls_table:
        raise ValueError('No creature souls wikitable found')

    rows = []
    current_size = None

    for tr in souls_table.find_all('tr'):
        th = tr.find('th')
        td = tr.find('td')

        if th and not td:
            headline = th.find('span', class_='mw-headline')
            if headline:
                span_id = headline.get('id', '').lower()
                current_size = SOUL_SIZE_MAP.get(span_id)
        elif td and current_size:
            name = extract_creature_name(td)
            if name:
                rows.append({'creature': name, 'soul_size': current_size})

    return rows


def parse_black_souls_list(soup):
    """Parse the Black Soul Gems section list.

    Returns (other_creatures: list[str], has_playable_races: bool).
    """
    for tag in soup.find_all(['h2', 'h3', 'h4']):
        headline = tag.find('span', class_='mw-headline')
        if not headline:
            continue
        span_id = headline.get('id', '')
        if 'Black' not in span_id:
            continue
        ul = tag.find_next('ul')
        if not ul:
            return [], False

        other_creatures = []
        has_playable_races = False

        for li in ul.find_all('li', recursive=False):
            text = li.get_text(strip=True)
            if re.search(r'playable race', text, re.IGNORECASE):
                has_playable_races = True
            else:
                a = li.find('a')
                name = a.get_text(strip=True) if a else text
                if name:
                    other_creatures.append(name)

        return other_creatures, has_playable_races

    return [], False


def extract_race_names(soup):
    """Extract playable race names from the Races_(Skyrim) section 1 table."""
    table = soup.find('table', class_='wikitable')
    if not table:
        raise ValueError('No wikitable found in Playable Races section')

    # Header row: find index of 'Race' column
    header_row = table.find('tr')
    ths = header_row.find_all('th') if header_row else []
    header_texts = [th.get_text(strip=True) for th in ths]

    try:
        race_col = header_texts.index('Race')
    except ValueError:
        race_col = 1  # fallback: second column is race name

    races = []
    for tr in table.find_all('tr')[1:]:
        tds = tr.find_all('td')
        if not tds or len(tds) <= race_col:
            continue
        name = tds[race_col].get_text(strip=True)
        if name:
            races.append(name)

    return races


def write_raw_file(records, outfile, header_fields):
    """Write pipe-delimited records to outfile."""
    with open(outfile, 'w', encoding='utf-8') as fh:
        for rec in records:
            line = '|'.join(str(rec[f]) for f in header_fields)
            fh.write(line + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim soul gem data from the wiki.')
    parser.add_argument('--out-dir', default=str(_SCRIPT_DIR),
                        help='Directory for raw output files')
    args = parser.parse_args()

    out_dir = args.out_dir
    if not op.isdir(out_dir):
        print(f'ERROR: output directory does not exist: {out_dir}', file=sys.stderr)
        sys.exit(1)

    types_out = op.join(out_dir, 'skyrim_soul_gem_types_raw.txt')
    souls_out = op.join(out_dir, 'skyrim_creature_souls_raw.txt')

    session = requests.Session()

    print('Fetching Soul_Gem_(Skyrim)...', file=sys.stderr)
    soup = fetch_page(SOUL_GEM_PAGE, session=session)

    print('Parsing soul gem types...', file=sys.stderr)
    gem_types = parse_types_table(soup)
    write_raw_file(gem_types, types_out,
                   ['name', 'weight', 'value', 'capacity', 'trappable_souls'])
    print(f'  {len(gem_types)} gem types → {types_out}', file=sys.stderr)

    print('Parsing creature souls...', file=sys.stderr)
    creature_souls = parse_souls_tables(soup)

    other_black, has_races = parse_black_souls_list(soup)
    if has_races:
        print('Fetching Races_(Skyrim) for playable races...', file=sys.stderr)
        races_soup = fetch_page(RACES_PAGE, session=session, section=RACES_SECTION)
        race_names = extract_race_names(races_soup)
        black_rows = [{'creature': r, 'soul_size': 'black'} for r in race_names]
        print(f'  {len(race_names)} playable races', file=sys.stderr)
    else:
        black_rows = []

    black_rows += [{'creature': c, 'soul_size': 'black'} for c in other_black]
    all_souls = creature_souls + black_rows

    write_raw_file(all_souls, souls_out, ['creature', 'soul_size'])
    print(f'  {len(all_souls)} creature souls → {souls_out}', file=sys.stderr)


if __name__ == '__main__':
    main()
