"""Tests for the smithing_parse scraper (perks, improvement, crafting materials)."""
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

SCRAPER_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/smithing_parse/skyrim_scrape_smithing.py')

_scraper = load_module(
    'TES/Skyrim/smithing/smithing_parse/skyrim_scrape_smithing.py',
    'sk_smithing_scraper',
)


def make_soup(html):
    return BeautifulSoup(html, 'html.parser')


# ---------------------------------------------------------------------------
# parse_perk_name
# ---------------------------------------------------------------------------

def test_perk_name_strips_asterisks():
    td = BeautifulSoup('<td>Steel Smithing**</td>', 'html.parser').find('td')
    assert _scraper.parse_perk_name(td) == 'Steel Smithing'

def test_perk_name_strips_dlc_marker():
    td = BeautifulSoup('<td>Vampire DG</td>', 'html.parser').find('td')
    assert _scraper.parse_perk_name(td) == 'Vampire'

def test_perk_name_via_link():
    td = BeautifulSoup('<td><a href="#">Advanced Armors</a>**</td>', 'html.parser').find('td')
    assert _scraper.parse_perk_name(td) == 'Advanced Armors'

def test_perk_name_no_suffix():
    td = BeautifulSoup('<td>Glass Smithing</td>', 'html.parser').find('td')
    assert _scraper.parse_perk_name(td) == 'Glass Smithing'


# ---------------------------------------------------------------------------
# parse_req_cell
# ---------------------------------------------------------------------------

def test_req_no_requirement():
    td = make_soup('<td>No requirement</td>').find('td')
    skill, prereq = _scraper.parse_req_cell(td)
    assert skill == 0
    assert prereq == 'None'

def test_req_skill_and_prereq():
    td = make_soup('<td>Smithing 60,<br/>Steel Smithing</td>').find('td')
    skill, prereq = _scraper.parse_req_cell(td)
    assert skill == 60
    assert prereq == 'Steel Smithing'

def test_req_or_prereq():
    td = make_soup('<td>Smithing 100,<br/>Glass or Daedric Smithing</td>').find('td')
    skill, prereq = _scraper.parse_req_cell(td)
    assert skill == 100
    assert 'Glass or Daedric' in prereq

def test_req_skill_30():
    td = make_soup('<td>Smithing 30,<br/>Steel Smithing</td>').find('td')
    skill, prereq = _scraper.parse_req_cell(td)
    assert skill == 30
    assert prereq == 'Steel Smithing'


# ---------------------------------------------------------------------------
# parse_perks_table
# ---------------------------------------------------------------------------

PERKS_HTML = """
<table class="skqtable">
  <tr><th>Perk (Ranks)</th><th>Requirements</th><th>Description</th></tr>
  <tr>
    <td><span id="Steel_Smithing"></span>Steel Smithing**</td>
    <td>No requirement</td>
    <td>Can create steel armor and weapons at forges.</td>
  </tr>
  <tr>
    <td>Arcane Blacksmith</td>
    <td>Smithing 60,<br/>Steel Smithing</td>
    <td>Magical weapons and armor can now be improved.</td>
  </tr>
  <tr>
    <td><a href="#">Dragon Armor</a></td>
    <td>Smithing 100,<br/>Glass or Daedric Smithing</td>
    <td>Can create dragon armor at forges.</td>
  </tr>
</table>
"""

def test_parse_perks_count():
    soup = make_soup(PERKS_HTML)
    perks = _scraper.parse_perks_table(soup)
    assert len(perks) == 3

def test_parse_perks_first_perk():
    soup = make_soup(PERKS_HTML)
    perks = _scraper.parse_perks_table(soup)
    assert perks[0]['name'] == 'Steel Smithing'
    assert perks[0]['skill_level'] == 0
    assert perks[0]['prerequisite'] == 'None'

def test_parse_perks_arcane_blacksmith():
    soup = make_soup(PERKS_HTML)
    perks = _scraper.parse_perks_table(soup)
    ab = next(p for p in perks if p['name'] == 'Arcane Blacksmith')
    assert ab['skill_level'] == 60
    assert ab['prerequisite'] == 'Steel Smithing'

def test_parse_perks_dragon_armor_or_prereq():
    soup = make_soup(PERKS_HTML)
    perks = _scraper.parse_perks_table(soup)
    da = next(p for p in perks if p['name'] == 'Dragon Armor')
    assert da['skill_level'] == 100
    assert 'Glass or Daedric' in da['prerequisite']

def test_parse_perks_no_pipes_in_description():
    soup = make_soup(PERKS_HTML)
    perks = _scraper.parse_perks_table(soup)
    for p in perks:
        assert '|' not in p['description']

def test_parse_perks_double_asterisk_stripped():
    soup = make_soup(PERKS_HTML)
    perks = _scraper.parse_perks_table(soup)
    assert perks[0]['name'] == 'Steel Smithing'
    assert '**' not in perks[0]['name']

