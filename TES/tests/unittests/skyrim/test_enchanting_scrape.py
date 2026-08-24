"""Tests for TES/Skyrim/enchanting/enchant_parse/skyrim_scrape_enchanting.py"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    'TES/Skyrim/enchanting/enchant_parse/skyrim_scrape_enchanting.py',
    'sk_enchant_scrape',
)
fetch_section      = _mod.fetch_section
parse_req_cell     = _mod.parse_req_cell
parse_perks_tables = _mod.parse_perks_tables
expand_perks       = _mod.expand_perks
strip_dlc_marker   = _mod.strip_dlc_marker
parse_effects_table = _mod.parse_effects_table
parse_apparel_table = _mod.parse_apparel_table
write_raw_file     = _mod.write_raw_file


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

PERKS_TABLE_HTML = """
<table class="wikitable">
<tr><th>Perk (Ranks)</th><th>Requirements</th><th>Description</th></tr>
<tr>
  <td>Enchanter (5)</td>
  <td>Enchanting 0/20/40/60/80</td>
  <td>New enchantments are 20/40/60/80/100% stronger.</td>
</tr>
<tr>
  <td>Soul Squeezer</td>
  <td>Enchanting 20<br/>Enchanter</td>
  <td>Soul gems provide extra magicka for recharging.</td>
</tr>
<tr>
  <td>Extra Effect</td>
  <td>Enchanting 100<br/>Storm Enchanter or Corpus Enchanter</td>
  <td>Can put two enchantments on the same item.</td>
</tr>
</table>
<table class="wikitable">
<tr><th>Perk (Ranks)</th><th>Requirements</th><th>Description</th></tr>
<tr>
  <td>Augmented Flames (2)</td>
  <td>Destruction 30/60<br/>Novice Destruction</td>
  <td>Fire enchantments do more damage.</td>
</tr>
<tr>
  <td>Master of the Mind</td>
  <td>Illusion 90<br/>Rage<br/>Quiet Casting</td>
  <td>Illusion enchantments work on undead, daedra and automatons.</td>
