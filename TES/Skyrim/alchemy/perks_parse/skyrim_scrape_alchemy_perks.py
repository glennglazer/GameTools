#!/usr/bin/python3

"""
File: skyrim_scrape_alchemy_perks.py
Author: Glenn Glazer

Fetch the Perks section of Alchemy_(Skyrim) from the Fandom wiki via the
MediaWiki action=parse API, expand multi-rank perks, and write a pipe-delimited
raw text file for the JSON parser.

Output format (one line per perk):
  name|skill_level|prerequisite|description

Multi-rank expansion rules:
  Alchemist (5 ranks, skill 0/20/40/60/80):
    Alchemist (1/5)  – no prerequisite
    Alchemist (2/5)  – requires Alchemist (1/5)
    ...
    Alchemist (5/5)  – requires Alchemist (4/5)

  Experimenter (3 ranks, skill 50/70/90):
    Experimenter (1/3) – requires Benefactor
    Experimenter (2/3) – requires Experimenter (1/3)
    Experimenter (3/3) – requires Experimenter (2/3)

  Snakeblood uses 'Experimenter (1/3)' (rank 1 is sufficient).
  All other bare 'Alchemist' prerequisites map to 'Alchemist (1/5)'.
"""

import argparse
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

GAME = 'skyrim'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
API_URL = 'https://elderscrolls.fandom.com/api.php'
PAGE_TITLE = 'Alchemy_(Skyrim)'
PERKS_SECTION = 11

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_OUT = str(_SCRIPT_DIR / 'skyrim_alchemy_perks_raw.txt')

PREREQ_NAME_MAP = {
    'Alchemist': 'Alchemist (1/5)',
    'Experimenter': 'Experimenter (1/3)',
}

ALCHEMIST_MAGNITUDES = ['20%', '40%', '60%', '80%', '100%']

EXPERIMENTER_DESCS = [
    'Eating an ingredient reveals the first two effects.',
    'Eating an ingredient reveals the first three effects.',
    'Eating an ingredient reveals all four effects.',
]


def fetch_perks_html(session=None) -> BeautifulSoup:
    """Fetch rendered HTML for the Perks section of Alchemy_(Skyrim)."""
    sess = session or requests.Session()
    sess.headers.setdefault('User-Agent', USER_AGENT)
    try:
        r = sess.get(API_URL, params={
            'action': 'parse',
            'page': PAGE_TITLE,
            'prop': 'text',
            'section': PERKS_SECTION,
            'format': 'json',
        }, timeout=20)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error fetching '{PAGE_TITLE}': {e}", file=sys.stderr)
        raise
    try:
        html = r.json()['parse']['text']['*']
    except (KeyError, ValueError) as e:
        print(f"Unexpected API response for '{PAGE_TITLE}': {e}", file=sys.stderr)
        raise
    return BeautifulSoup(html, 'html.parser')


def parse_perks_table(soup: BeautifulSoup) -> list:
    """Parse the wikitable in the Perks section.

    Returns a list of (name, req_str, desc) tuples — one per table row,
    in wiki order (multi-rank perks appear as a single row at this stage).
    """
    table = soup.find('table', class_='wikitable')
    if not table:
        raise ValueError('No wikitable found in the Perks section HTML')

    rows = []
    for tr in table.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        if not cells or not any(c.name == 'td' for c in cells):
            continue
        if len(cells) < 3:
            continue
        name = ' '.join(cells[0].get_text(separator=' ').split())
        req  = ' '.join(cells[1].get_text(separator=' ').split())
        desc = ' '.join(cells[2].get_text(separator=' ').split())
        rows.append((name, req, desc))
    return rows


def parse_skill_levels(req_str: str) -> list:
    """Extract Alchemy skill level numbers from a requirement string.

    'Alchemy 0/ 20/ 40/ 60/ 80' -> [0, 20, 40, 60, 80]
    'Alchemy 20, Alchemist'      -> [20]
    """
    m = re.search(r'Alchemy\s+([\d/\s]+)', req_str)
    if not m:
        return []
    return [int(n.strip()) for n in m.group(1).split('/') if n.strip().isdigit()]


