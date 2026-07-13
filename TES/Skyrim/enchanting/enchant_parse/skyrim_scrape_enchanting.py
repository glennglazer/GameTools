#!/usr/bin/env python3
"""
Scrape Skyrim enchanting data from the Elder Scrolls Wiki via the MediaWiki JSON API.

Produces three raw pipe-delimited files:
  skyrim_enchant_perks_raw.txt   — name|skill_level|prerequisite|description
  skyrim_enchant_effects_raw.txt — name|school
  skyrim_enchant_apparel_raw.txt — enchantment|head|chest|hands|feet|shield|amulet|ring
"""

import argparse
import os.path as op
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API_URL = 'https://elderscrolls.fandom.com/api.php'
ENCHANT_PAGE = 'Enchanting_(Skyrim)'
PERKS_SECTION = 10
ENCHANTS_SECTION = 13

USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'

_SCRIPT_DIR = Path(__file__).parent.resolve()

# Maps bare multi-rank perk names to their minimum rank form for prerequisite remapping
PREREQ_NAME_MAP = {
    'Enchanter': 'Enchanter (1/5)',
}

# Augmented element perk multi-rank expansion
AUGMENTED_ELEMENT_MAP = {
    'Augmented Flames': 'Fire',
    'Augmented Frost': 'Frost',
    'Augmented Shock': 'Shock',
}
AUGMENTED_MAGNITUDES = ['25%', '50%']

ENCHANTER_MAGNITUDES = ['20%', '40%', '60%', '80%', '100%']

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


def parse_req_cell(td):
    """Parse a perk requirements cell split on <br> tags.

    Returns (skill_levels: list[int], prereq_names: list[str]).
    """
    segments = _td_segments(td)
    if not segments:
        return [], []

    # First segment: skill level(s) — may include a skill name before the digits
    m = re.search(r'([\d]+(?:\s*/\s*[\d]+)*)', segments[0])
    if m:
        skill_levels = [int(n.strip()) for n in m.group(1).split('/')]
    else:
        skill_levels = []

    # Remaining segments: prerequisite names (may contain " or ")
    prereqs = []
    for seg in segments[1:]:
        for name in re.split(r'\s+or\s+', seg, flags=re.IGNORECASE):
            name = name.strip()
            if name:
                prereqs.append(name)

    return skill_levels, prereqs


def parse_perks_tables(soup):
    """Return raw perk rows from all perk wikitables.

    Each row is (name: str, req_td: Tag, description: str).
    """
    raw = []
    for table in soup.find_all('table', class_='wikitable'):
        first_th = table.find('th')
        if not first_th or 'Perk' not in first_th.get_text(strip=True):
            continue
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 3:
                continue
            raw.append((tds[0].get_text(strip=True), tds[1], tds[2].get_text(strip=True)))
    return raw


def remap_prereqs(names):
    """Apply PREREQ_NAME_MAP to a list of prereq names; return joined string or 'None'."""
    if not names:
        return 'None'
    remapped = [PREREQ_NAME_MAP.get(n, n) for n in names]
    return ', '.join(remapped)


def expand_perks(raw_rows):
    """Expand multi-rank perks; remap bare prereq names for single-rank perks.

    Returns list of dicts with keys: name, skill_level, prerequisite, description.
    """
    result = []

    for perk_name, req_td, desc in raw_rows:
        skill_levels, prereq_names = parse_req_cell(req_td)

        # Check for multi-rank perk: "Enchanter (5)", "Augmented Flames (2)", etc.
        m = re.match(r'^(.+?)\s+\((\d+)\)$', perk_name)

        if m:
            base_name = m.group(1)
            total_ranks = int(m.group(2))

            if base_name == 'Enchanter':
                magnitudes = ENCHANTER_MAGNITUDES
                for i, mag in enumerate(magnitudes):
                    rank = i + 1
                    rank_name = f'Enchanter ({rank}/5)'
                    if rank == 1:
                        prereq = remap_prereqs(prereq_names)
                    else:
                        prereq = f'Enchanter ({rank - 1}/5)'
                    skill = skill_levels[i] if i < len(skill_levels) else skill_levels[-1]
                    result.append({
                        'name': rank_name,
                        'skill_level': skill,
                        'prerequisite': prereq,
                        'description': f'New enchantments are {mag} stronger.',
                    })

            elif base_name in AUGMENTED_ELEMENT_MAP:
                element = AUGMENTED_ELEMENT_MAP[base_name]
                for i, mag in enumerate(AUGMENTED_MAGNITUDES):
                    rank = i + 1
                    rank_name = f'{base_name} ({rank}/{total_ranks})'
                    if rank == 1:
                        prereq = remap_prereqs(prereq_names)
                    else:
                        prereq = f'{base_name} ({rank - 1}/{total_ranks})'
                    skill = skill_levels[i] if i < len(skill_levels) else skill_levels[-1]
                    result.append({
                        'name': rank_name,
                        'skill_level': skill,
                        'prerequisite': prereq,
                        'description': f'{element} enchantments do {mag} more damage.',
                    })

            else:
                # Generic multi-rank perk (not yet encountered, but safe to handle)
                for i in range(total_ranks):
                    rank = i + 1
                    rank_name = f'{base_name} ({rank}/{total_ranks})'
                    if rank == 1:
                        prereq = remap_prereqs(prereq_names)
                    else:
                        prereq = f'{base_name} ({rank - 1}/{total_ranks})'
                    skill = skill_levels[i] if i < len(skill_levels) else skill_levels[-1]
                    result.append({
                        'name': rank_name,
                        'skill_level': skill,
                        'prerequisite': prereq,
                        'description': desc,
                    })
        else:
            # Single-rank perk
            skill = skill_levels[0] if skill_levels else 0
            prereq = remap_prereqs(prereq_names)
            result.append({
                'name': perk_name,
                'skill_level': skill,
                'prerequisite': prereq,
                'description': desc,
            })

    return result


