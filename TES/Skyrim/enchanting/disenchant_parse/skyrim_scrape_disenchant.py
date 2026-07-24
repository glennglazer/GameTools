#!/usr/bin/env python3
"""
Scrape Skyrim disenchanting source data from UESP Skyrim:Enchanting_Effects.

Section 2 (Apparel Effects) and section 3 (Weapon Effects) each contain a
wikitable where the Disenchant column lists, per effect, every item a player
can destroy to learn that enchantment.  The column uses collapsible divs with
mixed HTML patterns that require semantic parsing.

Produces two raw JSON files (lists of {effect, item, note} records):
  disenchant_apparel_raw.json
  disenchant_weapons_raw.json

These files are the inputs to the two downstream parsers.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UESP_API = 'https://en.uesp.net/w/api.php'
PAGE = 'Skyrim:Enchanting_Effects'
APPAREL_SECTION = 2
WEAPONS_SECTION = 3
USER_AGENT = 'GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)'

_SCRIPT_DIR = Path(__file__).parent.resolve()
_DEFAULT_APPAREL_OUT = str(_SCRIPT_DIR / 'disenchant_apparel_raw.json')
_DEFAULT_WEAPONS_OUT = str(_SCRIPT_DIR / 'disenchant_weapons_raw.json')


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_section(section: int, session=None) -> BeautifulSoup:
    """Fetch one section of Skyrim:Enchanting_Effects via the UESP API."""
    s = session or requests.Session()
    params = {
        'action': 'parse',
        'page': PAGE,
        'prop': 'text',
        'section': section,
        'format': 'json',
    }
    resp = s.get(UESP_API, params=params,
                 headers={'User-Agent': USER_AGENT}, timeout=30)
    resp.raise_for_status()
    html = resp.json()['parse']['text']['*']
    return BeautifulSoup(html, 'html.parser')


# ---------------------------------------------------------------------------
# Shared row-level helpers
# ---------------------------------------------------------------------------

def _effect_name_from_row(row) -> str | None:
    """Extract canonical effect name from a table row.

    Primary: uses the Skyrim wiki link in a TH cell (most reliable).
    Fallback: uses TH text for effects without dedicated wiki pages
    (e.g. 'Alteration &Magicka Regen' dual-enchantment combined effects).
    Group-header TH cells (rowspan > 1) and icon TH cells (File: links) are skipped.
    """
    # Primary: link-based extraction
    for th in row.find_all('th'):
        a = th.find('a', href=lambda h: h and '/wiki/Skyrim:' in h and 'File:' not in h)
        if a:
            href = a['href']
            name = href.split('/wiki/Skyrim:')[1]
            name = name.replace('%27', "'").replace('%22', '"').replace('%26', '&')
            name = name.replace('_', ' ')
            # Strip _(effect) suffix — added to disambiguate wiki pages
            name = re.sub(r'\s*\(effect\)\s*$', '', name, flags=re.IGNORECASE)
            return name

    # Fallback: TH text for effects without dedicated wiki pages
    for th in row.find_all('th'):
        # Skip group-header cells that span multiple rows
        if int(th.get('rowspan', 1)) > 1:
            continue
        # Skip icon cells (contain only a File: image link)
        if th.find('a', href=lambda h: h and 'File:' in h):
            continue
        text = th.get_text(strip=True)
        if text:
            return text

    return None


def _collapsible_content(row):
    """Return the mw-collapsible-content div from the Disenchant td, or None."""
    for td in row.find_all('td'):
        coll = td.find('div', class_='mw-collapsible')
        if coll:
            return coll.find('div', class_='mw-collapsible-content')
    return None


def _title_or_text(link) -> str:
    """Item name from a link: use title attribute (strip 'Skyrim:'), else text.

    Falls back to link text when the title points to a catch-all page
    (Generic Magic Apparel) — in those cases the specific name is in the text.
    """
    title = link.get('title', '')
    if title.startswith('Skyrim:'):
        name = title[len('Skyrim:'):]
        # Generic Magic Apparel is a catch-all page; the specific item name is
        # in the link text (e.g. "Novice Robes", "of Alchemy").
        if 'Generic Magic Apparel' in name:
            return link.get_text(strip=True)
        # Strip trailing disambiguation like " (item)"
        name = re.sub(r'\s*\([^)]+\)\s*$', '', name)
        return name.strip()
    return link.get_text(strip=True)


def _text_before_first_italic(li) -> str:
    """Concatenated text of li direct children up to (not including) the first <i>.

    Skips <sup> children (DLC markers like DG, DB, HF, CC) so they do not
    contaminate item-type names (e.g. 'Vampire ArmorDG' → 'Vampire Armor').
    """
    parts = []
    for child in li.children:
        name = getattr(child, 'name', None)
        if name == 'i':
            break
        if name == 'ul':
            break
        if name == 'sup':
            continue  # skip DLC/CC markers
        if hasattr(child, 'get_text'):
            parts.append(child.get_text())
        else:
            parts.append(str(child))
    return ''.join(parts).strip()


def _direct_italic_texts(li) -> list:
    """Text of all <i> tags in li that are NOT inside its sub-list."""
    inner_ul = li.find('ul', recursive=False)
    texts = []
    for i_tag in li.find_all('i'):
        if inner_ul and inner_ul in i_tag.parents:
            continue
        t = i_tag.get_text(strip=True)
        if t:
            texts.append(t)
    return texts


def _split_item_types(text: str) -> list:
    """Split 'Bracers/Gauntlets, Helmets, and Necklaces' into individual types."""
    result = []
    for part in text.split(','):
        for sp in part.split('/'):
            for ap in re.split(r'\band\b', sp, flags=re.IGNORECASE):
                ap = ap.strip()
                if ap:
                    result.append(ap)
    return result


def _inner_sub_texts(li) -> list:
    """Text lines from first-level sub-list items (the inner <ul><li> nodes)."""
    inner_ul = li.find('ul', recursive=False)
    if not inner_ul:
        return []
    return [x.get_text(separator=' ', strip=True)
            for x in inner_ul.find_all('li', recursive=False)]


def _text_after_link(li, link) -> str:
    """Text of li's direct-child nodes that come after the given link tag."""
    collecting = False
    parts = []
    for child in li.children:
        if child is link:
            collecting = True
            continue
        if not collecting:
            continue
        if getattr(child, 'name', None) == 'ul':
            break
        if hasattr(child, 'get_text'):
            parts.append(child.get_text())
        else:
            parts.append(str(child))
    return ''.join(parts).strip()


