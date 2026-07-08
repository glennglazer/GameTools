#!/usr/bin/python3

"""
File: oblivion_scrape_wiki.py
Author: Glenn Glazer

Fetch the Oblivion alchemy ingredients table from the Fandom wiki via the
MediaWiki action=parse API and write a pipe-delimited raw.txt file compatible
with the existing oblivion_parse_wiki_to_json.py parser.

Output format per entry (7 lines):
  |               ← separator
  |Name
  |Weight
  |Value
  |Source(s)
  |Effect1,Effect2,Effect3,Effect4
  |FormID

The main Ingredients_(Oblivion) wiki page includes Shivering Isles items inline
(marked {{SI}}), so a single fetch captures all Oblivion alchemy ingredients.

Source URL is read from ../source_urls.txt (relative to this script).
"""

import argparse
import os.path as op
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

GAME = 'oblivion'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
API_URL = 'https://elderscrolls.fandom.com/api.php'
EXPECTED_COLUMNS = 6  # name, weight, value, source, effects, ID

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

    Cells with <br> (effects column): comma-join plain text segments.
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
    """Validate and return the 6 fields for an Oblivion ingredient row, or None."""
    if len(cells) != EXPECTED_COLUMNS:
        return None
    return list(cells)  # name, weight, value, source, effects, ID


def format_entry(fields: list) -> str:
    """Format 6 field values as a 7-line pipe-delimited raw.txt entry."""
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
    parser = argparse.ArgumentParser(description='Scrape Oblivion alchemy ingredients from the wiki.')
    parser.add_argument('--out-dir', help='directory to write raw files to (default: repo .out/)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent.parent.parent
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

    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    all_entries = []
    for i, url in enumerate(urls):
        title = url_to_title(url)
        print(f"Fetching {url} ...")
        soup = fetch_parsed_html(title, session)
        rows = extract_rows(soup)
        entries = [format_entry(f) for r in rows if (f := fields_from_row(r)) is not None]
        if not entries:
            raise ValueError(f"No valid entries extracted from '{title}' — page structure may have changed")
        all_entries.extend(entries)
        print(f"  {len(entries)} entries from {title}")
        if i < len(urls) - 1:
            time.sleep(1)

    all_outfile = out_dir / f'{GAME}_all_ingredients_raw.txt'
    write_raw_file(all_entries, str(all_outfile))
    print(f"{len(all_entries)} entries → {all_outfile.name}")