def test_parse_perks_ignores_non_skqtable():
    html = '<table class="wikitable"><tr><th>Perk (Ranks)</th></tr></table>' + PERKS_HTML
    soup = make_soup(html)
    perks = _scraper.parse_perks_table(soup)
    assert len(perks) == 3


# ---------------------------------------------------------------------------
# parse_improvement_table
# ---------------------------------------------------------------------------

IMPROVEMENT_HTML = """
<table>
  <tr>
    <th rowspan="2">Quality</th>
    <th colspan="2">Skill Required</th>
    <th colspan="2">Effect</th>
  </tr>
  <tr>
    <th>Without Perk</th><th>With Perk</th>
    <th>Armor</th><th>Weapon</th>
  </tr>
  <tr><td>Fine</td><td>14</td><td>14</td><td>+2</td><td>+1</td></tr>
  <tr><td>Superior</td><td>31</td><td>22</td><td>+6</td><td>+3</td></tr>
  <tr><td>Legendary</td><td>168</td><td>91</td><td>+20</td><td>+10</td></tr>
</table>
"""

def test_parse_improvement_count():
    soup = make_soup(IMPROVEMENT_HTML)
    rows = _scraper.parse_improvement_table(soup)
    assert len(rows) == 3

def test_parse_improvement_fine():
    soup = make_soup(IMPROVEMENT_HTML)
    rows = _scraper.parse_improvement_table(soup)
    fine = rows[0]
    assert fine['quality'] == 'Fine'
    assert fine['skill_without_perk'] == '14'
    assert fine['skill_with_perk'] == '14'
    assert fine['armor_effect'] == '+2'
    assert fine['weapon_effect'] == '+1'

def test_parse_improvement_legendary():
    soup = make_soup(IMPROVEMENT_HTML)
    rows = _scraper.parse_improvement_table(soup)
    leg = rows[-1]
    assert leg['quality'] == 'Legendary'
    assert leg['skill_without_perk'] == '168'


# ---------------------------------------------------------------------------
# parse_materials_table
# ---------------------------------------------------------------------------

MATERIALS_HTML = """
<table>
  <tr><th>Smithing Category</th><th>Crafting Material</th></tr>
  <tr><td>Long Bow</td><td>Firewood</td></tr>
  <tr><td>Iron</td><td rowspan="2">Iron Ingot</td></tr>
  <tr><td>Studded</td></tr>
  <tr><td>Steel</td><td>Steel Ingot</td></tr>
</table>
"""

def test_parse_materials_count():
    soup = make_soup(MATERIALS_HTML)
    rows = _scraper.parse_materials_table(soup)
    assert len(rows) == 4

def test_parse_materials_simple_row():
    soup = make_soup(MATERIALS_HTML)
    rows = _scraper.parse_materials_table(soup)
    longbow = next(r for r in rows if r['smithing_category'] == 'Long Bow')
    assert longbow['crafting_material'] == 'Firewood'

def test_parse_materials_rowspan_expanded():
    soup = make_soup(MATERIALS_HTML)
    rows = _scraper.parse_materials_table(soup)
    # Both Iron and Studded should map to Iron Ingot
    categories = {r['smithing_category']: r['crafting_material'] for r in rows}
    assert categories['Iron'] == 'Iron Ingot'
    assert categories['Studded'] == 'Iron Ingot'

def test_parse_materials_dlc_stripped():
    html = """
    <table>
      <tr><th>Smithing Category</th><th>Crafting Material</th></tr>
      <tr><td>Vampire DG</td><td>Leather</td></tr>
    </table>
    """
    soup = make_soup(html)
    rows = _scraper.parse_materials_table(soup)
    assert rows[0]['smithing_category'] == 'Vampire'


# ---------------------------------------------------------------------------
# write_raw_file
# ---------------------------------------------------------------------------

def test_write_raw_file(tmp_path):
    records = [
        {'name': 'Steel Smithing', 'skill_level': 0, 'prerequisite': 'None',
         'description': 'Can create steel armor.'},
    ]
    outfile = str(tmp_path / 'out.txt')
    _scraper.write_raw_file(records, outfile,
                            ['name', 'skill_level', 'prerequisite', 'description'])
    lines = (tmp_path / 'out.txt').read_text().splitlines()
    assert len(lines) == 1
    assert lines[0] == 'Steel Smithing|0|None|Can create steel armor.'


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def test_scraper_help():
    result = subprocess.run(
        [sys.executable, SCRAPER_SCRIPT, '--help'],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert 'out-dir' in result.stdout

def test_scraper_bad_out_dir():
    result = subprocess.run(
        [sys.executable, SCRAPER_SCRIPT, '--out-dir', '/nonexistent_xyz'],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