# ---------------------------------------------------------------------------
# Apparel <li> parser
# ---------------------------------------------------------------------------

def _parse_apparel_li(effect: str, li, context_note: str | None = None) -> list:
    """Convert one apparel <li> to one or more {effect, item, note} records.

    Handles these patterns found in the UESP collapsible content:
      A – generic item types with "Includes" sub-note → All levels of enchantment
      B – generic item types, no sub-note → note = None (or context_note)
      C – named specific item, no note
      D – named specific item with sub-list note
      E – "Due to a bug, the [Item]..." sentence
      F – paragraph context note (passed in as context_note)
      G – CC items "Elite and Ascendant [Link]s"
      H – "Most" varieties (instead of "All")
      I – multiple italic keywords in one li (Resist Magic)
    """
    # Only items with a <sup> whose text is exactly "CC" are Creation Club items.
    # DLC sups (DG = Dawnguard, DB = Dragonborn, HF = Hearthfire) are not CC.
    has_cc = any(sup.get_text(strip=True) == 'CC' for sup in li.find_all('sup'))
    inner_notes = _inner_sub_texts(li)

    # Build direct_text (text of all children except the sub-list)
    direct_parts = []
    for child in li.children:
        if getattr(child, 'name', None) == 'ul':
            break
        if hasattr(child, 'get_text'):
            direct_parts.append(child.get_text(separator=' '))
        else:
            direct_parts.append(str(child))
    direct_text = re.sub(r'\s+', ' ', ' '.join(direct_parts)).strip()

    # --- Pattern E: bug note ------------------------------------------------
    if re.match(r'due to a bug', direct_text, re.IGNORECASE):
        link = li.find('a')
        if link:
            return [{'effect': effect,
                     'item': _title_or_text(link),
                     'note': 'This is due to a bug.'}]
        return []

    # --- Pattern G: CC items -----------------------------------------------
    if has_cc:
        italic = li.find('i')
        if italic:
            link = italic.find('a')
            base_name = _title_or_text(link) if link else italic.get_text(strip=True)
            prefix = _text_before_first_italic(li)
            parts = [p.strip() for p in re.split(r'\band\b', prefix, flags=re.IGNORECASE)
                     if p.strip()]
            if parts:
                return [{'effect': effect,
                         'item': f'{p} {base_name}',
                         'note': 'Creation Club content'}
                        for p in parts]
            return [{'effect': effect, 'item': base_name, 'note': 'Creation Club content'}]
        return []

    # --- Patterns A / B / H / I: "All" or "Most" generic items -------------
    if re.match(r'^(all|most)\b', direct_text, re.IGNORECASE):
        italic_texts = _direct_italic_texts(li)
        type_text_raw = _text_before_first_italic(li)
        type_text = re.sub(
            r'^(All|Most)\s+(?:varieties of\s+)?', '', type_text_raw,
            flags=re.IGNORECASE,
        ).strip().rstrip(' ,')

        has_includes = any('Includes' in n for n in inner_notes)
        quantifier = 'Most' if re.match(r'^most\b', direct_text, re.IGNORECASE) else 'All'
        if has_includes and quantifier == 'All':
            note = 'All levels of enchantment'
        elif has_includes and quantifier == 'Most':
            note = 'Most varieties; all levels of enchantment'
        elif quantifier == 'Most':
            note = 'Most varieties'
        else:
            note = context_note

        item_types = _split_item_types(type_text) if type_text else []
        records = []
        if not item_types:
            for keyword in italic_texts:
                records.append({'effect': effect, 'item': keyword, 'note': note})
        else:
            for keyword in italic_texts:
                for item_type in item_types:
                    records.append({'effect': effect, 'item': f'{item_type} {keyword}', 'note': note})
        return records

    # --- Patterns C / D: named specific item --------------------------------
    main_link = li.find('a')
    if main_link:
        item_name = _title_or_text(main_link)
        note = context_note
        after_text = _text_after_link(li, main_link)

        if re.match(r'^[-–]', after_text):
            clean = re.sub(r'^[-–]\s*', '', after_text).strip()
            note = (clean[0].upper() + clean[1:]) if clean else ''
            if note and not note.endswith('.'):
                note += '.'
        elif inner_notes:
            note = ' '.join(inner_notes)

        return [{'effect': effect, 'item': item_name, 'note': note}]

    return [{'effect': effect, 'item': direct_text, 'note': context_note}]


