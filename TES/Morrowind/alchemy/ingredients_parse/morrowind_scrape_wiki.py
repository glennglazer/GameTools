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
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

GAME = 'morrowind'
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
API_URL = 'https://elderscrolls.fandom.com/api.php'
EXPECTED_COLUMNS = 8  # name, weight, value, e1, e2, e3, e4, ID

# DLC icon text that Fandom renders as visible text inside <a> or as plain text
DLC_MARKERS = frozenset(['SI', 'KotN', 'MR', 'VH', 'FS', 'TC', 'HF', 'DG', 'DB', 'CC'])


def _link_text(a_tag) -> str:
    """Return wiki-link format text for a rendered <a> tag.

    Reconstructs 'Page Title (Game)|Display' from the href when the page title
    differs from the display text, which preserves disambiguation info.
    Returns plain display text when they match, or '' for DLC marker links.
    """
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

    Cells with <br> (Oblivion-style effects): comma-join plain text segments.
    All other cells: space-join, reconstructing 'Page|Display' from hrefs.
    DLC marker icons (SI, DG, etc.) are silently filtered.
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
    """Validate and return the 8 fields for a Morrowind ingredient row, or None.

    Empty effect cells (no effect in that slot) become '-' so the downstream
    parser's dash_to_null() converts them to None correctly.
    """
    if len(cells) != EXPECTED_COLUMNS:
        return None
    result = list(cells)
    for i in range(3, 7):  # effect columns
        if not result[i]:
            result[i] = '-'
    return result


def format_entry(fields: list) -> str:
    """Format 8 field values as a 9-line pipe-delimited raw.txt entry."""
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


def title_to_stem(title: str) -> str:
    """Convert a page title like 'Ingredients_(Morrowind)' to a file stem."""
    m = re.search(r'\(([^)]+)\)', title)
    expansion = m.group(1).lower().replace(' ', '_') if m else 'unknown'
    return 'base' if expansion == GAME else expansion


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Morrowind alchemy ingredients from the wiki.')
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
        if not entries:
            raise ValueError(f"No valid entries extracted from '{title}' — page structure may have changed")
        write_raw_file(entries, str(outfile))
        print(f"  {len(entries)} entries → {outfile.name}")
        per_url_files.append(outfile)

        if i < len(urls) - 1:
            time.sleep(1)

    # Combine all per-URL files into the _all_ file
    all_outfile = out_dir / f'{GAME}_all_ingredients_raw.txt'
    try:
        all_content = ''.join(p.read_text() for p in per_url_files)
        all_outfile.write_text(all_content)
    except OSError as e:
        print(f"Failed to write combined file {all_outfile.name}: {e}")
        raise
    total = sum(1 for line in all_content.splitlines() if line == '|')
    print(f"Combined {total} entries → {all_outfile.name}")
