"""Tests for Oblivion/alchemy/ingredients_parse/oblivion_scrape_wiki.py"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "TES/Oblivion/alchemy/ingredients_parse/oblivion_scrape_wiki.py",
    "ob_scrape",
)
fetch_parsed_html = _mod.fetch_parsed_html
cell_text = _mod.cell_text
extract_rows = _mod.extract_rows
fields_from_row = _mod.fields_from_row
format_entry = _mod.format_entry
write_raw_file = _mod.write_raw_file

# Minimal HTML matching the Oblivion wikitable structure
SAMPLE_HTML = """
<table class="wikitable sortable">
  <tr>
    <th>Ingredient</th><th>Weight</th><th>Base Value</th>
    <th>Sources</th><th>Effects</th><th>Form ID</th>
  </tr>
  <tr>
    <td><a href="...">Alkanet Flower</a></td>
    <td>0.1</td><td>1</td>
    <td>Alkanet</td>
    <td>Restore Intelligence<br/>Resist Poison<br/>Light<br/>Damage Fatigue</td>
    <td>0003365C</td>
  </tr>
  <tr>
    <td><a href="...">Boar Meat</a></td>
    <td>2.0</td><td>1</td>
    <td>Boar</td>
    <td>Restore Fatigue<br/>Fortify Strength</td>
    <td>0003AB19</td>
  </tr>
