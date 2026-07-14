#!/usr/bin/env python3
"""
Scrape Skyrim smithing perks, improvement table, and crafting materials
from the Elder Scrolls Wiki via the MediaWiki JSON API.

Source page: Smithing_(Skyrim)
  Section 10 → skyrim_smithing_perks_raw.txt
  Section 11 → skyrim_smithing_improvement_raw.txt
               skyrim_smithing_materials_raw.txt

Perks format:    name|skill_level|prerequisite|description
Improvement format: quality|skill_without_perk|skill_with_perk|armor_effect|weapon_effect
Materials format:   smithing_category|crafting_material
"""

import argparse
import os.path as op
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API_URL = 'https://elderscrolls.fandom.com/api.php'
SMITHING_PAGE = 'Smithing_(Skyrim)'
PERKS_SECTION = 10
IMPROVEMENT_SECTION = 11

USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'

_SCRIPT_DIR = Path(__file__).parent.resolve()

DLC_MARKERS = frozenset(['DG', 'DR', 'DB', 'HF', 'CC'])


def fetch_section(page_title, section, session=None):
    """Fetch a wiki page section via the MediaWiki API; return BeautifulSoup."""
    s = session or requests.Session()
    params = {
        'action': 'parse',
        'page': page_title,
        'prop': 'text',
        'section': section,
        'format': 'json',
    }
    resp = s.get(API_URL, params=params,
                 headers={'User-Agent': USER_AGENT}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    html = data['parse']['text']['*']
    return BeautifulSoup(html, 'html.parser')


def _td_segments(td):
    """Split td content on <br> tags; return list of stripped text strings."""
    segments = []
    current = []
    for child in td.children:
        if getattr(child, 'name', None) == 'br':
            text = ''.join(
                c.get_text() if hasattr(c, 'get_text') else str(c)
                for c in current
            ).strip()
            if text:
                segments.append(text)
            current = []
        else:
            current.append(child)
    text = ''.join(
        c.get_text() if hasattr(c, 'get_text') else str(c)
        for c in current
    ).strip()
    if text:
        segments.append(text)
    return segments


def strip_dlc_suffix(text):
    """Remove trailing DLC marker words from a text string."""
    words = text.split()
    while words and words[-1] in DLC_MARKERS:
        words.pop()
    return ' '.join(words)


def parse_perk_name(td):
    """Extract perk name, stripping ** suffix and DLC markers."""
    text = td.get_text(separator='', strip=True)
    text = text.rstrip('*').strip()
    return strip_dlc_suffix(text)


def parse_req_cell(td):
    """Parse a perk requirements cell.

    Format: 'Smithing N,<br/>Prereq Name' or 'No requirement'.
    Returns (skill_level: int, prerequisite: str).
    """
    segments = _td_segments(td)
    if not segments:
        return 0, 'None'

    full = ' '.join(s.rstrip(',').strip() for s in segments)
    if 'no requirement' in full.lower():
        return 0, 'None'

    m = re.search(r'(\d+)', segments[0])
    skill = int(m.group(1)) if m else 0

    prereq = ', '.join(s.strip() for s in segments[1:]) if len(segments) > 1 else 'None'
    return skill, prereq


def parse_perks_table(soup):
    """Return list of perk dicts from the smithing perks table (skqtable class)."""
    perks = []
    for table in soup.find_all('table', class_='skqtable'):
        first_th = table.find('th')
        if not first_th or 'Perk' not in first_th.get_text(strip=True):
            continue
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 3:
                continue
            name = parse_perk_name(tds[0])
            if not name:
                continue
            skill, prereq = parse_req_cell(tds[1])
            desc = tds[2].get_text(separator=' ', strip=True)
            # Strip pipes to avoid breaking the raw file format
            desc = desc.replace('|', ' ')
            perks.append({
                'name': name,
                'skill_level': skill,
                'prerequisite': prereq,
                'description': desc,
            })
    return perks


def parse_improvement_table(soup):
    """Return list of improvement level dicts.

    Table has a two-row header (colspan/rowspan); data rows start at row 2.
    Columns after flattening: quality, skill_without_perk, skill_with_perk,
    armor_effect, weapon_effect.
    """
    rows = []
    for table in soup.find_all('table'):
        headers = []
        for th in table.find_all('th'):
            headers.append(th.get_text(strip=True).lower())
        if 'quality' not in headers:
            continue
        data_rows = table.find_all('tr')
        for tr in data_rows[2:]:  # skip two header rows
            tds = tr.find_all('td')
            if len(tds) < 5:
                continue
            quality = tds[0].get_text(strip=True)
            if not quality or quality.lower() == 'quality':
                continue
            rows.append({
                'quality': quality,
                'skill_without_perk': tds[1].get_text(strip=True),
                'skill_with_perk': tds[2].get_text(strip=True),
                'armor_effect': tds[3].get_text(strip=True),
                'weapon_effect': tds[4].get_text(strip=True),
            })
    return rows


def parse_materials_table(soup):
    """Return list of (smithing_category, crafting_material) pairs.

    Handles rowspan in the crafting_material column.
    """
    rows = []
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if 'smithing category' not in ' '.join(headers).lower():
            continue

        pending_material = None
        pending_rowspan = 0

        for tr in table.find_all('tr')[1:]:  # skip header
            tds = tr.find_all('td')
            if not tds:
                continue

            if pending_rowspan > 0:
                category = strip_dlc_suffix(tds[0].get_text(strip=True))
                material = pending_material
                pending_rowspan -= 1
            elif len(tds) >= 2:
                category = strip_dlc_suffix(tds[0].get_text(strip=True))
                mat_cell = tds[1]
                rs = int(mat_cell.get('rowspan', 1))
                material = mat_cell.get_text(strip=True)
                if rs > 1:
                    pending_material = material
                    pending_rowspan = rs - 1
            else:
                continue

            if category and material:
                rows.append({
                    'smithing_category': category,
                    'crafting_material': material,
                })
    return rows


def write_raw_file(records, outfile, fields):
    """Write pipe-delimited records to outfile."""
    with open(outfile, 'w', encoding='utf-8') as fh:
        for rec in records:
            line = '|'.join(str(rec[f]) for f in fields)
            fh.write(line + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim smithing data (perks, improvement, materials).')
    parser.add_argument('--out-dir', default=str(_SCRIPT_DIR),
                        help='Directory for raw output files')
    args = parser.parse_args()

    out_dir = args.out_dir
    if not op.isdir(out_dir):
        print(f'ERROR: output directory does not exist: {out_dir}', file=sys.stderr)
        sys.exit(1)

    perks_out = op.join(out_dir, 'skyrim_smithing_perks_raw.txt')
    improvement_out = op.join(out_dir, 'skyrim_smithing_improvement_raw.txt')
    materials_out = op.join(out_dir, 'skyrim_smithing_materials_raw.txt')

    session = requests.Session()

    print('Fetching Smithing_(Skyrim) section 10 (perks)...', file=sys.stderr)
    perks_soup = fetch_section(SMITHING_PAGE, PERKS_SECTION, session=session)
    perks = parse_perks_table(perks_soup)
    if not perks:
        print('ERROR: No perks found — check wiki API response.', file=sys.stderr)
        sys.exit(1)
    write_raw_file(perks, perks_out,
                   ['name', 'skill_level', 'prerequisite', 'description'])
    print(f'  {len(perks)} perks → {perks_out}', file=sys.stderr)

    print('Fetching Smithing_(Skyrim) section 11 (improvement/materials)...', file=sys.stderr)
    imp_soup = fetch_section(SMITHING_PAGE, IMPROVEMENT_SECTION, session=session)

    improvement = parse_improvement_table(imp_soup)
    if not improvement:
        print('ERROR: No improvement rows found.', file=sys.stderr)
        sys.exit(1)
    write_raw_file(improvement, improvement_out,
                   ['quality', 'skill_without_perk', 'skill_with_perk',
                    'armor_effect', 'weapon_effect'])
    print(f'  {len(improvement)} improvement levels → {improvement_out}', file=sys.stderr)

    materials = parse_materials_table(imp_soup)
    if not materials:
        print('ERROR: No crafting material rows found.', file=sys.stderr)
        sys.exit(1)
    write_raw_file(materials, materials_out,
                   ['smithing_category', 'crafting_material'])
    print(f'  {len(materials)} material rows → {materials_out}', file=sys.stderr)


if __name__ == '__main__':
    main()
