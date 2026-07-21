#!/usr/bin/python3

"""
Fetch the Skyrim alchemy Effect List from the UESP wiki and write a JSON
mapping of effect_name → {base_cost, base_mag, base_dur}.

Source: https://en.uesp.net/wiki/Skyrim:Alchemy_Effects (Effect List section)

Output JSON format:
{
  "Cure Disease": {"base_cost": 0.5, "base_mag": 5, "base_dur": 0},
  ...
}

Names are stored exactly as they appear on the wiki.  The parser
(skyrim_parse_wiki_to_json.py) performs case-insensitive matching when it
joins this data to ingredient effects, so capitalisation differences between
sources (e.g. "Fortify One-handed" vs "Fortify One-Handed") are handled there.
"""

import argparse
import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
UESP_API   = 'https://en.uesp.net/w/api.php'
PAGE       = 'Skyrim:Alchemy_Effects'
SECTION    = 6   # "Effect List" section index

_SCRIPT_DIR = Path(__file__).parent.resolve()


def fetch_effect_list(session: requests.Session | None = None) -> dict:
    """Fetch the Effect List section from UESP and return effect_name → metadata."""
    sess = session or requests.Session()
    sess.headers.setdefault('User-Agent', USER_AGENT)

    r = sess.get(UESP_API, params={
        'action': 'parse',
        'page': PAGE,
        'prop': 'text',
        'section': SECTION,
        'format': 'json',
    }, timeout=20)
    r.raise_for_status()

    html = r.json()['parse']['text']['*']
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='wikitable')
    if table is None:
        raise ValueError(f"No wikitable found in section {SECTION} of '{PAGE}' — page structure may have changed")

    effects = {}
    for row in table.find_all('tr')[1:]:   # skip the header row
        th = row.find('th')
        tds = row.find_all('td')
        if not th or len(tds) < 5:
            continue
        # The effect name is in the first <a> inside the row header.
        link = th.find('a')
        effect_name = link.get_text(strip=True) if link else th.get_text(strip=True)
        # Columns: Ingredients(0), Description(1), Base_Cost(2), Base_Mag(3), Base_Dur(4)
        try:
            base_cost = float(tds[2].get_text(strip=True))
            base_mag  = int(tds[3].get_text(strip=True))
            base_dur  = int(tds[4].get_text(strip=True))
        except (ValueError, IndexError) as e:
            print(f"Warning: could not parse row for '{effect_name}': {e}", file=sys.stderr)
            continue
        effects[effect_name] = {'base_cost': base_cost, 'base_mag': base_mag, 'base_dur': base_dur}

    return effects


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim alchemy effect metadata (base_cost, base_mag, base_dur) from UESP.',
    )
    parser.add_argument(
        'outfile', nargs='?',
        default=str(_SCRIPT_DIR / 'skyrim_effects_raw.json'),
        help='output JSON file path (default: skyrim_effects_raw.json in this directory)',
    )
    args = parser.parse_args()

    print(f"Fetching '{PAGE}' from UESP …")
    try:
        effects = fetch_effect_list()
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError) as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    if not effects:
        print("Error: no effects parsed from UESP page", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.outfile, 'w') as f:
            json.dump(effects, f, indent=2)
    except OSError as e:
        print(f"Failed to write {args.outfile}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  {len(effects)} effects → {args.outfile}")
