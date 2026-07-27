"""Tests for TES/Skyrim/enchanting/souls_parse/skyrim_scrape_souls.py"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    'TES/Skyrim/enchanting/souls_parse/skyrim_scrape_souls.py',
    'sk_souls_scrape',
)
fetch_page             = _mod.fetch_page
parse_types_table      = _mod.parse_types_table
extract_creature_name  = _mod.extract_creature_name
parse_souls_tables     = _mod.parse_souls_tables
parse_black_souls_list = _mod.parse_black_souls_list
extract_race_names     = _mod.extract_race_names
write_raw_file         = _mod.write_raw_file


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

TYPES_TABLE_HTML = """
<table class="wikitable">
<tr><th>Name</th><th>Weight</th><th>Value</th><th>Capacity</th><th>Trappable Souls</th></tr>
<tr><td>Petty Soul Gem</td><td>0.1</td><td>10</td><td>250</td><td>Can hold creature souls below level 4.</td></tr>
<tr><td>Lesser Soul Gem</td><td>0.2</td><td>25</td><td>500</td><td>Can hold creature souls below level 16.</td></tr>
<tr><td>Grand Soul Gem</td><td>0.5</td><td>200</td><td>3000</td><td>Can hold any soul, excluding those of humanoids.</td></tr>
<tr><td>Black Soul Gem</td><td>1</td><td>500</td><td>3000</td><td>Can hold any soul, including those of humanoids.</td></tr>
<tr><td>Soul Gem Fragment</td><td>0.1</td><td>5</td><td>0</td><td>Cannot hold souls.</td></tr>
</table>
"""

SOULS_TABLE_HTML = """
<table class="wikitable">
<tr><th><h3><span class="mw-headline" id="Petty_Souls">Petty Souls</span></h3></th></tr>
<tr><td><a href="/wiki/Chicken">Chicken</a></td></tr>
<tr><td><a href="/wiki/Mudcrab">Mudcrab</a></td></tr>
<tr><th><h3><span class="mw-headline" id="Lesser_Souls">Lesser Souls</span></h3></th></tr>
<tr><td><a href="/wiki/Wolf">Wolf</a> <sup><a href="/wiki/Dragonborn">DB</a></sup></td></tr>
<tr><td><a href="/wiki/Skeleton">Skeleton</a></td></tr>
<tr><th><h3><span class="mw-headline" id="Grand_Souls">Grand Souls</span></h3></th></tr>
<tr><td><a href="/wiki/Mammoth">Mammoth</a></td></tr>
</table>
"""

BLACK_SOULS_HTML = """
<h2><span class="mw-headline" id="Black_Soul_Gems">Black Soul Gems</span></h2>
<p>Some text.</p>
<ul>
<li>Any <a href="/wiki/Characters_(Skyrim)">character</a> from any of the ten playable races.</li>
<li><a href="/wiki/Dremora">Dremora</a></li>
<li><a href="/wiki/Vampire">Vampire</a></li>
</ul>
"""

RACES_TABLE_HTML = """
<table class="wikitable">
<tr><th>Image</th><th>Race</th><th>Effects</th><th>Power</th></tr>
<tr><td></td><td><a href="/wiki/Argonian_(Skyrim)">Argonian</a></td><td>Waterbreathing</td><td>Histskin</td></tr>
<tr><td></td><td><a href="/wiki/Khajiit_(Skyrim)">Khajiit</a></td><td>Night Eye</td><td>Claws</td></tr>
<tr><td></td><td><a href="/wiki/Nord_(Skyrim)">Nord</a></td><td>Frost Resistance</td><td>Battle Cry</td></tr>
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
# fetch_page
# ---------------------------------------------------------------------------

def test_fetch_page_returns_soup():
    session = make_mock_session(TYPES_TABLE_HTML)
    soup = fetch_page('Soul_Gem_(Skyrim)', session=session)
    assert soup.find('table', class_='wikitable') is not None

def test_fetch_page_http_error_raises():
    mock = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError('404')
    mock.get.return_value = resp
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_page('Soul_Gem_(Skyrim)', session=mock)

def test_fetch_page_bad_response_structure_raises():
    mock = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {'error': {'code': 'missingtitle'}}
    mock.get.return_value = resp
    with pytest.raises(KeyError):
        fetch_page('Soul_Gem_(Skyrim)', session=mock)


# ---------------------------------------------------------------------------
# parse_types_table
# ---------------------------------------------------------------------------

def test_parse_types_table_correct_count():
    soup = make_soup(TYPES_TABLE_HTML)
    rows = parse_types_table(soup)
    assert len(rows) == 5

def test_parse_types_table_first_row_fields():
    soup = make_soup(TYPES_TABLE_HTML)
    rows = parse_types_table(soup)
    assert rows[0]['name'] == 'Petty Soul Gem'
    assert rows[0]['weight'] == 0.1
    assert rows[0]['value'] == 10
    assert rows[0]['capacity'] == 250
    assert 'below level 4' in rows[0]['trappable_souls']

def test_parse_types_table_weight_is_float():
    soup = make_soup(TYPES_TABLE_HTML)
    rows = parse_types_table(soup)
    assert isinstance(rows[0]['weight'], float)

def test_parse_types_table_integer_weight():
    soup = make_soup(TYPES_TABLE_HTML)
    rows = parse_types_table(soup)
    black = next(r for r in rows if r['name'] == 'Black Soul Gem')
    assert black['weight'] == 1.0

