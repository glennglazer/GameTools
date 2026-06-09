#!/usr/bin/python3

"""
File: morrowind_scrape_wiki.py
Author: Glenn Glazer

Fetch Morrowind alchemy ingredient tables from the Fandom wiki via the MediaWiki
action=parse API and write pipe-delimited raw.txt files compatible with the
existing morrowind_parse_wiki_to_json.py parser.

Output format per entry (9 lines):
  |               ← separator
  |Name
  |Weight
  |Value
  |Effect 1
  |Effect 2
  |Effect 3
  |Effect 4
  |FormID

Source URLs are read from ../source_urls.txt (relative to this script).
One per-URL raw file is written per source, plus a combined _all_ file.
"""

import argparse
import os.path as op
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

GAME = 'morrowind'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
API_URL = 'https://elderscrolls.fandom.com/api.php'
EXPECTED_COLUMNS = 8  # name, weight, value, e1, e2, e3, e4, ID


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


def extract_rows(soup: BeautifulSoup, all_tables: bool = False) -> list:
    """Extract data rows from wikitable(s). Returns list of cell-text lists."""
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        return []

    target_tables = tables if all_tables else [tables[0]]

    rows = []
    for table in target_tables:
        for tr in table.find_all('tr'):
            cells = tr.find_all(['td', 'th'])
            if not any(c.name == 'td' for c in cells):
                continue  # skip header-only rows
            rows.append([cell_text(c) for c in cells])
    return rows


def fields_from_row(cells: list) -> list:
    """Validate and return the 8 fields for a Morrowind ingredient row, or None."""
    if len(cells) != EXPECTED_COLUMNS:
        return None
    return list(cells)  # name, weight, value, e1, e2, e3, e4, ID


def format_entry(fields: list) -> str:
    """Format 8 field values as a 9-line pipe-delimited raw.txt entry."""
    lines = ['|'] + [f'|{f}' for f in fields]
    return '\n'.join(lines) + '\n'


def write_raw_file(entries: list, outfile: str) -> None:
    """Write formatted entry strings to outfile."""
    with open(outfile, 'w') as f:
        f.write(''.join(entries))


def url_to_title(url: str) -> str:
    """Extract wiki page title from a Fandom URL."""
    return url.rstrip('/').split('/wiki/')[-1]


def title_to_stem(title: str) -> str:
    """Convert a page title like 'Ingredients_(Morrowind)' to a file stem."""
    m = re.search(r'\(([^)]+)\)', title)
    expansion = m.group(1).lower().replace(' ', '_') if m else 'unknown'
    return 'base' if expansion == GAME else expansion


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Morrowind alchemy ingredients from the wiki.')
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

    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    per_url_files = []
    for i, url in enumerate(urls):
        title = url_to_title(url)
        stem = title_to_stem(title)
        outfile = out_dir / f'{GAME}_{stem}_ingredients_raw.txt'

        print(f"Fetching {url} ...")
        soup = fetch_parsed_html(title, session)
        rows = extract_rows(soup)
        entries = [format_entry(f) for r in rows if (f := fields_from_row(r)) is not None]
        write_raw_file(entries, str(outfile))
        print(f"  {len(entries)} entries → {outfile.name}")
        per_url_files.append(outfile)

        if i < len(urls) - 1:
            time.sleep(1)

    # Combine all per-URL files into the _all_ file
    all_outfile = out_dir / f'{GAME}_all_ingredients_raw.txt'
    all_content = ''.join(p.read_text() for p in per_url_files)
    all_outfile.write_text(all_content)
    total = sum(1 for line in all_content.splitlines() if line == '|')
    print(f"Combined {total} entries → {all_outfile.name}")