# ---------------------------------------------------------------------------
# Weapon <li> parser
# ---------------------------------------------------------------------------

def _parse_weapons_li(effect: str, li, context_note: str | None = None) -> list:
    """Convert one weapon <li> to one or more {effect, item, note} records.

    Patterns in the weapons section:
      A – "All weapons of X" (generic enchantment tier)
      B – "All varieties of [adj] weapons" (Turn Undead)
      C – named specific item, no note
      D – named specific item with inline dash note
    """
    inner_ul = li.find('ul', recursive=False)
    inner_notes = [x.get_text(separator=' ', strip=True)
                   for x in inner_ul.find_all('li', recursive=False)] if inner_ul else []

    direct_parts = []
    for child in li.children:
        if getattr(child, 'name', None) == 'ul':
            break
        if hasattr(child, 'get_text'):
            direct_parts.append(child.get_text(separator=' '))
        else:
            direct_parts.append(str(child))
    direct_text = re.sub(r'\s+', ' ', ' '.join(direct_parts)).strip()

    # --- Pattern A: "All weapons of X" -------------------------------------
    if re.match(r'^all weapons\b', direct_text, re.IGNORECASE):
        italic_texts = _direct_italic_texts(li)
        records = []
        for keyword in italic_texts:
            records.append({'effect': effect,
                            'item': f'All weapons {keyword}',
                            'note': context_note})
        if not italic_texts:
            records.append({'effect': effect, 'item': direct_text, 'note': context_note})
        return records

    # --- Pattern B: "All varieties of [adj] weapons" (Turn Undead) ---------
    if re.match(r'^all varieties of\b', direct_text, re.IGNORECASE):
        italic_texts = _direct_italic_texts(li)
        return [{'effect': effect,
                 'item': f'{adj} weapons',
                 'note': context_note}
                for adj in italic_texts]

    # --- Patterns C / D: named specific item --------------------------------
    main_link = li.find('a')
    if main_link:
        item_name = _title_or_text(main_link)
        note = context_note
        after_text = _text_after_link(li, main_link)

        if re.match(r'^[-–]', after_text):
            clean = re.sub(r'^[-–]\s*', '', after_text).strip()
            note = (clean[0].upper() + clean[1:]) if clean else ''
            if note and not note.endswith('.'):
                note += '.'
        elif inner_notes:
            note = ' '.join(inner_notes)

        return [{'effect': effect, 'item': item_name, 'note': note}]

    return [{'effect': effect, 'item': direct_text, 'note': context_note}]


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------