def parse_prereq_names(req_str: str) -> list:
    """Extract prerequisite perk names from a requirement string.

    'Alchemy 20, Alchemist'                        -> ['Alchemist']
    'Alchemy 80, Concentrated Poison, Experimenter' -> ['Concentrated Poison', 'Experimenter']
    'Alchemy 0/ 20/ 40/ 60/ 80'                   -> []
    """
    cleaned = re.sub(r'Alchemy\s+[\d/\s]+', '', req_str)
    parts = [p.strip().strip(',').strip() for p in cleaned.split(',')]
    return [p for p in parts if p]


def clean_description(desc: str) -> str:
    """Strip editor-note parentheticals from perk descriptions.

    Removes text starting at the first '(' whose content begins with a
    lowercase letter (editor commentary, not part of the game text).
    """
    m = re.match(r'^(.*?)\s*\([a-z]', desc)
    text = m.group(1) if m else desc
    text = text.rstrip('.').strip()
    return text + '.'


def remap_prereqs(names: list) -> str:
    """Remap raw wiki perk names to expanded names; return as comma-separated string."""
    remapped = [PREREQ_NAME_MAP.get(p, p) for p in names]
    return ', '.join(remapped) if remapped else 'None'


def expand_perks(raw_rows: list) -> list:
    """Expand multi-rank perks and return a flat list of perk dicts.

    Each dict: {name, skill_level, prerequisite, description}
    """
    result = []
    for raw_name, req_str, raw_desc in raw_rows:
        ranks_m = re.search(r'\((\d+)\)\s*$', raw_name.strip())
        total_ranks = int(ranks_m.group(1)) if ranks_m else 1
        base_name = re.sub(r'\s*\(\d+\)\s*$', '', raw_name.strip())

        skill_levels = parse_skill_levels(req_str)
        prereqs = parse_prereq_names(req_str)

        if base_name == 'Alchemist' and total_ranks == 5:
            for i in range(5):
                skill = skill_levels[i] if i < len(skill_levels) else 0
                prereq = 'None' if i == 0 else f'Alchemist ({i}/5)'
                desc = f'Potions and poisons are {ALCHEMIST_MAGNITUDES[i]} stronger.'
                result.append({
                    'name': f'Alchemist ({i + 1}/5)',
                    'skill_level': skill,
                    'prerequisite': prereq,
                    'description': desc,
                })

        elif base_name == 'Experimenter' and total_ranks == 3:
            for i in range(3):
                skill = skill_levels[i] if i < len(skill_levels) else 50
                if i == 0:
                    prereq = remap_prereqs(prereqs)
                else:
                    prereq = f'Experimenter ({i}/3)'
                result.append({
                    'name': f'Experimenter ({i + 1}/3)',
                    'skill_level': skill,
                    'prerequisite': prereq,
                    'description': EXPERIMENTER_DESCS[i],
                })

        else:
            skill = skill_levels[0] if skill_levels else 0
            result.append({
                'name': base_name,
                'skill_level': skill,
                'prerequisite': remap_prereqs(prereqs),
                'description': clean_description(raw_desc),
            })

    return result


def format_line(perk: dict) -> str:
    """Format one perk dict as a pipe-delimited line."""
    return f"{perk['name']}|{perk['skill_level']}|{perk['prerequisite']}|{perk['description']}"


def write_raw_file(perks: list, outfile: str) -> None:
    """Write one perk per line to the raw output file."""
    try:
        with open(outfile, 'w') as f:
            for perk in perks:
                f.write(format_line(perk) + '\n')
    except OSError as e:
        print(f"Failed to write {outfile}: {e}", file=sys.stderr)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim alchemy perks from the Fandom wiki.'
    )
    parser.add_argument('--out-dir', help='directory to write raw file (default: script directory)')
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve() if args.out_dir else _SCRIPT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    outfile = str(out_dir / 'skyrim_alchemy_perks_raw.txt')

    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    print(f"Fetching perks section from '{PAGE_TITLE}' ...")
    soup = fetch_perks_html(session)
    raw_rows = parse_perks_table(soup)
    if not raw_rows:
        print("No perk rows found — page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    perks = expand_perks(raw_rows)
    if not perks:
        print("Perk expansion produced no results.", file=sys.stderr)
        sys.exit(1)

    write_raw_file(perks, outfile)
    print(f"  {len(perks)} perks → {Path(outfile).name}")
