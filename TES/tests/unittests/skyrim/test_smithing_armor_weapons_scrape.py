"""Tests for armor_parse and weapons_parse scrapers (table parsing logic)."""
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

ARMOR_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/armor_parse/skyrim_scrape_smithing_armor.py')
WEAPON_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/weapons_parse/skyrim_scrape_smithing_weapons.py')

_armor = load_module(
    'TES/Skyrim/smithing/armor_parse/skyrim_scrape_smithing_armor.py',
    'sk_armor_scraper',
)
_weapon = load_module(
    'TES/Skyrim/smithing/weapons_parse/skyrim_scrape_smithing_weapons.py',
    'sk_weapon_scraper',
)


def make_soup(html):
    return BeautifulSoup(html, 'html.parser')


# ---------------------------------------------------------------------------
# armor scraper — parse_armor_tables
# ---------------------------------------------------------------------------

STEEL_ARMOR_HTML = """
<table class="wikitable sortable highlight">
  <tr>
    <th>Piece</th>
    <th><img alt="ArmorIcon"/></th>
    <th><img alt="WeightIcon"/></th>
    <th><img alt="Gold"/></th>
    <th>Leather Strips</th>
    <th>Iron Ingot</th>
    <th>Steel Ingot</th>
    <th>ID</th>
  </tr>
  <tr>
    <th>Steel Armor</th>
    <td>34</td><td>35</td><td>275</td>
    <td>3</td><td>1</td><td>3</td>
    <td>0001395C</td>
  </tr>
  <tr>
    <th>Steel Helmet</th>
    <td>15</td><td>5</td><td>60</td>
    <td>2</td><td>1</td><td>2</td>
    <td>00013954</td>
  </tr>
  <tr>
    <th>Total (with shield)</th>
    <td>96</td><td>64</td><td>660</td>
    <td>10</td><td>5</td><td>14</td>
    <td>–</td>
  </tr>
</table>
"""

def test_armor_parse_count():
    soup = make_soup(STEEL_ARMOR_HTML)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    assert len(rows) == 2

def test_armor_parse_piece_name():
    soup = make_soup(STEEL_ARMOR_HTML)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    names = [r['piece'] for r in rows]
    assert 'Steel Armor' in names

def test_armor_parse_material_perk():
    soup = make_soup(STEEL_ARMOR_HTML)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    assert all(r['material_perk'] == 'Steel Smithing' for r in rows)

def test_armor_parse_stats():
    soup = make_soup(STEEL_ARMOR_HTML)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    armor = next(r for r in rows if r['piece'] == 'Steel Armor')
    assert armor['armor_rating'] == 34
    assert armor['weight'] == 35.0
    assert armor['value'] == 275

def test_armor_parse_materials():
    soup = make_soup(STEEL_ARMOR_HTML)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    armor = next(r for r in rows if r['piece'] == 'Steel Armor')
    assert armor['leather_strips'] == 3
    assert armor['iron_ingot'] == 1
    assert armor['steel_ingot'] == 3

def test_armor_parse_total_row_excluded():
    soup = make_soup(STEEL_ARMOR_HTML)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    names = [r['piece'] for r in rows]
    assert not any(n.startswith('Total') for n in names)

def test_armor_parse_unused_cols_zero():
    soup = make_soup(STEEL_ARMOR_HTML)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    armor = next(r for r in rows if r['piece'] == 'Steel Armor')
    assert armor['ebony_ingot'] == 0
    assert armor['daedra_heart'] == 0
    assert armor['stalhrim'] == 0

def test_armor_parse_no_material_table_skipped():
    html = """
    <table>
      <tr>
        <th>Piece</th>
        <th><img alt="ArmorIcon"/></th>
        <th><img alt="WeightIcon"/></th>
        <th><img alt="Gold"/></th>
        <th>ID</th>
      </tr>
      <tr><th>Elven Light Armor</th><td>46</td><td>7</td><td>275</td><td>AAA</td></tr>
    </table>
    """
    soup = make_soup(html)
    rows = _armor.parse_armor_tables(soup, 'Elven Smithing')
    assert rows == []

def test_armor_parse_non_craftable_excluded():
    html = """
    <table>
      <tr>
        <th>Piece</th>
        <th><img alt="ArmorIcon"/></th>
        <th><img alt="WeightIcon"/></th>
        <th><img alt="Gold"/></th>
        <th>Iron Ingot</th><th>ID</th>
      </tr>
      <tr><th>Found Only Item</th><td>20</td><td>10</td><td>100</td><td>0</td><td>ABC</td></tr>
    </table>
    """
    soup = make_soup(html)
    rows = _armor.parse_armor_tables(soup, 'Steel Smithing')
    assert rows == []

