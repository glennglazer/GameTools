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
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

GAME = 'skyrim'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
API_URL = 'https://elderscrolls.fandom.com/api.php'
EXPECTED_COLUMNS = 8   # name, e1, e2, e3, e4, weight, value, ID (no location)
OUTPUT_FIELDS = 9      # above 8 + empty location placeholder

DLC_MARKERS = frozenset(['SI', 'KotN', 'MR', 'VH', 'FS', 'TC', 'HF', 'DG', 'DB', 'CC'])


def _link_text(a_tag) -> str:
    """Return wiki-link format text for a rendered <a> tag."""
    href = a_tag.get('href', '')
    display = a_tag.get_text(strip=True)
    if not display or display in DLC_MARKERS:
        return ''
    if '/wiki/' not in href:
        return display
    page_title = unquote(href.split('/wiki/')[-1]).replace('_', ' ').strip()
    if page_title and page_title != display:
        return f'{page_title}|{display}'
    return display


def fetch_parsed_html(page_title: str, session=None) -> BeautifulSoup:
    """Fetch rendered HTML for a Fandom wiki page via the action=parse API."""
    sess = session or requests.Session()
    sess.headers.setdefault('User-Agent', USER_AGENT)
    try:
        r = sess.get(API_URL, params={
            'action': 'parse',
            'page': page_title,
            'prop': 'text',
            'format': 'json',
        }, timeout=20)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Network or HTTP error fetching wiki page '{page_title}': {e}")
        raise
    try:
        html = r.json()['parse']['text']['*']
    except (KeyError, ValueError) as e:
        print(f"Unexpected API response structure for page '{page_title}': {e}")
        raise
    return BeautifulSoup(html, 'html.parser')


def cell_text(tag) -> str:
    """Extract text from a table cell, preserving wiki link disambiguation.

    Cells with <br>: comma-join plain text segments.
    All other cells: space-join, reconstructing 'Page|Display' from hrefs.
    DLC marker icons are silently filtered.
    """
    if tag.find('br'):
        parts, current = [], []
        for node in tag.descendants:
            name = getattr(node, 'name', None)
            if name == 'br':
                seg = ' '.join(p for p in current if p).strip()
                if seg:
                    parts.append(seg)
                current = []
            elif name == 'a':
                d = node.get_text(strip=True)
                if d and d not in DLC_MARKERS:
                    current.append(d)
            elif name is None:
                if getattr(node.parent, 'name', None) == 'a':
                    continue
                t = str(node).strip()
                if t and t not in DLC_MARKERS:
                    current.append(t)
        seg = ' '.join(p for p in current if p).strip()
        if seg:
            parts.append(seg)
        return ','.join(parts)
    else:
        parts = []
        for node in tag.descendants:
            name = getattr(node, 'name', None)
            if name == 'a':
                lt = _link_text(node)
                if lt:
                    parts.append(lt)
            elif name is None:
                if getattr(node.parent, 'name', None) == 'a':
                    continue
                t = str(node).strip()
                if t and t not in DLC_MARKERS:
                    parts.append(t)
        return ' '.join(parts).strip()


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
    result = list(cells[:7]) + [''] + [cells[7]]
    # Parser uses int() for value; DLC pages sometimes render whole numbers as '2.0'.
    # Normalise to int string to prevent ValueError.
    val = result[6]
    if '.' in val:
        try:
            result[6] = str(int(float(val)))
        except (ValueError, TypeError):
            pass
    return result


def format_entry(fields: list) -> str:
    """Format 9 field values as a 10-line pipe-delimited raw.txt entry."""
    lines = ['|'] + [f'|{f}' for f in fields]
    return '\n'.join(lines) + '\n'


def write_raw_file(entries: list, outfile: str) -> None:
    """Write formatted entry strings to outfile."""
    try:
        with open(outfile, 'w') as f:
            f.write(''.join(entries))
    except OSError as e:
        print(f"Failed to write output file {outfile}: {e}")
        raise


def url_to_title(url: str) -> str:
    """Extract wiki page title from a Fandom URL."""
    return url.rstrip('/').split('/wiki/')[-1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Skyrim alchemy ingredients from the wiki.')
    parser.add_argument('--out-dir', help='directory to write raw files to (default: repo .out/)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent.parent
    default_out = repo_root / '.out'
    out_dir = Path(args.out_dir).resolve() if args.out_dir else default_out
    out_dir.mkdir(parents=True, exist_ok=True)
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
    if not entries:
        raise ValueError(f"No valid entries extracted from '{title}' — page structure may have changed")

    outfile = out_dir / f'{GAME}_all_ingredients_raw.txt'
    write_raw_file(entries, str(outfile))
    print(f"  {len(entries)} entries → {outfile.name}")
