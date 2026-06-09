#!/usr/bin/python3

"""
File: skyrim_scrape_wiki.py
Author: Glenn Glazer

Fetch Skyrim alchemy ingredient tables from the Fandom wiki via the MediaWiki
action=parse API and write a pipe-delimited raw.txt file compatible with the
existing skyrim_parse_wiki_to_json.py parser.

Output format per entry (10 lines):
  |               ← separator
  |Name
  |Effect 1
  |Effect 2
  |Effect 3
  |Effect 4
  |Weight
  |Value
  |               ← location (blank; wiki no longer has this column)
  |FormID

The Skyrim page uses DPL templates that render as 5 ingredient tables on one
page (base, Hearthfire, Dawnguard, Dragonborn, Creation Club), followed by a
sixth Potions table. Only tables whose first header cell is "Ingredient" are
collected.

Source URL is read from ../source_urls.txt (relative to this script).
"""

import argparse
import os.path as op
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

GAME = 'skyrim'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
API_URL = 'https://elderscrolls.fandom.com/api.php'
EXPECTED_COLUMNS = 8   # name, e1, e2, e3, e4, weight, value, ID (no location)
OUTPUT_FIELDS = 9      # above 8 + empty location placeholder


def fetch_parsed_html(page_title: str, session=None) -> BeautifulSoup:
    """Fetch rendered HTML for a Fandom wiki page via the action=parse API."""
    sess = session or requests.Session()
    sess.headers.setdefault('User-Agent', USER_AGENT)
    r = sess.get(API_URL, params={
        'action': 'parse',
        'page': page_title,
        'prop': 'text',
        'format': 'json',
    }, timeout=20)
    r.raise_for_status()
    html = r.json()['parse']['text']['*']
    return BeautifulSoup(html, 'html.parser')


def cell_text(tag) -> str:
    """Extract clean text from a cell, joining br-separated values with comma."""
    return ','.join(s.strip() for s in tag.strings if s.strip())


def extract_rows(soup: BeautifulSoup, all_tables: bool = True) -> list:
    """Extract data rows from ingredient wikitables.

    When all_tables=True (default for Skyrim), collects rows from all tables
    whose first column header is 'Ingredient'. Tables with other first headers
    (e.g. 'Potion') are skipped.
    """
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        return []

    if all_tables:
        target_tables = [
            t for t in tables
            if t.find('th') and t.find('th').get_text(strip=True) == 'Ingredient'
        ]
    else:
        target_tables = [tables[0]]

    rows = []
    for table in target_tables:
        for tr in table.find_all('tr'):
            cells = tr.find_all(['td', 'th'])
            if not any(c.name == 'td' for c in cells):
                continue  # skip header-only rows
            rows.append([cell_text(c) for c in cells])
    return rows


def fields_from_row(cells: list) -> list:
    """Return 9 output fields for a Skyrim ingredient row, or None.

    Inserts a blank location placeholder (field 8) since the wiki no longer
    has a location column, but the parser expects 10 lines per entry.
    """
    if len(cells) != EXPECTED_COLUMNS:
        return None
    # cells: name, e1, e2, e3, e4, weight, value, ID
    # output: name, e1, e2, e3, e4, weight, value, '' (location), ID
    return list(cells[:7]) + [''] + [cells[7]]


def format_entry(fields: list) -> str:
    """Format 9 field values as a 10-line pipe-delimited raw.txt entry."""
    lines = ['|'] + [f'|{f}' for f in fields]
    return '\n'.join(lines) + '\n'


def write_raw_file(entries: list, outfile: str) -> None:
    """Write formatted entry strings to outfile."""
    with open(outfile, 'w') as f:
        f.write(''.join(entries))


def url_to_title(url: str) -> str:
    """Extract wiki page title from a Fandom URL."""
    return url.rstrip('/').split('/wiki/')[-1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Skyrim alchemy ingredients from the wiki.')
    parser.add_argument('--out-dir', help='directory to write raw files to (default: script directory)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else script_dir
    source_urls_file = script_dir.parent / 'source_urls.txt'

    if not source_urls_file.exists():
        print(f"source_urls.txt not found at {source_urls_file}", file=sys.stderr)
        sys.exit(1)

    urls = [
        line.strip()
        for line in source_urls_file.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]

    if len(urls) != 1:
        print(f"Warning: expected 1 URL for Skyrim, got {len(urls)}. Using first URL only.", file=sys.stderr)

    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    title = url_to_title(urls[0])
    print(f"Fetching {urls[0]} ...")
    soup = fetch_parsed_html(title, session)
    rows = extract_rows(soup, all_tables=True)
    entries = [format_entry(f) for r in rows if (f := fields_from_row(r)) is not None]

    outfile = out_dir / f'{GAME}_all_ingredients_raw.txt'
    write_raw_file(entries, str(outfile))
    print(f"  {len(entries)} entries → {outfile.name}")
