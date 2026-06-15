"""Tests for Morrowind/alchemy/ingredients_parse/morrowind_scrape_wiki.py"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Morrowind/alchemy/ingredients_parse/morrowind_scrape_wiki.py",
    "mw_scrape",
)
fetch_parsed_html = _mod.fetch_parsed_html
cell_text = _mod.cell_text
extract_rows = _mod.extract_rows
fields_from_row = _mod.fields_from_row
format_entry = _mod.format_entry
write_raw_file = _mod.write_raw_file

from bs4 import BeautifulSoup

# Minimal HTML that matches the Morrowind wikitable structure
SAMPLE_HTML = """
<table class="wikitable sortable">
  <tr><th>Ingredient</th><th></th><th></th><th>Effect 1</th><th>Effect 2</th><th>Effect 3</th><th>Effect 4</th><th>ID</th></tr>
  <tr>
    <th><small><a href="/wiki/Alit_Hide">Alit Hide</a></small></th>
    <td>1.0</td><td>5</td>
    <td>Drain Intelligence</td>
    <td>Resist Poison</td>
    <td>Telekinesis</td>
    <td>Detect Animal</td>
    <td>ingred_alit_hide_01</td>
  </tr>
  <tr>
    <th><small><a href="/wiki/Ampoule_Pod">Ampoule Pod</a></small></th>
    <td>0.1</td><td>2</td>
    <td>Water Walking</td>
    <td>Paralyze</td>
    <td>Detect Animal</td>
    <td>Drain Willpower</td>
    <td>ingred_bc_ampoule_pod</td>
  </tr>
