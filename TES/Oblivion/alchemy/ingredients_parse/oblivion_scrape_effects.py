#!/usr/bin/python3

"""
Fetch Oblivion alchemy effect base costs from the UESP wiki and write a JSON
mapping of effect_name → {base_cost}.

Source: https://en.uesp.net/wiki/Oblivion:Spell_Effects

Output JSON format:
{
  "Restore Health": {"base_cost": 10.0},
  "Damage Health": {"base_cost": 12.0},
  ...
}

Names are stored exactly as they appear on the wiki (generic forms: "Restore
Attribute", "Damage Attribute", etc.).  The parser expands these to their
specific variants ("Restore Intelligence", "Damage Agility", etc.) via
load_effects_raw().
"""

import argparse
import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'
UESP_API   = 'https://en.uesp.net/w/api.php'
PAGE       = 'Oblivion:Spell_Effects'

_SCRIPT_DIR = Path(__file__).parent.resolve()


def fetch_effect_list(session: requests.Session | None = None) -> dict:
    """Fetch the Spell Effects table from UESP and return effect_name → {base_cost}."""
    sess = session or requests.Session()
    sess.headers.setdefault('User-Agent', USER_AGENT)

    r = sess.get(UESP_API, params={
        'action': 'parse',
        'page': PAGE,
        'prop': 'text',
        'format': 'json',
    }, timeout=30)
    r.raise_for_status()

    html = r.json()['parse']['text']['*']
    soup = BeautifulSoup(html, 'html.parser')

    effects = {}
    for table in soup.find_all('table', class_='wikitable'):
        for row in table.find_all('tr')[1:]:
            tds = row.find_all('td')
            if len(tds) < 3:
                continue
            effect_name = tds[0].get_text(strip=True)
            # Column order: Effect Name | Effect ID | Base Cost | Barter Factor | Description
            try:
                base_cost = float(tds[2].get_text(strip=True))
            except (ValueError, IndexError) as e:
                print(f"Warning: could not parse row for '{effect_name}': {e}", file=sys.stderr)
                continue
            if effect_name:
                effects[effect_name] = {'base_cost': base_cost}

    return effects


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape Oblivion spell effect base costs from UESP.',
    )
    parser.add_argument(
        'outfile', nargs='?',
        default=str(_SCRIPT_DIR / 'oblivion_effects_raw.json'),
        help='output JSON file path (default: oblivion_effects_raw.json in this directory)',
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
