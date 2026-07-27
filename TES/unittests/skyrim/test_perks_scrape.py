"""Tests for TES/Skyrim/alchemy/perks_parse/skyrim_scrape_alchemy_perks.py"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    'TES/Skyrim/alchemy/perks_parse/skyrim_scrape_alchemy_perks.py',
    'sk_perks_scrape',
)
fetch_perks_html  = _mod.fetch_perks_html
parse_perks_table = _mod.parse_perks_table
parse_skill_levels = _mod.parse_skill_levels
parse_prereq_names = _mod.parse_prereq_names
expand_perks      = _mod.expand_perks
write_raw_file    = _mod.write_raw_file
format_line       = _mod.format_line
clean_description = _mod.clean_description

PERKS_TABLE_HTML = """
<table class="wikitable">
<tr><th>Perk (Ranks)</th><th>Requirements</th><th>Description</th></tr>
<tr>
  <td><span id="Alchemist"></span>Alchemist (5)</td>
  <td>Alchemy 0/ 20/ 40/ 60/ 80</td>
  <td>Potions and poisons are 20% / 40% / 60% / 80% / 100% stronger.</td>
</tr>
<tr>
  <td><span id="Physician"></span>Physician</td>
  <td>Alchemy 20, Alchemist</td>
  <td>Potions you mix that restore health or stamina are 25% more powerful.</td>
</tr>
<tr>
  <td><span id="Experimenter"></span>Experimenter (3)</td>
  <td>Alchemy 50/ 70/ 90, Benefactor</td>
  <td>Eating an ingredient reveals the first two / three / four effects.</td>
</tr>
<tr>
  <td><span id="Snakeblood"></span>Snakeblood</td>
  <td>Alchemy 80, Concentrated Poison, Experimenter</td>
  <td>50% resistance to all poisons.</td>
</tr>
<tr>
  <td><span id="Green_Thumb"></span>Green Thumb</td>
  <td>Alchemy 70, Concentrated Poison</td>
  <td>Two ingredients are gathered from plants (description is misleading - editorial note).</td>