def test_armor_parse_dragonplate_icon_variants():
    html = """
    <table>
      <tr>
        <th>Piece</th>
        <th><img alt="Iron Shield SK"/></th>
        <th><img alt="Skyrim-knapsack"/></th>
        <th><img alt="Gold"/></th>
        <th>Dragon Scales</th>
        <th>Dragon Bone</th>
        <th>Leather Strips</th>
        <th>ID</th>
      </tr>
      <tr>
        <th>Dragonplate Armor</th>
        <td>102</td><td>40</td><td>1500</td>
        <td>4</td><td>2</td><td>3</td>
        <td>xx001234</td>
      </tr>
    </table>
    """
    soup = make_soup(html)
    rows = _armor.parse_armor_tables(soup, 'Dragon Armor')
    assert len(rows) == 1
    row = rows[0]
    assert row['armor_rating'] == 102
    assert row['weight'] == 40.0
    assert row['dragon_scales'] == 4
    assert row['dragon_bone'] == 2

def test_armor_parse_comma_formatted_value():
    html = """
    <table>
      <tr>
        <th>Piece</th>
        <th><img alt="ArmorIcon"/></th>
        <th><img alt="WeightIcon"/></th>
        <th><img alt="Gold"/></th>
        <th>Orichalcum Ingot</th>
        <th>ID</th>
      </tr>
      <tr>
        <th>Orcish Armor</th>
        <td>34</td><td>35</td><td>2,400</td>
        <td>3</td>
        <td>000139B3</td>
      </tr>
    </table>
    """
    soup = make_soup(html)
    rows = _armor.parse_armor_tables(soup, 'Orcish Smithing')
    assert rows[0]['value'] == 2400

def test_armor_parse_dlc_marker_stripped_from_piece():
    html = """
    <table>
      <tr>
        <th>Piece</th>
        <th><img alt="ArmorIcon"/></th>
        <th><img alt="WeightIcon"/></th>
        <th><img alt="Gold"/></th>
        <th>Stalhrim</th>
        <th>ID</th>
      </tr>
      <tr>
        <th>Stalhrim Armor DG</th>
        <td>39</td><td>59</td><td>800</td>
        <td>3</td>
        <td>xx001234</td>
      </tr>
    </table>
    """
    soup = make_soup(html)
    rows = _armor.parse_armor_tables(soup, 'Ebony Smithing')
    assert rows[0]['piece'] == 'Stalhrim Armor'


# ---------------------------------------------------------------------------
# weapon scraper — parse_weapon_tables
# ---------------------------------------------------------------------------

STEEL_WEAPON_HTML = """
<table class="wikitable sortable">
  <tr>
    <th>Piece</th>
    <th><img alt="DamageIcon"/></th>
    <th><img alt="WeightIcon"/></th>
    <th><img alt="Gold"/></th>
    <th>Leather Strips</th>
    <th>Iron Ingot</th>
    <th>Steel Ingot</th>
    <th>Firewood</th>
    <th>ID</th>
  </tr>
  <tr>
    <th>Steel Dagger</th>
    <td>5</td><td>2.5</td><td>25</td>
    <td>1</td><td>1</td><td>1</td><td>0</td>
    <td>0001397E</td>
  </tr>
  <tr>
    <th>Steel Greatsword</th>
    <td>15</td><td>16</td><td>150</td>
    <td>2</td><td>1</td><td>2</td><td>1</td>
    <td>00013981</td>
  </tr>
</table>
"""

def test_weapon_parse_count():
    soup = make_soup(STEEL_WEAPON_HTML)
    rows = _weapon.parse_weapon_tables(soup, 'Steel Smithing')
    assert len(rows) == 2

def test_weapon_parse_piece_name():
    soup = make_soup(STEEL_WEAPON_HTML)
    rows = _weapon.parse_weapon_tables(soup, 'Steel Smithing')
    names = [r['piece'] for r in rows]
    assert 'Steel Dagger' in names

def test_weapon_parse_stats():
    soup = make_soup(STEEL_WEAPON_HTML)
    rows = _weapon.parse_weapon_tables(soup, 'Steel Smithing')
    dagger = next(r for r in rows if r['piece'] == 'Steel Dagger')
    assert dagger['damage'] == 5
    assert dagger['weight'] == 2.5
    assert dagger['value'] == 25

def test_weapon_parse_materials():
    soup = make_soup(STEEL_WEAPON_HTML)
    rows = _weapon.parse_weapon_tables(soup, 'Steel Smithing')
    gs = next(r for r in rows if r['piece'] == 'Steel Greatsword')
    assert gs['leather_strips'] == 2
    assert gs['steel_ingot'] == 2
    assert gs['firewood'] == 1