</table>
"""

SAMPLE_JSON_RESPONSE = {
    'parse': {'text': {'*': SAMPLE_HTML}}
}


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
    soup = fetch_parsed_html('Ingredients_(Morrowind)', session=session)
    assert soup is not None
    assert soup.find('table', class_='wikitable') is not None
    session.get.assert_called_once()

def test_fetch_parsed_html_passes_correct_params():
    session = make_mock_session(SAMPLE_JSON_RESPONSE)
    fetch_parsed_html('Ingredients_(Morrowind)', session=session)
    call_kwargs = session.get.call_args
    params = call_kwargs[1]['params'] if 'params' in call_kwargs[1] else call_kwargs[0][1]
    assert params['action'] == 'parse'
    assert params['page'] == 'Ingredients_(Morrowind)'

def test_fetch_parsed_html_non_200_raises():
    session = make_mock_session(None, raise_error=True)
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_parsed_html('Ingredients_(Morrowind)', session=session)

def test_fetch_parsed_html_connection_error_raises():
    session = MagicMock()
    session.get.side_effect = requests.exceptions.ConnectionError("Connection refused")
    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_parsed_html('Ingredients_(Morrowind)', session=session)

def test_fetch_parsed_html_missing_parse_key_raises():
    # API returns JSON but without the expected ['parse']['text']['*'] structure
    session = make_mock_session({'error': {'code': 'missingtitle', 'info': 'page not found'}})
    with pytest.raises(KeyError):
        fetch_parsed_html('Nonexistent_Page', session=session)


# ---------------------------------------------------------------------------
# cell_text
# ---------------------------------------------------------------------------

def test_cell_text_plain_text():
    tag = BeautifulSoup('<td>Alit Hide</td>', 'html.parser').find('td')
    assert cell_text(tag) == 'Alit Hide'

def test_cell_text_with_link_no_disambiguation():
    # href matches display → no pipe trick added
    tag = BeautifulSoup('<th><small><a href="/wiki/Alit_Hide">Alit Hide</a></small></th>', 'html.parser').find('th')
    assert cell_text(tag) == 'Alit Hide'

def test_cell_text_with_link_preserves_disambiguation():
    # Page title differs from display → reconstruct wiki link format
    tag = BeautifulSoup('<td><a href="/wiki/Resist_Poison_(Morrowind)">Resist Poison</a></td>', 'html.parser').find('td')
    assert cell_text(tag) == 'Resist Poison (Morrowind)|Resist Poison'

def test_cell_text_multiword_effect_space_joined():
    # Two-word effect rendered as two separate links → space-joined
    html = '<td><a href="/wiki/Drain_(Morrowind)">Drain</a> <a href="/wiki/Fatigue">Fatigue</a></td>'
    tag = BeautifulSoup(html, 'html.parser').find('td')
    assert cell_text(tag) == 'Drain (Morrowind)|Drain Fatigue'

def test_cell_text_dlc_marker_filtered():
    # DLC icon link (e.g. {{SI}}) must not appear in the output
    html = '<td><a href="/wiki/Bear_Pelt_(Bloodmoon)">Bear Pelt</a><a href="/wiki/Bloodmoon">SI</a></td>'
    tag = BeautifulSoup(html, 'html.parser').find('td')
    assert cell_text(tag) == 'Bear Pelt (Bloodmoon)|Bear Pelt'

def test_cell_text_empty_cell_returns_empty():
    tag = BeautifulSoup('<td></td>', 'html.parser').find('td')
    assert cell_text(tag) == ''


# ---------------------------------------------------------------------------
# extract_rows
# ---------------------------------------------------------------------------

def test_extract_rows_returns_data_rows():
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    rows = extract_rows(soup)
    assert len(rows) == 2

def test_extract_rows_first_row_content():
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    rows = extract_rows(soup)
    assert rows[0][0] == 'Alit Hide'
    assert rows[0][1] == '1.0'
    assert rows[0][2] == '5'
    assert rows[0][7] == 'ingred_alit_hide_01'

def test_extract_rows_no_table_returns_empty():
    soup = BeautifulSoup('<html><body><p>No table here</p></body></html>', 'html.parser')
    assert extract_rows(soup) == []

def test_extract_rows_all_tables_combines_rows():
    multi_html = SAMPLE_HTML + """
    <table class="wikitable sortable">
      <tr><th>Ingredient</th><th></th><th></th><th>E1</th><th>E2</th><th>E3</th><th>E4</th><th>ID</th></tr>
      <tr>
        <th><a href="...">Ash Salts</a></th>
        <td>0.1</td><td>25</td>
        <td>Drain Agility</td><td>Resist Magicka</td><td>Cure Blight</td><td>Resist Magicka</td>
        <td>ingred_ash_salts_01</td>
      </tr>
    </table>
    """
    soup = BeautifulSoup(multi_html, 'html.parser')
    rows = extract_rows(soup, all_tables=True)
    assert len(rows) == 3  # 2 from first table + 1 from second


# ---------------------------------------------------------------------------
# fields_from_row
# ---------------------------------------------------------------------------

def test_fields_from_row_valid_returns_list():
    cells = ['Alit Hide', '1.0', '5', 'Drain Intelligence', 'Resist Poison', 'Telekinesis', 'Detect Animal', 'ingred_alit_hide_01']
    result = fields_from_row(cells)
    assert result == cells

def test_fields_from_row_empty_effect_becomes_dash():
    # Empty effect cells must become '-' so dash_to_null() in the parser fires
    cells = ['Bread', '0.2', '1', 'Restore Fatigue', '', '', '', 'ingred_bread_01']
    result = fields_from_row(cells)
    assert result[4] == '-'
    assert result[5] == '-'
    assert result[6] == '-'
    assert result[3] == 'Restore Fatigue'  # non-empty effects unchanged

def test_fields_from_row_wrong_count_returns_none():
    assert fields_from_row(['Name', 'Weight', 'Value']) is None

def test_fields_from_row_extra_columns_returns_none():
    assert fields_from_row(['a'] * 9) is None


# ---------------------------------------------------------------------------
# format_entry
# ---------------------------------------------------------------------------

def test_format_entry_produces_9_lines():
    fields = ['Alit Hide', '1.0', '5', 'Drain Intelligence', 'Resist Poison', 'Telekinesis', 'Detect Animal', 'ingred_alit_hide_01']
    result = format_entry(fields)
    lines = result.rstrip('\n').split('\n')
    assert len(lines) == 9

def test_format_entry_first_line_is_separator():
    fields = ['Alit Hide', '1.0', '5', 'e', 'e', 'e', 'e', 'id']
    result = format_entry(fields)
    assert result.split('\n')[0] == '|'

def test_format_entry_fields_have_pipe_prefix():
    fields = ['Alit Hide', '1.0', '5', 'e1', 'e2', 'e3', 'e4', 'id']
    result = format_entry(fields)
    for line in result.rstrip('\n').split('\n')[1:]:
        assert line.startswith('|')


# ---------------------------------------------------------------------------
# write_raw_file
# ---------------------------------------------------------------------------

def test_write_raw_file_creates_correct_content(tmp_path):
    outfile = str(tmp_path / 'out.txt')
    entries = [format_entry(['Alit Hide', '1.0', '5', 'e', 'e', 'e', 'e', 'id'])]
    write_raw_file(entries, outfile)
    content = Path(outfile).read_text()
    assert '|Alit Hide' in content
    assert content.startswith('|')

def test_write_raw_file_two_entries_parseable_by_parser(tmp_path):
    """Written entries should be parseable by the existing morrowind parser."""
    outfile = str(tmp_path / 'out.txt')
    entries = [
        format_entry(['Alit Hide', '1.0', '5', 'Drain Intelligence', 'Resist Poison', 'Telekinesis', 'Detect Animal', 'ingred_alit_hide_01']),
        format_entry(['Ampoule Pod', '0.1', '2', 'Water Walking', 'Paralyze', 'Detect Animal', 'Drain Willpower', 'ingred_bc_ampoule_pod']),
    ]
    write_raw_file(entries, outfile)
    # Verify the parser can read the file
    parse_mod = load_module(
        'Morrowind/alchemy/ingredients_json/morrowind_parse_wiki_to_json.py',
        'mw_alchemy_parse_check',
    )
    ing, eff = parse_mod.parse(outfile)
    assert len(ing) == 2
    assert ing[0]['name'] == 'Alit Hide'
    assert ing[1]['name'] == 'Ampoule Pod'

def test_write_raw_file_bad_path_raises():
    with pytest.raises(OSError):
        write_raw_file([], '/nonexistent_dir_xyz/out.txt')
