#!/usr/bin/python3

"""
Fetch per-effect alchemy stats (Base Cost, Base Mag, Base Dur) from UESP
individual effect pages for CC-only alchemy effects — effects not listed on
the base-game Skyrim:Alchemy_Effects page.

Currently one CC-only alchemy effect exists:
  Skyrim:Fortify_Persuasion  (added by Rare Curios; only on Glassfish)

Output JSON (cc_effects_raw.json):
{
  "Fortify Persuasion": {"base_cost": 0.5, "base_mag": 1, "base_dur": 30},
  ...
}
"""

import argparse
import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
UESP_API   = 'https://en.uesp.net/w/api.php'

# UESP page names for CC-only alchemy effects (no namespace prefix needed for
# effect pages — they use the Skyrim: namespace).
CC_EFFECT_PAGES = [
    'Skyrim:Fortify_Persuasion',
]

_SCRIPT_DIR = Path(__file__).parent.resolve()


def _page_title_to_effect_name(page: str) -> str:
    """Convert 'Skyrim:Fortify_Persuasion' → 'Fortify Persuasion'."""
    return page.split(':', 1)[-1].replace('_', ' ')


def fetch_alchemy_stats(page: str, session: requests.Session | None = None) -> dict | None:
    """Return {base_cost, base_mag, base_dur} from the Alchemy infobox section of a UESP effect page.

    Returns None if the Alchemy section or required fields are missing.
    """
    sess = session or requests.Session()
    sess.headers.setdefault('User-Agent', USER_AGENT)

    r = sess.get(UESP_API, params={
        'action': 'parse',
        'page': page,
        'prop': 'text',
        'section': 0,
        'format': 'json',
    }, timeout=20)
    r.raise_for_status()

    html = r.json()['parse']['text']['*']
    soup = BeautifulSoup(html, 'html.parser')

    # The effect infobox is the table whose class includes 'infobox'.
    table = soup.find('table', class_=lambda c: c and 'infobox' in c.split())
    if table is None:
        return None

    stats = {}
    in_alchemy = False

    for row in table.find_all('tr'):
        th = row.find('th')
        td = row.find('td')

        # Detect section boundary rows (colspan=2 th cells).
        if th and th.get('colspan'):
            text = th.get_text(strip=True)
            link_href = (th.find('a') or {}).get('href', '')
            if 'Alchemy_Effects' in link_href or text == 'Alchemy':
                in_alchemy = True
            elif in_alchemy:
                # Entered a new section — stop scanning.
                break
            continue

        if not (in_alchemy and th and td):
            continue

        label = th.get_text(strip=True)
        value = td.get_text(strip=True)
        if label == 'Base Cost':
            stats['base_cost'] = float(value)
        elif label == 'Base Mag':
            stats['base_mag'] = int(value)
        elif label == 'Base Dur':
            stats['base_dur'] = int(value)

    if 'base_mag' not in stats:
        return None
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape alchemy stats for CC-only effects from UESP individual effect pages.',
    )
    parser.add_argument(
        'outfile', nargs='?',
        default=str(_SCRIPT_DIR / 'cc_effects_raw.json'),
        help='output JSON file path (default: cc_effects_raw.json in this directory)',
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    effects: dict = {}
    errors: int = 0
    for page in CC_EFFECT_PAGES:
        effect_name = _page_title_to_effect_name(page)
        print(f"Fetching '{page}' …")
        try:
            stats = fetch_alchemy_stats(page, session)
        except requests.exceptions.RequestException as e:
            print(f"  Network error: {e}", file=sys.stderr)
            errors += 1
            continue
        except (KeyError, ValueError) as e:
            print(f"  Parse error for '{page}': {e}", file=sys.stderr)
            errors += 1
            continue

        if stats is None:
            print(f"  Warning: no Alchemy stats found for '{page}' — skipping", file=sys.stderr)
            errors += 1
            continue

        effects[effect_name] = stats
        print(f"  {effect_name}: base_mag={stats['base_mag']}")

    if errors and not effects:
        print("Error: no effects scraped successfully", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.outfile, 'w') as f:
            json.dump(effects, f, indent=2)
    except OSError as e:
        print(f"Failed to write {args.outfile}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  {len(effects)} CC effects → {args.outfile}")