</table>
"""

SAMPLE_JSON_RESPONSE = {'parse': {'text': {'*': SAMPLE_HTML}}}


def make_mock_session(json_data, raise_error=False):
    mock_session = MagicMock()
    mock_response = MagicMock()
    if raise_error:
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden")
    else:
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = json_data
    mock_session.get.return_value = mock_response
    return mock_session


# ---------------------------------------------------------------------------
# fetch_parsed_html
# ---------------------------------------------------------------------------

def test_fetch_parsed_html_returns_soup():
    session = make_mock_session(SAMPLE_JSON_RESPONSE)
    soup = fetch_parsed_html('Ingredients_(Oblivion)', session=session)
    assert soup.find('table', class_='wikitable') is not None

def test_fetch_parsed_html_non_200_raises():
    session = make_mock_session(None, raise_error=True)
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_parsed_html('Ingredients_(Oblivion)', session=session)

def test_fetch_parsed_html_connection_error_raises():
    session = MagicMock()
    session.get.side_effect = requests.exceptions.ConnectionError("Connection refused")
    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_parsed_html('Ingredients_(Oblivion)', session=session)

def test_fetch_parsed_html_missing_parse_key_raises():
    # API returns JSON but without the expected ['parse']['text']['*'] structure
    session = make_mock_session({'error': {'code': 'missingtitle', 'info': 'page not found'}})
    with pytest.raises(KeyError):
        fetch_parsed_html('Nonexistent_Page', session=session)


# ---------------------------------------------------------------------------
# cell_text — Oblivion-specific: <br>-separated effects comma-joined; DLC markers filtered
# ---------------------------------------------------------------------------

def test_cell_text_br_separated_joins_with_comma():
    tag = BeautifulSoup(
        '<td>Restore Intelligence<br/>Resist Poison<br/>Light<br/>Damage Fatigue</td>',
        'html.parser'
    ).find('td')
    assert cell_text(tag) == 'Restore Intelligence,Resist Poison,Light,Damage Fatigue'

def test_cell_text_single_value():
    tag = BeautifulSoup('<td>Alkanet</td>', 'html.parser').find('td')
    assert cell_text(tag) == 'Alkanet'

def test_cell_text_linked_ingredient_name_no_disambiguation():
    tag = BeautifulSoup('<td><a href="/wiki/Alkanet_Flower">Alkanet Flower</a></td>', 'html.parser').find('td')
    assert cell_text(tag) == 'Alkanet Flower'

def test_cell_text_linked_ingredient_name_with_disambiguation():
    tag = BeautifulSoup('<td><a href="/wiki/Alkanet_Flower_(Oblivion)">Alkanet Flower</a></td>', 'html.parser').find('td')
    assert cell_text(tag) == 'Alkanet Flower (Oblivion)|Alkanet Flower'

def test_cell_text_dlc_marker_filtered_from_name():
    html = '<td><a href="/wiki/Alocasia_Fruit_(Oblivion)">Alocasia Fruit</a><a href="/wiki/Shivering_Isles">SI</a></td>'
    tag = BeautifulSoup(html, 'html.parser').find('td')
    assert cell_text(tag) == 'Alocasia Fruit (Oblivion)|Alocasia Fruit'


# ---------------------------------------------------------------------------
# extract_rows
# ---------------------------------------------------------------------------

def test_extract_rows_returns_data_rows():
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    rows = extract_rows(soup)
    assert len(rows) == 2

def test_extract_rows_effects_comma_separated():
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    rows = extract_rows(soup)
    effects = rows[0][4]
    assert ',' in effects
    assert 'Restore Intelligence' in effects
    assert 'Damage Fatigue' in effects

def test_extract_rows_no_table_returns_empty():
    soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
    assert extract_rows(soup) == []


# ---------------------------------------------------------------------------
# fields_from_row
# ---------------------------------------------------------------------------

def test_fields_from_row_valid_returns_list():
    cells = ['Alkanet Flower', '0.1', '1', 'Alkanet', 'Restore Intelligence,Resist Poison,Light,Damage Fatigue', '0003365C']
    assert fields_from_row(cells) == cells

def test_fields_from_row_wrong_count_returns_none():
    assert fields_from_row(['a', 'b', 'c']) is None

def test_fields_from_row_too_many_columns_returns_none():
    assert fields_from_row(['a'] * 7) is None


# ---------------------------------------------------------------------------
# format_entry
# ---------------------------------------------------------------------------

def test_format_entry_produces_7_lines():
    fields = ['Alkanet Flower', '0.1', '1', 'Alkanet', 'Restore Intelligence,Resist Poison,Light,Damage Fatigue', '0003365C']
    lines = format_entry(fields).rstrip('\n').split('\n')
    assert len(lines) == 7

def test_format_entry_effects_on_single_line():
    fields = ['Name', '0.1', '1', 'Source', 'Effect1,Effect2,Effect3,Effect4', 'ID']
    lines = format_entry(fields).rstrip('\n').split('\n')
    assert lines[5] == '|Effect1,Effect2,Effect3,Effect4'

def test_format_entry_separator_first():
    fields = ['Name', '0.1', '1', 'Source', 'Effect', 'ID']
    assert format_entry(fields).split('\n')[0] == '|'


# ---------------------------------------------------------------------------
# write_raw_file + round-trip with parser
# ---------------------------------------------------------------------------

def test_write_raw_file_creates_correct_content(tmp_path):
    outfile = str(tmp_path / 'out.txt')
    entries = [format_entry(['Alkanet Flower', '0.1', '1', 'Alkanet', 'Restore Intelligence,Resist Poison,Light,Damage Fatigue', '0003365C'])]
    write_raw_file(entries, outfile)
    content = Path(outfile).read_text()
    assert '|Alkanet Flower' in content

def test_write_raw_file_round_trip_with_parser(tmp_path):
    outfile = str(tmp_path / 'out.txt')
    entries = [
        format_entry(['Alkanet Flower', '0.1', '1', 'Alkanet', 'Restore Intelligence,Resist Poison,Light,Damage Fatigue', '0003365C']),
        format_entry(['Boar Meat', '2.0', '1', 'Boar', 'Restore Fatigue,Fortify Strength,None,None', '0003AB19']),
    ]
    write_raw_file(entries, outfile)
    parse_mod = load_module(
        'TES/Oblivion/alchemy/ingredients_json/oblivion_parse_wiki_to_json.py',
        'ob_alchemy_parse_check',
    )
    ing, eff = parse_mod.parse(outfile)
    assert len(ing) == 2
    assert ing[0]['name'] == 'Alkanet Flower'

def test_write_raw_file_bad_path_raises():
    with pytest.raises(OSError):
        write_raw_file([], '/nonexistent_dir_xyz/out.txt')