</tr>
</table>
"""

SAMPLE_API_RESPONSE = {'parse': {'text': {'*': PERKS_TABLE_HTML}}}


def make_mock_session(json_data=None, raise_error=False):
    mock = MagicMock()
    resp = MagicMock()
    if raise_error:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError('403')
    else:
        resp.raise_for_status.return_value = None
        resp.json.return_value = json_data
    mock.get.return_value = resp
    return mock


# ---------------------------------------------------------------------------
# fetch_perks_html
# ---------------------------------------------------------------------------

def test_fetch_perks_html_returns_soup():
    session = make_mock_session(SAMPLE_API_RESPONSE)
    soup = fetch_perks_html(session=session)
    assert soup.find('table', class_='wikitable') is not None

def test_fetch_perks_html_http_error_raises():
    session = make_mock_session(raise_error=True)
    with pytest.raises(requests.exceptions.HTTPError):
        fetch_perks_html(session=session)

def test_fetch_perks_html_connection_error_raises():
    session = MagicMock()
    session.get.side_effect = requests.exceptions.ConnectionError('refused')
    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_perks_html(session=session)

def test_fetch_perks_html_bad_response_structure_raises():
    session = make_mock_session({'error': {'code': 'missingtitle'}})
    with pytest.raises(KeyError):
        fetch_perks_html(session=session)


# ---------------------------------------------------------------------------
# parse_perks_table
# ---------------------------------------------------------------------------

def test_parse_perks_table_returns_correct_row_count():
    soup = BeautifulSoup(PERKS_TABLE_HTML, 'html.parser')
    rows = parse_perks_table(soup)
    assert len(rows) == 5  # 4 perks + multi-rank Alchemist/Experimenter as single rows

def test_parse_perks_table_first_row_is_alchemist():
    soup = BeautifulSoup(PERKS_TABLE_HTML, 'html.parser')
    rows = parse_perks_table(soup)
    assert rows[0][0] == 'Alchemist (5)'

def test_parse_perks_table_skips_header_row():
    soup = BeautifulSoup(PERKS_TABLE_HTML, 'html.parser')
    names = [r[0] for r in parse_perks_table(soup)]
    assert 'Perk (Ranks)' not in names

def test_parse_perks_table_no_table_raises():
    soup = BeautifulSoup('<html><body></body></html>', 'html.parser')
    with pytest.raises(ValueError, match='wikitable'):
        parse_perks_table(soup)

def test_parse_perks_table_requirements_extracted():
    soup = BeautifulSoup(PERKS_TABLE_HTML, 'html.parser')
    rows = parse_perks_table(soup)
    physician_row = next(r for r in rows if r[0] == 'Physician')
    assert 'Alchemy 20' in physician_row[1]
    assert 'Alchemist' in physician_row[1]


# ---------------------------------------------------------------------------
# parse_skill_levels
# ---------------------------------------------------------------------------

def test_parse_skill_levels_single():
    assert parse_skill_levels('Alchemy 20, Alchemist') == [20]

def test_parse_skill_levels_multi():
    assert parse_skill_levels('Alchemy 0/ 20/ 40/ 60/ 80') == [0, 20, 40, 60, 80]

def test_parse_skill_levels_three():
    assert parse_skill_levels('Alchemy 50/ 70/ 90, Benefactor') == [50, 70, 90]

def test_parse_skill_levels_no_alchemy_returns_empty():
    assert parse_skill_levels('None') == []


# ---------------------------------------------------------------------------
# parse_prereq_names
# ---------------------------------------------------------------------------

def test_parse_prereq_names_single():
    assert parse_prereq_names('Alchemy 20, Alchemist') == ['Alchemist']

def test_parse_prereq_names_multi():
    result = parse_prereq_names('Alchemy 80, Concentrated Poison, Experimenter')
    assert result == ['Concentrated Poison', 'Experimenter']

def test_parse_prereq_names_none():
    assert parse_prereq_names('Alchemy 0/ 20/ 40/ 60/ 80') == []

def test_parse_prereq_names_multi_level_with_prereq():
    assert parse_prereq_names('Alchemy 50/ 70/ 90, Benefactor') == ['Benefactor']


# ---------------------------------------------------------------------------
# clean_description
# ---------------------------------------------------------------------------

def test_clean_description_strips_editor_note():
    desc = 'Two ingredients are gathered from plants (description is misleading - editorial note).'
    assert clean_description(desc) == 'Two ingredients are gathered from plants.'

def test_clean_description_leaves_plain_description_intact():
    desc = '50% resistance to all poisons.'
    assert clean_description(desc) == '50% resistance to all poisons.'

def test_clean_description_ensures_trailing_period():
    assert clean_description('No period').endswith('.')


# ---------------------------------------------------------------------------
# expand_perks
# ---------------------------------------------------------------------------

def _make_raw(soup):
    return parse_perks_table(soup)

def test_expand_perks_alchemist_produces_five_rows():
    raw = [('Alchemist (5)', 'Alchemy 0/ 20/ 40/ 60/ 80', 'X')]
    perks = expand_perks(raw)
    names = [p['name'] for p in perks]
    assert names == [f'Alchemist ({i}/5)' for i in range(1, 6)]

def test_expand_perks_alchemist_skill_levels():
    raw = [('Alchemist (5)', 'Alchemy 0/ 20/ 40/ 60/ 80', 'X')]
    perks = expand_perks(raw)
    assert [p['skill_level'] for p in perks] == [0, 20, 40, 60, 80]

def test_expand_perks_alchemist_prerequisite_chain():
    raw = [('Alchemist (5)', 'Alchemy 0/ 20/ 40/ 60/ 80', 'X')]
    perks = expand_perks(raw)
    assert perks[0]['prerequisite'] == 'None'
    assert perks[1]['prerequisite'] == 'Alchemist (1/5)'
    assert perks[4]['prerequisite'] == 'Alchemist (4/5)'

def test_expand_perks_alchemist_descriptions_contain_magnitudes():
    raw = [('Alchemist (5)', 'Alchemy 0/ 20/ 40/ 60/ 80', 'X')]
    perks = expand_perks(raw)
    assert '20%' in perks[0]['description']
    assert '100%' in perks[4]['description']

def test_expand_perks_experimenter_produces_three_rows():
    raw = [('Experimenter (3)', 'Alchemy 50/ 70/ 90, Benefactor', 'X')]
    perks = expand_perks(raw)
    assert [p['name'] for p in perks] == ['Experimenter (1/3)', 'Experimenter (2/3)', 'Experimenter (3/3)']

def test_expand_perks_experimenter_prereq_chain():
    raw = [('Experimenter (3)', 'Alchemy 50/ 70/ 90, Benefactor', 'X')]
    perks = expand_perks(raw)
    assert perks[0]['prerequisite'] == 'Benefactor'
    assert perks[1]['prerequisite'] == 'Experimenter (1/3)'
    assert perks[2]['prerequisite'] == 'Experimenter (2/3)'

def test_expand_perks_single_remaps_alchemist_prereq():
    raw = [('Physician', 'Alchemy 20, Alchemist', 'Potions restore health.')]
    perks = expand_perks(raw)
    assert perks[0]['prerequisite'] == 'Alchemist (1/5)'

def test_expand_perks_snakeblood_remaps_experimenter_prereq():
    raw = [('Snakeblood', 'Alchemy 80, Concentrated Poison, Experimenter', '50% resistance.')]
    perks = expand_perks(raw)
    assert perks[0]['prerequisite'] == 'Concentrated Poison, Experimenter (1/3)'

def test_expand_perks_no_prereq_becomes_none():
    raw = [('Alchemist (5)', 'Alchemy 0/ 20/ 40/ 60/ 80', 'X')]
    perks = expand_perks(raw)
    assert perks[0]['prerequisite'] == 'None'

def test_expand_perks_full_table():
    soup = BeautifulSoup(PERKS_TABLE_HTML, 'html.parser')
    raw = parse_perks_table(soup)
    perks = expand_perks(raw)
    names = [p['name'] for p in perks]
    assert 'Alchemist (1/5)' in names
    assert 'Alchemist (5/5)' in names
    assert 'Experimenter (1/3)' in names
    assert 'Experimenter (3/3)' in names
    assert 'Physician' in names
    assert 'Snakeblood' in names
    assert 'Green Thumb' in names


# ---------------------------------------------------------------------------
# write_raw_file
# ---------------------------------------------------------------------------

def test_write_raw_file_produces_correct_lines(tmp_path):
    perks = [
        {'name': 'Alchemist (1/5)', 'skill_level': 0, 'prerequisite': 'None',
         'description': 'Potions and poisons are 20% stronger.'},
        {'name': 'Physician', 'skill_level': 20, 'prerequisite': 'Alchemist (1/5)',
         'description': 'Health potions are 25% more powerful.'},
    ]
    outfile = str(tmp_path / 'perks.txt')
    write_raw_file(perks, outfile)
    lines = Path(outfile).read_text().splitlines()
    assert len(lines) == 2
    assert lines[0] == 'Alchemist (1/5)|0|None|Potions and poisons are 20% stronger.'
    assert lines[1] == 'Physician|20|Alchemist (1/5)|Health potions are 25% more powerful.'

def test_write_raw_file_bad_path_raises():
    with pytest.raises(OSError):
        write_raw_file([], '/nonexistent_dir_xyz/out.txt')

def test_format_line_pipe_delimited():
    perk = {'name': 'Purity', 'skill_level': 100, 'prerequisite': 'Snakeblood',
            'description': 'Removes negatives from potions.'}
    assert format_line(perk) == 'Purity|100|Snakeblood|Removes negatives from potions.'