</tr>
</table>
"""

EFFECTS_TABLE_HTML = """
<table class="wikitable">
<tr><th>Enchantment</th><th>School</th></tr>
<tr><td>Absorb Health</td><td>Destruction</td></tr>
<tr><td>Banish</td><td>Conjuration</td></tr>
<tr><td>Chaos Damage DR</td><td>Destruction</td></tr>
</table>
"""

APPAREL_TABLE_HTML = """
<table class="wikitable">
<tr><th>Enchantment</th><th>Head</th><th>Chest</th><th>Hands</th><th>Feet</th><th>Shield</th><th>Amulet</th><th>Ring</th></tr>
<tr><td>Fortify Alchemy</td><td>Yes</td><td></td><td>Yes</td><td></td><td></td><td>Yes</td><td>Yes</td></tr>
<tr><td>Fortify Archery</td><td>Yes</td><td>Yes</td><td>Yes</td><td></td><td>Yes</td><td></td><td>Yes</td></tr>
<tr><td>Muffle†</td><td></td><td></td><td></td><td>Yes</td><td></td><td></td><td></td></tr>
</table>
"""


def make_mock_session(html):
    mock = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {'parse': {'text': {'*': html}}}
    mock.get.return_value = resp
    return mock


def make_soup(html):
    return BeautifulSoup(html, 'html.parser')


# ---------------------------------------------------------------------------
# fetch_section
# ---------------------------------------------------------------------------

def test_fetch_section_returns_soup():
    session = make_mock_session(PERKS_TABLE_HTML)
    soup = fetch_section('Enchanting_(Skyrim)', 10, session=session)
    assert soup.find('table', class_='wikitable') is not None

def test_fetch_section_http_error_raises():
    mock = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError('404')
    mock.get.return_value = resp
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_section('Enchanting_(Skyrim)', 10, session=mock)

def test_fetch_section_bad_response_raises():
    mock = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {'error': {'code': 'missingtitle'}}
    mock.get.return_value = resp
    with pytest.raises(KeyError):
        fetch_section('Enchanting_(Skyrim)', 10, session=mock)


# ---------------------------------------------------------------------------
# parse_req_cell
# ---------------------------------------------------------------------------

def test_parse_req_cell_skill_only():
    td = make_soup('<td>Enchanting 0/20/40/60/80</td>').find('td')
    levels, prereqs = parse_req_cell(td)
    assert levels == [0, 20, 40, 60, 80]
    assert prereqs == []

def test_parse_req_cell_with_prereq():
    td = make_soup('<td>Enchanting 20<br/>Enchanter</td>').find('td')
    levels, prereqs = parse_req_cell(td)
    assert levels == [20]
    assert prereqs == ['Enchanter']

def test_parse_req_cell_two_prereqs():
    td = make_soup('<td>Illusion 90<br/>Rage<br/>Quiet Casting</td>').find('td')
    levels, prereqs = parse_req_cell(td)
    assert levels == [90]
    assert 'Rage' in prereqs
    assert 'Quiet Casting' in prereqs

def test_parse_req_cell_or_prereqs():
    td = make_soup('<td>Enchanting 100<br/>Storm Enchanter or Corpus Enchanter</td>').find('td')
    levels, prereqs = parse_req_cell(td)
    assert levels == [100]
    assert 'Storm Enchanter' in prereqs
    assert 'Corpus Enchanter' in prereqs

def test_parse_req_cell_multi_rank():
    td = make_soup('<td>Destruction 30/60<br/>Novice Destruction</td>').find('td')
    levels, prereqs = parse_req_cell(td)
    assert levels == [30, 60]
    assert prereqs == ['Novice Destruction']


# ---------------------------------------------------------------------------
# parse_perks_tables
# ---------------------------------------------------------------------------

def test_parse_perks_tables_finds_all_tables():
    soup = make_soup(PERKS_TABLE_HTML)
    raw = parse_perks_tables(soup)
    names = [r[0] for r in raw]
    assert 'Enchanter (5)' in names
    assert 'Augmented Flames (2)' in names
    assert 'Master of the Mind' in names

def test_parse_perks_tables_skips_non_perk_tables():
    html = PERKS_TABLE_HTML + EFFECTS_TABLE_HTML
    soup = make_soup(html)
    raw = parse_perks_tables(soup)
    names = [r[0] for r in raw]
    assert 'Absorb Health' not in names


# ---------------------------------------------------------------------------
# expand_perks
# ---------------------------------------------------------------------------

def test_expand_perks_enchanter_produces_five_rows():
    soup = make_soup(PERKS_TABLE_HTML)
    raw = parse_perks_tables(soup)
    perks = expand_perks(raw)
    names = [p['name'] for p in perks]
    assert all(f'Enchanter ({i}/5)' in names for i in range(1, 6))

def test_expand_perks_enchanter_skill_levels():
    soup = make_soup(PERKS_TABLE_HTML)
    raw = parse_perks_tables(soup)
    perks = expand_perks(raw)
    enchanters = [p for p in perks if p['name'].startswith('Enchanter (')]
    assert [p['skill_level'] for p in enchanters] == [0, 20, 40, 60, 80]

def test_expand_perks_enchanter_prereq_chain():
    raw = [('Enchanter (5)', make_soup('<td>Enchanting 0/20/40/60/80</td>').find('td'),
            'New enchantments are stronger.')]
    perks = expand_perks(raw)
    assert perks[0]['prerequisite'] == 'None'
    assert perks[1]['prerequisite'] == 'Enchanter (1/5)'
    assert perks[4]['prerequisite'] == 'Enchanter (4/5)'

def test_expand_perks_enchanter_descriptions_have_magnitudes():
    raw = [('Enchanter (5)', make_soup('<td>Enchanting 0/20/40/60/80</td>').find('td'), 'X')]
    perks = expand_perks(raw)
    assert '20%' in perks[0]['description']
    assert '100%' in perks[4]['description']

def test_expand_perks_augmented_flames_two_rows():
    raw = [('Augmented Flames (2)',
            make_soup('<td>Destruction 30/60<br/>Novice Destruction</td>').find('td'),
            'X')]
    perks = expand_perks(raw)
    names = [p['name'] for p in perks]
    assert names == ['Augmented Flames (1/2)', 'Augmented Flames (2/2)']

def test_expand_perks_augmented_frost_magnitudes():
    raw = [('Augmented Frost (2)',
            make_soup('<td>Destruction 30/60<br/>Novice Destruction</td>').find('td'),
            'X')]
    perks = expand_perks(raw)
    assert '25%' in perks[0]['description']
    assert '50%' in perks[1]['description']

def test_expand_perks_augmented_skill_levels():
    raw = [('Augmented Shock (2)',
            make_soup('<td>Destruction 30/60<br/>Novice Destruction</td>').find('td'),
            'X')]
    perks = expand_perks(raw)
    assert perks[0]['skill_level'] == 30
    assert perks[1]['skill_level'] == 60

def test_expand_perks_soul_squeezer_remaps_enchanter():
    raw = [('Soul Squeezer',
            make_soup('<td>Enchanting 20<br/>Enchanter</td>').find('td'),
            'Soul gems provide extra magicka.')]
    perks = expand_perks(raw)
    assert len(perks) == 1
    assert perks[0]['prerequisite'] == 'Enchanter (1/5)'

def test_expand_perks_extra_effect_or_prereqs():
    raw = [('Extra Effect',
            make_soup('<td>Enchanting 100<br/>Storm Enchanter or Corpus Enchanter</td>').find('td'),
            'Can put two enchantments.')]
    perks = expand_perks(raw)
    assert 'Storm Enchanter' in perks[0]['prerequisite']
    assert 'Corpus Enchanter' in perks[0]['prerequisite']

def test_expand_perks_master_of_mind_two_prereqs():
    raw = [('Master of the Mind',
            make_soup('<td>Illusion 90<br/>Rage<br/>Quiet Casting</td>').find('td'),
            'Illusion enchantments work on undead.')]
    perks = expand_perks(raw)
    assert 'Rage' in perks[0]['prerequisite']
    assert 'Quiet Casting' in perks[0]['prerequisite']

def test_expand_perks_full_table():
    soup = make_soup(PERKS_TABLE_HTML)
    raw = parse_perks_tables(soup)
    perks = expand_perks(raw)
    names = [p['name'] for p in perks]
    assert 'Enchanter (1/5)' in names
    assert 'Enchanter (5/5)' in names
    assert 'Augmented Flames (1/2)' in names
    assert 'Augmented Flames (2/2)' in names
    assert 'Soul Squeezer' in names
    assert 'Extra Effect' in names
    assert 'Master of the Mind' in names


# ---------------------------------------------------------------------------
# strip_dlc_marker
# ---------------------------------------------------------------------------

def test_strip_dlc_marker_removes_dr():
    assert strip_dlc_marker('Chaos Damage DR') == 'Chaos Damage'

def test_strip_dlc_marker_removes_dg():
    assert strip_dlc_marker('Vampire DR DG') == 'Vampire'

def test_strip_dlc_marker_no_marker_unchanged():
    assert strip_dlc_marker('Absorb Health') == 'Absorb Health'

def test_strip_dlc_marker_all_known_codes():
    for code in ['DG', 'DR', 'DB', 'HF', 'CC']:
        assert strip_dlc_marker(f'Spell {code}') == 'Spell'


# ---------------------------------------------------------------------------
# parse_effects_table
# ---------------------------------------------------------------------------

def test_parse_effects_table_correct_count():
    soup = make_soup(EFFECTS_TABLE_HTML)
    rows = parse_effects_table(soup)
    assert len(rows) == 3

def test_parse_effects_table_fields():
    soup = make_soup(EFFECTS_TABLE_HTML)
    rows = parse_effects_table(soup)
    assert rows[0] == {'name': 'Absorb Health', 'school': 'Destruction'}

def test_parse_effects_table_strips_dlc():
    soup = make_soup(EFFECTS_TABLE_HTML)
    rows = parse_effects_table(soup)
    names = [r['name'] for r in rows]
    assert 'Chaos Damage' in names
    assert 'Chaos Damage DR' not in names

def test_parse_effects_table_no_table_returns_empty():
    soup = make_soup('<html><body></body></html>')
    assert parse_effects_table(soup) == []


# ---------------------------------------------------------------------------
# parse_apparel_table
# ---------------------------------------------------------------------------

def test_parse_apparel_table_correct_count():
    soup = make_soup(APPAREL_TABLE_HTML)
    rows = parse_apparel_table(soup)
    assert len(rows) == 3

def test_parse_apparel_table_fortify_alchemy_slots():
    soup = make_soup(APPAREL_TABLE_HTML)
    rows = parse_apparel_table(soup)
    row = next(r for r in rows if r['enchantment'] == 'Fortify Alchemy')
    assert row['head'] is True
    assert row['chest'] is False
    assert row['hands'] is True
    assert row['amulet'] is True
    assert row['ring'] is True

def test_parse_apparel_table_strips_dagger():
    soup = make_soup(APPAREL_TABLE_HTML)
    rows = parse_apparel_table(soup)
    names = [r['enchantment'] for r in rows]
    assert 'Muffle' in names
    assert 'Muffle†' not in names

def test_parse_apparel_table_boolean_types():
    soup = make_soup(APPAREL_TABLE_HTML)
    rows = parse_apparel_table(soup)
    row = rows[0]
    for col in ['head', 'chest', 'hands', 'feet', 'shield', 'amulet', 'ring']:
        assert isinstance(row[col], bool)

def test_parse_apparel_table_no_table_returns_empty():
    soup = make_soup('<html><body></body></html>')
    assert parse_apparel_table(soup) == []


# ---------------------------------------------------------------------------
# write_raw_file (enchanting)
# ---------------------------------------------------------------------------

def test_write_raw_file_perks(tmp_path):
    records = [
        {'name': 'Enchanter (1/5)', 'skill_level': 0, 'prerequisite': 'None',
         'description': 'New enchantments are 20% stronger.'},
    ]
    outfile = str(tmp_path / 'perks.txt')
    write_raw_file(records, outfile, ['name', 'skill_level', 'prerequisite', 'description'])
    lines = Path(outfile).read_text().splitlines()
    assert lines[0] == 'Enchanter (1/5)|0|None|New enchantments are 20% stronger.'

def test_write_raw_file_apparel(tmp_path):
    records = [{'enchantment': 'Fortify Alchemy', 'head': True, 'chest': False,
                'hands': True, 'feet': False, 'shield': False, 'amulet': True, 'ring': True}]
    outfile = str(tmp_path / 'apparel.txt')
    write_raw_file(records, outfile,
                   ['enchantment', 'head', 'chest', 'hands', 'feet', 'shield', 'amulet', 'ring'])
    lines = Path(outfile).read_text().splitlines()
    assert lines[0] == 'Fortify Alchemy|True|False|True|False|False|True|True'
