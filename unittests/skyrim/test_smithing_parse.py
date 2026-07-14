"""Tests for all 5 smithing JSON parsers."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

PERKS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/perks_json/skyrim_parse_smithing_perks_to_json.py')
ARMOR_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/armor_json/skyrim_parse_smithing_armor_to_json.py')
WEAPON_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/weapons_json/skyrim_parse_smithing_weapons_to_json.py')
IMPROVE_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/improvement_json/skyrim_parse_smithing_improvement_to_json.py')
MATS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/materials_json/skyrim_parse_smithing_materials_to_json.py')

_perks = load_module('TES/Skyrim/smithing/perks_json/skyrim_parse_smithing_perks_to_json.py', 'sk_sp_parse')
_armor = load_module('TES/Skyrim/smithing/armor_json/skyrim_parse_smithing_armor_to_json.py', 'sk_sa_parse')
_weapon = load_module('TES/Skyrim/smithing/weapons_json/skyrim_parse_smithing_weapons_to_json.py', 'sk_sw_parse')
_improve = load_module('TES/Skyrim/smithing/improvement_json/skyrim_parse_smithing_improvement_to_json.py', 'sk_si_parse')
_mats = load_module('TES/Skyrim/smithing/materials_json/skyrim_parse_smithing_materials_to_json.py', 'sk_sm_parse')


def make_raw(tmp_path, filename, content):
    p = tmp_path / filename
    p.write_text(content)
    return str(p)


def run(script, args):
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# perks parser
# ---------------------------------------------------------------------------

PERKS_RAW = (
    "Steel Smithing|0|None|Can create steel armor and weapons.\n"
    "Arcane Blacksmith|60|Steel Smithing|Magical armor can be improved.\n"
)

def test_perks_parse_count(tmp_path):
    f = make_raw(tmp_path, 'p.txt', PERKS_RAW)
    assert len(_perks.parse(f)) == 2

def test_perks_parse_fields(tmp_path):
    f = make_raw(tmp_path, 'p.txt', PERKS_RAW)
    rows = _perks.parse(f)
    assert rows[0]['name'] == 'Steel Smithing'
    assert rows[0]['skill_level'] == 0
    assert rows[0]['prerequisite'] == 'None'

def test_perks_parse_skill_is_int(tmp_path):
    f = make_raw(tmp_path, 'p.txt', PERKS_RAW)
    rows = _perks.parse(f)
    assert isinstance(rows[1]['skill_level'], int)
    assert rows[1]['skill_level'] == 60

def test_perks_parse_wrong_fields_raises(tmp_path):
    f = make_raw(tmp_path, 'p.txt', 'TooFew|fields\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _perks.parse(f)

def test_perks_parse_bad_skill_raises(tmp_path):
    f = make_raw(tmp_path, 'p.txt', 'Steel Smithing|NOTINT|None|desc\n')
    with pytest.raises(ValueError, match='not an integer'):
        _perks.parse(f)

def test_perks_subprocess_creates_json(tmp_path):
    infile = make_raw(tmp_path, 'p.txt', PERKS_RAW)
    outfile = str(tmp_path / 'perks.json')
    result = run(PERKS_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 2

def test_perks_subprocess_no_change(tmp_path):
    infile = make_raw(tmp_path, 'p.txt', PERKS_RAW)
    outfile = str(tmp_path / 'perks.json')
    run(PERKS_SCRIPT, [infile, outfile])
    result = run(PERKS_SCRIPT, [infile, outfile])
    assert 'No changes' in result.stderr

def test_perks_subprocess_missing_input(tmp_path):
    result = run(PERKS_SCRIPT, [str(tmp_path / 'missing.txt'), str(tmp_path / 'out.json')])
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# armor parser
# ---------------------------------------------------------------------------

def _make_armor_raw(tmp_path, rows):
    """rows: list of dicts for armor pieces; missing material cols default to 0."""
    mat_cols = _armor.ARMOR_MATERIAL_COLS
    lines = []
    for r in rows:
        fixed = [
            r.get('piece', 'Test Armor'),
            r.get('material_perk', 'Steel Smithing'),
            str(r.get('armor_rating', 34)),
            str(r.get('weight', 35.0)),
            str(r.get('value', 275)),
            r.get('id', 'AAA'),
        ]
        mats = [str(r.get(col, 0)) for col in mat_cols]
        lines.append('|'.join(fixed + mats))
    p = tmp_path / 'armor.txt'
    p.write_text('\n'.join(lines) + '\n')
    return str(p)

ARMOR_SAMPLE = [
    {'piece': 'Steel Armor', 'material_perk': 'Steel Smithing',
     'armor_rating': 34, 'weight': 35.0, 'value': 275, 'id': '0001395C',
     'leather_strips': 3, 'iron_ingot': 1, 'steel_ingot': 3},
    {'piece': 'Steel Helmet', 'material_perk': 'Steel Smithing',
     'armor_rating': 15, 'weight': 5.0, 'value': 60, 'id': '00013954',
     'leather_strips': 2, 'iron_ingot': 1, 'steel_ingot': 2},
]

def test_armor_parse_count(tmp_path):
    f = _make_armor_raw(tmp_path, ARMOR_SAMPLE)
    assert len(_armor.parse(f)) == 2

def test_armor_parse_fields(tmp_path):
    f = _make_armor_raw(tmp_path, ARMOR_SAMPLE)
    rows = _armor.parse(f)
    assert rows[0]['piece'] == 'Steel Armor'
    assert rows[0]['material_perk'] == 'Steel Smithing'
    assert rows[0]['armor_rating'] == 34
    assert rows[0]['weight'] == 35.0
    assert rows[0]['leather_strips'] == 3

def test_armor_parse_types(tmp_path):
    f = _make_armor_raw(tmp_path, ARMOR_SAMPLE)
    rows = _armor.parse(f)
    assert isinstance(rows[0]['armor_rating'], int)
    assert isinstance(rows[0]['weight'], float)
    assert isinstance(rows[0]['leather_strips'], int)

def test_armor_parse_wrong_fields_raises(tmp_path):
    f = make_raw(tmp_path, 'bad.txt', 'Steel Armor|Steel Smithing\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _armor.parse(f)

def test_armor_subprocess_creates_json(tmp_path):
    infile = _make_armor_raw(tmp_path, ARMOR_SAMPLE)
    outfile = str(tmp_path / 'armor.json')
    result = run(ARMOR_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 2

def test_armor_subprocess_no_change(tmp_path):
    infile = _make_armor_raw(tmp_path, ARMOR_SAMPLE)
    outfile = str(tmp_path / 'armor.json')
    run(ARMOR_SCRIPT, [infile, outfile])
    result = run(ARMOR_SCRIPT, [infile, outfile])
    assert 'No changes' in result.stderr

def test_armor_compute_diff_new_row(tmp_path):
    new_row = dict(ARMOR_SAMPLE[0])
    new_row['piece'] = 'Daedric Armor'
    upsert, delete = _armor.compute_diff(
        ARMOR_SAMPLE, ARMOR_SAMPLE + [new_row], lambda r: r['piece']
    )
    assert len(upsert) == 1 and upsert[0]['piece'] == 'Daedric Armor'


# ---------------------------------------------------------------------------
# weapons parser
# ---------------------------------------------------------------------------

def _make_weapon_raw(tmp_path, rows):
    mat_cols = _weapon.WEAPON_MATERIAL_COLS
    lines = []
    for r in rows:
        fixed = [
            r.get('piece', 'Steel Dagger'),
            r.get('material_perk', 'Steel Smithing'),
            str(r.get('damage', 5)),
            str(r.get('weight', 2.5)),
            str(r.get('value', 25)),
            r.get('id', 'AAA'),
        ]
        mats = [str(r.get(col, 0)) for col in mat_cols]
        lines.append('|'.join(fixed + mats))
    p = tmp_path / 'weapons.txt'
    p.write_text('\n'.join(lines) + '\n')
    return str(p)

WEAPON_SAMPLE = [
    {'piece': 'Steel Dagger', 'material_perk': 'Steel Smithing',
     'damage': 5, 'weight': 2.5, 'value': 25, 'id': '0001397E',
     'leather_strips': 1, 'iron_ingot': 1, 'steel_ingot': 1},
    {'piece': 'Steel Sword', 'material_perk': 'Steel Smithing',
     'damage': 8, 'weight': 10.0, 'value': 75, 'id': '00013989',
     'leather_strips': 1, 'iron_ingot': 1, 'steel_ingot': 2},
]

def test_weapon_parse_count(tmp_path):
    f = _make_weapon_raw(tmp_path, WEAPON_SAMPLE)
    assert len(_weapon.parse(f)) == 2

def test_weapon_parse_fields(tmp_path):
    f = _make_weapon_raw(tmp_path, WEAPON_SAMPLE)
    rows = _weapon.parse(f)
    assert rows[0]['piece'] == 'Steel Dagger'
    assert rows[0]['damage'] == 5
    assert rows[0]['weight'] == 2.5

def test_weapon_parse_types(tmp_path):
    f = _make_weapon_raw(tmp_path, WEAPON_SAMPLE)
    rows = _weapon.parse(f)
    assert isinstance(rows[0]['damage'], int)
    assert isinstance(rows[0]['weight'], float)

def test_weapon_subprocess_creates_json(tmp_path):
    infile = _make_weapon_raw(tmp_path, WEAPON_SAMPLE)
    outfile = str(tmp_path / 'weapons.json')
    result = run(WEAPON_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 2


# ---------------------------------------------------------------------------
# improvement parser
# ---------------------------------------------------------------------------

IMPROVE_RAW = (
    "Fine|14|14|+2|+1\n"
    "Superior|31|22|+6|+3\n"
    "Legendary|168|91|+20|+10\n"
)

def test_improve_parse_count(tmp_path):
    f = make_raw(tmp_path, 'i.txt', IMPROVE_RAW)
    assert len(_improve.parse(f)) == 3

def test_improve_parse_fields(tmp_path):
    f = make_raw(tmp_path, 'i.txt', IMPROVE_RAW)
    rows = _improve.parse(f)
    assert rows[0]['quality'] == 'Fine'
    assert rows[0]['skill_without_perk'] == 14
    assert rows[0]['skill_with_perk'] == 14
    assert rows[0]['armor_effect'] == '+2'
    assert rows[0]['weapon_effect'] == '+1'

def test_improve_parse_types(tmp_path):
    f = make_raw(tmp_path, 'i.txt', IMPROVE_RAW)
    rows = _improve.parse(f)
    assert isinstance(rows[0]['skill_without_perk'], int)
    assert isinstance(rows[0]['skill_with_perk'], int)

def test_improve_parse_wrong_fields_raises(tmp_path):
    f = make_raw(tmp_path, 'bad.txt', 'Fine|14\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _improve.parse(f)

def test_improve_subprocess_creates_json(tmp_path):
    infile = make_raw(tmp_path, 'i.txt', IMPROVE_RAW)
    outfile = str(tmp_path / 'imp.json')
    result = run(IMPROVE_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 3

def test_improve_subprocess_no_change(tmp_path):
    infile = make_raw(tmp_path, 'i.txt', IMPROVE_RAW)
    outfile = str(tmp_path / 'imp.json')
    run(IMPROVE_SCRIPT, [infile, outfile])
    result = run(IMPROVE_SCRIPT, [infile, outfile])
    assert 'No changes' in result.stderr


# ---------------------------------------------------------------------------
# materials parser
# ---------------------------------------------------------------------------

MATS_RAW = (
    "Iron|Iron Ingot\n"
    "Studded|Iron Ingot\n"
    "Steel|Steel Ingot\n"
)

def test_mats_parse_count(tmp_path):
    f = make_raw(tmp_path, 'm.txt', MATS_RAW)
    assert len(_mats.parse(f)) == 3

def test_mats_parse_fields(tmp_path):
    f = make_raw(tmp_path, 'm.txt', MATS_RAW)
    rows = _mats.parse(f)
    assert rows[0]['smithing_category'] == 'Iron'
    assert rows[0]['crafting_material'] == 'Iron Ingot'

def test_mats_parse_wrong_fields_raises(tmp_path):
    f = make_raw(tmp_path, 'bad.txt', 'OnlyOne\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _mats.parse(f)

def test_mats_parse_empty_category_raises(tmp_path):
    f = make_raw(tmp_path, 'bad.txt', '|Iron Ingot\n')
    with pytest.raises(ValueError, match='empty smithing_category'):
        _mats.parse(f)

def test_mats_subprocess_creates_json(tmp_path):
    infile = make_raw(tmp_path, 'm.txt', MATS_RAW)
    outfile = str(tmp_path / 'mats.json')
    result = run(MATS_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 3

def test_mats_subprocess_no_change(tmp_path):
    infile = make_raw(tmp_path, 'm.txt', MATS_RAW)
    outfile = str(tmp_path / 'mats.json')
    run(MATS_SCRIPT, [infile, outfile])
    result = run(MATS_SCRIPT, [infile, outfile])
    assert 'No changes' in result.stderr

def test_mats_compute_diff_uses_composite_key():
    old = [{'smithing_category': 'Iron', 'crafting_material': 'Iron Ingot'}]
    new = [
        {'smithing_category': 'Iron', 'crafting_material': 'Iron Ingot'},
        {'smithing_category': 'Steel', 'crafting_material': 'Steel Ingot'},
    ]
    upsert, delete = _mats.compute_diff(
        old, new, lambda r: (r['smithing_category'], r['crafting_material'])
    )
    assert len(upsert) == 1 and upsert[0]['smithing_category'] == 'Steel'
