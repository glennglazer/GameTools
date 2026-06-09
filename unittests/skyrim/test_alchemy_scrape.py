"""Tests for Skyrim/alchemy/ingredients_parse/skyrim_scrape_wiki.py"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Skyrim/alchemy/ingredients_parse/skyrim_scrape_wiki.py",
    "sk_scrape",
)
fetch_parsed_html = _mod.fetch_parsed_html
cell_text = _mod.cell_text
extract_rows = _mod.extract_rows
fields_from_row = _mod.fields_from_row
format_entry = _mod.format_entry
write_raw_file = _mod.write_raw_file

# Minimal HTML: two ingredient tables + one potion table (should be skipped)
INGREDIENT_TABLE = """
<table class="wikitable sortable">
  <tr><th>Ingredient</th><th>Primary Effect</th><th>Secondary Effect</th>
      <th>Tertiary Effect</th><th>Quaternary Effect</th>
      <th>Weight</th><th>Value</th><th>ID</th></tr>
  <tr>
    <th><a href="...">Abecean Longfin</a></th>
    <td>Weakness to Frost</td><td>Fortify Sneak</td>
    <td>Weakness to Poison</td><td>Fortify Restoration</td>
    <td>0.5</td><td>15</td><td>00106E1B</td>
  </tr>
</table>
"""

SECOND_INGREDIENT_TABLE = """
<table class="wikitable sortable">
  <tr><th>Ingredient</th><th>Primary Effect</th><th>Secondary Effect</th>
      <th>Tertiary Effect</th><th>Quaternary Effect</th>
      <th>Weight</th><th>Value</th><th>ID</th></tr>
  <tr>
    <th><a href="...">Ancestor Moth Wing</a></th>
    <td>Damage Stamina</td><td>Fortify Conjuration</td>
    <td>Damage Magicka Regen</td><td>Fortify Enchanting</td>
    <td>0</td><td>2</td><td>XX003523</td>
  </tr>
</table>
"""

POTION_TABLE = """
<table class="wikitable sortable">
  <tr><th>Potion</th><th>Ingredients</th><th>Cure Disease</th></tr>
  <tr><td>Cure Disease</td><td>Charred Skeever Hide</td><td>Yes</td></tr>
</table>
"""

SAMPLE_HTML = INGREDIENT_TABLE + SECOND_INGREDIENT_TABLE + POTION_TABLE
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
    soup = fetch_parsed_html('Ingredients_(Skyrim)', session=session)
    assert soup.find('table', class_='wikitable') is not None

def test_fetch_parsed_html_non_200_raises():
    session = make_mock_session(None, raise_error=True)
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_parsed_html('Ingredients_(Skyrim)', session=session)


# ---------------------------------------------------------------------------
# extract_rows — multi-table, Potion table excluded
# ---------------------------------------------------------------------------

def test_extract_rows_single_table_single_row():
    soup = BeautifulSoup(INGREDIENT_TABLE, 'html.parser')
    rows = extract_rows(soup, all_tables=True)
    assert len(rows) == 1
    assert rows[0][0] == 'Abecean Longfin'

def test_extract_rows_all_tables_combines_ingredient_tables():
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    rows = extract_rows(soup, all_tables=True)
    # 2 ingredient tables × 1 row each = 2; Potion table is skipped
    assert len(rows) == 2
    names = [r[0] for r in rows]
    assert 'Abecean Longfin' in names
    assert 'Ancestor Moth Wing' in names

def test_extract_rows_potion_table_excluded():
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    rows = extract_rows(soup, all_tables=True)
    names = [r[0] for r in rows]
    assert 'Cure Disease' not in names

def test_extract_rows_no_table_returns_empty():
    soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
    assert extract_rows(soup, all_tables=True) == []

def test_extract_rows_single_mode_uses_first_table_only():
    soup = BeautifulSoup(SAMPLE_HTML, 'html.parser')
    rows = extract_rows(soup, all_tables=False)
    assert len(rows) == 1
    assert rows[0][0] == 'Abecean Longfin'


# ---------------------------------------------------------------------------
# fields_from_row — inserts blank location at index 7
# ---------------------------------------------------------------------------

def test_fields_from_row_inserts_blank_location():
    cells = ['Abecean Longfin', 'Weakness to Frost', 'Fortify Sneak', 'Weakness to Poison', 'Fortify Restoration', '0.5', '15', '00106E1B']
    result = fields_from_row(cells)
    assert result is not None
    assert len(result) == 9
    assert result[7] == ''        # blank location
    assert result[8] == '00106E1B'  # ID at position 8

def test_fields_from_row_wrong_count_returns_none():
    assert fields_from_row(['a', 'b', 'c']) is None

def test_fields_from_row_nine_columns_returns_none():
    assert fields_from_row(['a'] * 9) is None


# ---------------------------------------------------------------------------
# format_entry — 10 lines per entry
# ---------------------------------------------------------------------------

def test_format_entry_produces_10_lines():
    fields = ['Abecean Longfin', 'Weakness to Frost', 'Fortify Sneak', 'Weakness to Poison', 'Fortify Restoration', '0.5', '15', '', '00106E1B']
    lines = format_entry(fields).rstrip('\n').split('\n')
    assert len(lines) == 10

def test_format_entry_blank_location_is_bare_pipe():
    fields = ['Name', 'e1', 'e2', 'e3', 'e4', '0.5', '15', '', 'ID']
    lines = format_entry(fields).rstrip('\n').split('\n')
    assert lines[8] == '|'   # blank location field

def test_format_entry_id_is_last_line():
    fields = ['Name', 'e1', 'e2', 'e3', 'e4', '0.5', '15', '', '00106E1B']
    lines = format_entry(fields).rstrip('\n').split('\n')
    assert lines[9] == '|00106E1B'


# ---------------------------------------------------------------------------
# write_raw_file + round-trip with Skyrim parser
# ---------------------------------------------------------------------------

def test_write_raw_file_creates_correct_content(tmp_path):
    outfile = str(tmp_path / 'out.txt')
    fields = fields_from_row(['Abecean Longfin', 'Weakness to Frost', 'Fortify Sneak', 'Weakness to Poison', 'Fortify Restoration', '0.5', '15', '00106E1B'])
    write_raw_file([format_entry(fields)], outfile)
    content = Path(outfile).read_text()
    assert '|Abecean Longfin' in content
    assert content.count('\n') >= 10

def test_write_raw_file_round_trip_with_parser(tmp_path):
    outfile = str(tmp_path / 'out.txt')
    entries = [
        format_entry(fields_from_row(['Abecean Longfin', 'Weakness to Frost', 'Fortify Sneak', 'Weakness to Poison', 'Fortify Restoration', '0.5', '15', '00106E1B'])),
        format_entry(fields_from_row(['Bear Claws', 'Restore Stamina', 'Fortify Health', 'Fortify One-handed', 'Damage Magicka Regen', '0.1', '3', '0003AD57'])),
    ]
    write_raw_file(entries, outfile)
    parse_mod = load_module(
        'Skyrim/alchemy/ingredients_parse/skyrim_parse_wiki_to_json.py',
        'sk_alchemy_parse_check',
    )
    ing, eff = parse_mod.parse(outfile)
    assert len(ing) == 2
    assert ing[0]['name'] == 'Abecean Longfin'
    assert ing[1]['name'] == 'Bear Claws'

def test_write_raw_file_bad_path_raises():
    with pytest.raises(OSError):
        write_raw_file([], '/nonexistent_dir_xyz/out.txt')