def _parse_section(soup, li_parser) -> list:
    """Walk the wikitable in soup; apply li_parser to each collapsible's items."""
    records = []
    table = soup.find('table', class_='wikitable')
    if not table:
        return records

    current_effect = None
    for row in table.find_all('tr'):
        name = _effect_name_from_row(row)
        if name:
            current_effect = name

        if not current_effect:
            continue

        content = _collapsible_content(row)
        if not content:
            continue

        pending_note = None
        for child in content.children:
            tag_name = getattr(child, 'name', None)
            if tag_name == 'p':
                p_text = child.get_text(strip=True)
                if p_text.endswith(':'):
                    p_text = p_text[:-1] + '.'
                pending_note = p_text
            elif tag_name == 'ul':
                for li in child.find_all('li', recursive=False):
                    records.extend(li_parser(current_effect, li, pending_note))
                pending_note = None

    return records


def parse_apparel_section(soup) -> list:
    """Return {effect, item, note} records from the Apparel Effects table."""
    return _parse_section(soup, _parse_apparel_li)


def parse_weapons_section(soup) -> list:
    """Return {effect, item, note} records from the Weapon Effects table."""
    return _parse_section(soup, _parse_weapons_li)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Scrape Skyrim disenchanting data from UESP.')
    parser.add_argument('--apparel-out', default=_DEFAULT_APPAREL_OUT,
                        help='Output path for disenchant_apparel_raw.json')
    parser.add_argument('--weapons-out', default=_DEFAULT_WEAPONS_OUT,
                        help='Output path for disenchant_weapons_raw.json')
    args = parser.parse_args()

    for path in [args.apparel_out, args.weapons_out]:
        parent = Path(path).parent
        if not parent.exists():
            print(f'ERROR: output directory does not exist: {parent}', file=sys.stderr)
            sys.exit(1)

    session = requests.Session()

    print('Fetching Skyrim:Enchanting_Effects section 2 (Apparel)...', file=sys.stderr)
    apparel_soup = fetch_section(APPAREL_SECTION, session=session)
    apparel_records = parse_apparel_section(apparel_soup)
    with open(args.apparel_out, 'w', encoding='utf-8') as f:
        json.dump(apparel_records, f, indent=2)
    print(f'  {len(apparel_records)} apparel records → {args.apparel_out}', file=sys.stderr)

    print('Fetching Skyrim:Enchanting_Effects section 3 (Weapons)...', file=sys.stderr)
    weapons_soup = fetch_section(WEAPONS_SECTION, session=session)
    weapons_records = parse_weapons_section(weapons_soup)
    with open(args.weapons_out, 'w', encoding='utf-8') as f:
        json.dump(weapons_records, f, indent=2)
    print(f'  {len(weapons_records)} weapon records → {args.weapons_out}', file=sys.stderr)


if __name__ == '__main__':
    main()