def strip_dlc_marker(name):
    """Remove trailing DLC marker words (DG, DR, DB, HF, CC) from a name."""
    words = name.split()
    while words and words[-1] in DLC_MARKERS:
        words.pop()
    return ' '.join(words)


def parse_effects_table(soup):
    """Return list of {name, school} dicts from the weapon enchantments table.

    The weapons table uses class='article-table', not 'wikitable', so this
    searches all tables and uses header content as the discriminator.
    """
    effects = []
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if 'Enchantment' in headers and 'School' in headers:
            ench_col = headers.index('Enchantment')
            school_col = headers.index('School')
            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if not tds or len(tds) <= max(ench_col, school_col):
                    continue
                name = strip_dlc_marker(tds[ench_col].get_text(separator=' ', strip=True))
                school = tds[school_col].get_text(separator=' ', strip=True)
                if name and school:
                    effects.append({'name': name, 'school': school})
    return effects


def parse_apparel_table(soup):
    """Return list of dicts from the apparel enchantments table.

    Columns: enchantment, head, chest, hands, feet, shield, amulet, ring (True/False).
    """
    slot_cols = ['head', 'chest', 'hands', 'feet', 'shield', 'amulet', 'ring']
    slot_labels = ['Head', 'Chest', 'Hands', 'Feet', 'Shield', 'Amulet', 'Ring']

    for table in soup.find_all('table', class_='wikitable'):
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if not all(lbl in headers for lbl in ['Head', 'Ring']):
            continue
        col_indices = {}
        try:
            col_indices['enchantment'] = headers.index('Enchantment')
        except ValueError:
            col_indices['enchantment'] = 0
        for key, lbl in zip(slot_cols, slot_labels):
            try:
                col_indices[key] = headers.index(lbl)
            except ValueError:
                pass

        rows = []
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
            max_needed = max(col_indices.values())
            if len(tds) <= max_needed:
                continue
            raw_name = tds[col_indices['enchantment']].get_text(strip=True)
            name = raw_name.replace('†', '').strip()  # strip †
            if not name:
                continue
            rec = {'enchantment': name}
            for key in slot_cols:
                idx = col_indices.get(key)
                if idx is not None and idx < len(tds):
                    rec[key] = tds[idx].get_text(strip=True).lower() == 'yes'
                else:
                    rec[key] = False
            rows.append(rec)

        if rows:
            return rows

    return []


def write_raw_file(records, outfile, fields):
    """Write pipe-delimited records to outfile."""
    with open(outfile, 'w', encoding='utf-8') as fh:
        for rec in records:
            line = '|'.join(str(rec[f]) for f in fields)
            fh.write(line + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim enchanting data from the wiki.')
    parser.add_argument('--out-dir', default=str(_SCRIPT_DIR),
                        help='Directory for raw output files')
    args = parser.parse_args()

    out_dir = args.out_dir
    if not op.isdir(out_dir):
        print(f'ERROR: output directory does not exist: {out_dir}', file=sys.stderr)
        sys.exit(1)

    perks_out = op.join(out_dir, 'skyrim_enchant_perks_raw.txt')
    effects_out = op.join(out_dir, 'skyrim_enchant_effects_raw.txt')
    apparel_out = op.join(out_dir, 'skyrim_enchant_apparel_raw.txt')

    session = requests.Session()

    print('Fetching Enchanting_(Skyrim) section 10 (perks)...', file=sys.stderr)
    perks_soup = fetch_section(ENCHANT_PAGE, PERKS_SECTION, session=session)

    raw_rows = parse_perks_tables(perks_soup)
    perks = expand_perks(raw_rows)
    write_raw_file(perks, perks_out,
                   ['name', 'skill_level', 'prerequisite', 'description'])
    print(f'  {len(perks)} perks → {perks_out}', file=sys.stderr)

    print('Fetching Enchanting_(Skyrim) section 13 (enchantments)...', file=sys.stderr)
    enchants_soup = fetch_section(ENCHANT_PAGE, ENCHANTS_SECTION, session=session)

    effects = parse_effects_table(enchants_soup)
    write_raw_file(effects, effects_out, ['name', 'school'])
    print(f'  {len(effects)} enchantment effects → {effects_out}', file=sys.stderr)

    apparel = parse_apparel_table(enchants_soup)
    write_raw_file(apparel, apparel_out,
                   ['enchantment', 'head', 'chest', 'hands', 'feet',
                    'shield', 'amulet', 'ring'])
    print(f'  {len(apparel)} apparel enchantments → {apparel_out}', file=sys.stderr)


if __name__ == '__main__':
    main()