def test_weapon_parse_non_craftable_excluded():
    html = """
    <table>
      <tr>
        <th>Name</th>
        <th><img alt="DamageIcon"/></th>
        <th><img alt="WeightIcon"/></th>
        <th><img alt="Gold"/></th>
        <th>Leather Strips</th>
        <th>Firewood</th>
        <th>ID</th>
      </tr>
      <tr>
        <th>Nordic Bow</th>
        <td>13</td><td>10</td><td>185</td>
        <td>-</td><td>-</td>
        <td>xx012345</td>
      </tr>
    </table>
    """
    soup = make_soup(html)
    rows = _weapon.parse_weapon_tables(soup, 'Advanced Armors')
    assert rows == []

def test_weapon_parse_ebony_icon_variants():
    html = """
    <table>
      <tr>
        <th></th>
        <th><img alt="IronDagger SK"/></th>
        <th><img alt="Skyrim-knapsack"/></th>
        <th><img alt="Gold"/></th>
        <th>Leather Strips</th>
        <th>Ebony Ingots</th>
        <th>Firewood</th>
        <th>ID</th>
      </tr>
      <tr>
        <th>Ebony Dagger</th>
        <td>10</td><td>5</td><td>290</td>
        <td>1</td><td>1</td><td>0</td>
        <td>000139AE</td>
      </tr>
    </table>
    """
    soup = make_soup(html)
    rows = _weapon.parse_weapon_tables(soup, 'Ebony Smithing')
    assert len(rows) == 1
    row = rows[0]
    assert row['damage'] == 10
    assert row['ebony_ingot'] == 1

def test_weapon_parse_unused_cols_zero():
    soup = make_soup(STEEL_WEAPON_HTML)
    rows = _weapon.parse_weapon_tables(soup, 'Steel Smithing')
    dagger = next(r for r in rows if r['piece'] == 'Steel Dagger')
    assert dagger['ebony_ingot'] == 0
    assert dagger['daedra_heart'] == 0
    assert dagger['stalhrim'] == 0

def test_weapon_parse_crossbow_as_material():
    html = """
    <table>
      <tr>
        <th>Piece</th>
        <th><img alt="DamageIcon"/></th>
        <th><img alt="WeightIcon"/></th>
        <th><img alt="Gold"/></th>
        <th>Crossbow</th>
        <th>Corundum Ingot</th>
        <th>ID</th>
      </tr>
      <tr>
        <th>Enhanced Crossbow</th>
        <td>19</td><td>14</td><td>350</td>
        <td>1</td><td>2</td>
        <td>xx00CAFE</td>
      </tr>
    </table>
    """
    soup = make_soup(html)
    rows = _weapon.parse_weapon_tables(soup, 'Steel Smithing')
    assert len(rows) == 1
    assert rows[0]['crossbow'] == 1
    assert rows[0]['corundum_ingot'] == 2


# ---------------------------------------------------------------------------
# write_raw_file
# ---------------------------------------------------------------------------

def test_armor_write_raw_file(tmp_path):
    mat_cols = _armor.ARMOR_MATERIAL_COLS
    rec = {col: 0 for col in mat_cols}
    rec.update({'piece': 'Steel Armor', 'material_perk': 'Steel Smithing',
                'armor_rating': 34, 'weight': 35.0, 'value': 275, 'id': 'ABC',
                'leather_strips': 3, 'iron_ingot': 1, 'steel_ingot': 3})
    outfile = str(tmp_path / 'out.txt')
    _armor.write_raw_file([rec], outfile)
    lines = (tmp_path / 'out.txt').read_text().splitlines()
    assert len(lines) == 1
    parts = lines[0].split('|')
    assert len(parts) == len(_armor.ARMOR_ALL_COLS)
    assert parts[0] == 'Steel Armor'
    assert parts[1] == 'Steel Smithing'

def test_weapon_write_raw_file(tmp_path):
    mat_cols = _weapon.WEAPON_MATERIAL_COLS
    rec = {col: 0 for col in mat_cols}
    rec.update({'piece': 'Steel Dagger', 'material_perk': 'Steel Smithing',
                'damage': 5, 'weight': 2.5, 'value': 25, 'id': 'XYZ',
                'leather_strips': 1, 'iron_ingot': 1, 'steel_ingot': 1})
    outfile = str(tmp_path / 'out.txt')
    _weapon.write_raw_file([rec], outfile)
    lines = (tmp_path / 'out.txt').read_text().splitlines()
    assert len(lines) == 1
    parts = lines[0].split('|')
    assert len(parts) == len(_weapon.WEAPON_ALL_COLS)

def test_armor_bad_out_dir():
    result = subprocess.run(
        [sys.executable, ARMOR_SCRIPT, '--out-dir', '/nonexistent_xyz'],
        capture_output=True, text=True,
    )
    assert result.returncode != 0

def test_weapon_bad_out_dir():
    result = subprocess.run(
        [sys.executable, WEAPON_SCRIPT, '--out-dir', '/nonexistent_xyz'],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