def test_parse_types_table_zero_capacity():
    soup = make_soup(TYPES_TABLE_HTML)
    rows = parse_types_table(soup)
    frag = next(r for r in rows if r['name'] == 'Soul Gem Fragment')
    assert frag['capacity'] == 0

def test_parse_types_table_no_table_raises():
    soup = make_soup('<html><body></body></html>')
    with pytest.raises(ValueError, match='types wikitable'):
        parse_types_table(soup)


# ---------------------------------------------------------------------------
# extract_creature_name
# ---------------------------------------------------------------------------

def test_extract_creature_name_plain():
    td = make_soup('<td><a href="/wiki/Chicken">Chicken</a></td>').find('td')
    assert extract_creature_name(td) == 'Chicken'

def test_extract_creature_name_ignores_dlc_sup():
    html = '<td><a href="/wiki/Wolf">Wolf</a> <sup><a href="/wiki/DB">DB</a></sup></td>'
    td = make_soup(html).find('td')
    assert extract_creature_name(td) == 'Wolf'

def test_extract_creature_name_no_link():
    td = make_soup('<td>Gargoyle</td>').find('td')
    assert extract_creature_name(td) == 'Gargoyle'


# ---------------------------------------------------------------------------
# parse_souls_tables
# ---------------------------------------------------------------------------

def test_parse_souls_tables_returns_rows():
    soup = make_soup(SOULS_TABLE_HTML)
    rows = parse_souls_tables(soup)
    assert len(rows) > 0

def test_parse_souls_tables_correct_sizes():
    soup = make_soup(SOULS_TABLE_HTML)
    rows = parse_souls_tables(soup)
    sizes = {r['creature']: r['soul_size'] for r in rows}
    assert sizes['Chicken'] == 'petty'
    assert sizes['Mudcrab'] == 'petty'
    assert sizes['Skeleton'] == 'lesser'
    assert sizes['Mammoth'] == 'grand'

def test_parse_souls_tables_dlc_creature_name():
    soup = make_soup(SOULS_TABLE_HTML)
    rows = parse_souls_tables(soup)
    wolf = next((r for r in rows if r['creature'] == 'Wolf'), None)
    assert wolf is not None
    assert wolf['soul_size'] == 'lesser'

def test_parse_souls_tables_no_table_raises():
    soup = make_soup('<html><body><p>Nothing here</p></body></html>')
    with pytest.raises(ValueError, match='souls wikitable'):
        parse_souls_tables(soup)


# ---------------------------------------------------------------------------
# parse_black_souls_list
# ---------------------------------------------------------------------------

def test_parse_black_souls_list_detects_playable_races():
    soup = make_soup(BLACK_SOULS_HTML)
    _, has_races = parse_black_souls_list(soup)
    assert has_races is True

def test_parse_black_souls_list_other_creatures():
    soup = make_soup(BLACK_SOULS_HTML)
    others, _ = parse_black_souls_list(soup)
    assert 'Dremora' in others
    assert 'Vampire' in others

def test_parse_black_souls_list_races_item_not_in_others():
    soup = make_soup(BLACK_SOULS_HTML)
    others, _ = parse_black_souls_list(soup)
    assert not any('playable' in c.lower() for c in others)

def test_parse_black_souls_list_no_section_returns_empty():
    soup = make_soup('<html><body><p>Nothing</p></body></html>')
    others, has_races = parse_black_souls_list(soup)
    assert others == []
    assert has_races is False


# ---------------------------------------------------------------------------
# extract_race_names
# ---------------------------------------------------------------------------

def test_extract_race_names_correct_count():
    soup = make_soup(RACES_TABLE_HTML)
    races = extract_race_names(soup)
    assert len(races) == 3

def test_extract_race_names_correct_values():
    soup = make_soup(RACES_TABLE_HTML)
    races = extract_race_names(soup)
    assert 'Argonian' in races
    assert 'Khajiit' in races
    assert 'Nord' in races

def test_extract_race_names_no_table_raises():
    soup = make_soup('<html><body></body></html>')
    with pytest.raises(ValueError):
        extract_race_names(soup)


# ---------------------------------------------------------------------------
# write_raw_file
# ---------------------------------------------------------------------------

def test_write_raw_file_gem_types(tmp_path):
    records = [
        {'name': 'Petty Soul Gem', 'weight': 0.1, 'value': 10,
         'capacity': 250, 'trappable_souls': 'Can hold creature souls below level 4.'},
    ]
    outfile = str(tmp_path / 'types.txt')
    write_raw_file(records, outfile, ['name', 'weight', 'value', 'capacity', 'trappable_souls'])
    lines = Path(outfile).read_text().splitlines()
    assert len(lines) == 1
    assert lines[0] == 'Petty Soul Gem|0.1|10|250|Can hold creature souls below level 4.'

def test_write_raw_file_creature_souls(tmp_path):
    records = [
        {'creature': 'Chicken', 'soul_size': 'petty'},
        {'creature': 'Nord', 'soul_size': 'black'},
    ]
    outfile = str(tmp_path / 'souls.txt')
    write_raw_file(records, outfile, ['creature', 'soul_size'])
    lines = Path(outfile).read_text().splitlines()
    assert lines[0] == 'Chicken|petty'
    assert lines[1] == 'Nord|black'

def test_write_raw_file_bad_path_raises():
    with pytest.raises(OSError):
        write_raw_file([], '/nonexistent_dir_xyz/out.txt', ['a'])
