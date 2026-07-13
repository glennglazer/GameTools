"""Tests for perks, effects, and apparel JSON parsers."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

PERKS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/perks_json/skyrim_parse_enchant_perks_to_json.py')
EFFECTS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/enchant_effects_json/skyrim_parse_enchant_effects_to_json.py')
APPAREL_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/enchant_apparel_json/skyrim_parse_enchant_apparel_to_json.py')

_perks = load_module(
    'TES/Skyrim/enchanting/perks_json/skyrim_parse_enchant_perks_to_json.py',
    'sk_enchant_perks_parse',
)
_effects = load_module(
    'TES/Skyrim/enchanting/enchant_effects_json/skyrim_parse_enchant_effects_to_json.py',
    'sk_enchant_effects_parse',
)
_apparel = load_module(
    'TES/Skyrim/enchanting/enchant_apparel_json/skyrim_parse_enchant_apparel_to_json.py',
    'sk_enchant_apparel_parse',
)

PERKS_RAW = (
    "Enchanter (1/5)|0|None|New enchantments are 20% stronger.\n"
    "Soul Squeezer|20|Enchanter (1/5)|Soul gems provide extra magicka.\n"
)

EFFECTS_RAW = (
    "Absorb Health|Destruction\n"
    "Banish|Conjuration\n"
)

APPAREL_RAW = (
    "Fortify Alchemy|True|False|True|False|False|True|True\n"
    "Muffle|False|False|False|True|False|False|False\n"
)

PERKS_SAMPLE = [
    {'name': 'Enchanter (1/5)', 'skill_level': 0, 'prerequisite': 'None',
     'description': 'New enchantments are 20% stronger.'},
    {'name': 'Soul Squeezer', 'skill_level': 20, 'prerequisite': 'Enchanter (1/5)',
     'description': 'Soul gems provide extra magicka.'},
]

EFFECTS_SAMPLE = [
    {'name': 'Absorb Health', 'school': 'Destruction'},
    {'name': 'Banish', 'school': 'Conjuration'},
]

APPAREL_SAMPLE = [
    {'enchantment': 'Fortify Alchemy', 'head': True, 'chest': False,
     'hands': True, 'feet': False, 'shield': False, 'amulet': True, 'ring': True},
    {'enchantment': 'Muffle', 'head': False, 'chest': False,
     'hands': False, 'feet': True, 'shield': False, 'amulet': False, 'ring': False},
]


def make_raw(tmp_path, filename, content):
    p = tmp_path / filename
    p.write_text(content)
    return str(p)


def run(script, args):
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


# ===========================================================================
# perks parser
# ===========================================================================

def test_perks_parse_count(tmp_path):
    infile = make_raw(tmp_path, 'perks.txt', PERKS_RAW)
    assert len(_perks.parse(infile)) == 2

def test_perks_parse_skill_is_int(tmp_path):
    infile = make_raw(tmp_path, 'perks.txt', PERKS_RAW)
    rows = _perks.parse(infile)
    assert isinstance(rows[0]['skill_level'], int)

def test_perks_parse_fields(tmp_path):
    infile = make_raw(tmp_path, 'perks.txt', PERKS_RAW)
    rows = _perks.parse(infile)
    assert rows[0]['name'] == 'Enchanter (1/5)'
    assert rows[0]['prerequisite'] == 'None'

def test_perks_parse_wrong_fields_raises(tmp_path):
    bad = make_raw(tmp_path, 'bad.txt', 'TooFew|fields\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _perks.parse(bad)

def test_perks_parse_bad_skill_raises(tmp_path):
    bad = make_raw(tmp_path, 'bad.txt', 'Enchanter (1/5)|NOTINT|None|desc\n')
    with pytest.raises(ValueError, match='not an integer'):
        _perks.parse(bad)

def test_perks_compute_diff_new_row():
    new = {'name': 'Purity', 'skill_level': 100, 'prerequisite': 'Snakeblood', 'description': 'X'}
    upsert, delete = _perks.compute_diff(PERKS_SAMPLE, PERKS_SAMPLE + [new], lambda r: r['name'])
    assert len(upsert) == 1 and upsert[0]['name'] == 'Purity'

def test_perks_subprocess_creates_json(tmp_path):
    infile = make_raw(tmp_path, 'perks.txt', PERKS_RAW)
    outfile = str(tmp_path / 'perks.json')
    result = run(PERKS_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 2

def test_perks_subprocess_no_change(tmp_path):
    infile = make_raw(tmp_path, 'perks.txt', PERKS_RAW)
    outfile = str(tmp_path / 'perks.json')
    run(PERKS_SCRIPT, [infile, outfile])
    result = run(PERKS_SCRIPT, [infile, outfile])
    assert result.returncode == 0
    assert 'No changes' in result.stderr

def test_perks_subprocess_missing_input_exits_nonzero(tmp_path):
    result = run(PERKS_SCRIPT, [str(tmp_path / 'missing.txt'), str(tmp_path / 'out.json')])
    assert result.returncode != 0


# ===========================================================================
# effects parser
# ===========================================================================

def test_effects_parse_count(tmp_path):
    infile = make_raw(tmp_path, 'eff.txt', EFFECTS_RAW)
    assert len(_effects.parse(infile)) == 2

def test_effects_parse_fields(tmp_path):
    infile = make_raw(tmp_path, 'eff.txt', EFFECTS_RAW)
    rows = _effects.parse(infile)
    assert rows[0] == {'name': 'Absorb Health', 'school': 'Destruction'}

def test_effects_parse_wrong_fields_raises(tmp_path):
    bad = make_raw(tmp_path, 'bad.txt', 'OnlyOne\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _effects.parse(bad)

def test_effects_parse_empty_name_raises(tmp_path):
    bad = make_raw(tmp_path, 'bad.txt', '|Destruction\n')
    with pytest.raises(ValueError, match='empty name'):
        _effects.parse(bad)

def test_effects_compute_diff_no_change():
    upsert, delete = _effects.compute_diff(EFFECTS_SAMPLE, EFFECTS_SAMPLE, lambda r: r['name'])
    assert upsert == [] and delete == []

def test_effects_subprocess_creates_json(tmp_path):
    infile = make_raw(tmp_path, 'eff.txt', EFFECTS_RAW)
    outfile = str(tmp_path / 'eff.json')
    result = run(EFFECTS_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 2

def test_effects_subprocess_no_change(tmp_path):
    infile = make_raw(tmp_path, 'eff.txt', EFFECTS_RAW)
    outfile = str(tmp_path / 'eff.json')
    run(EFFECTS_SCRIPT, [infile, outfile])
    result = run(EFFECTS_SCRIPT, [infile, outfile])
    assert 'No changes' in result.stderr


# ===========================================================================
# apparel parser
# ===========================================================================

def test_apparel_parse_count(tmp_path):
    infile = make_raw(tmp_path, 'app.txt', APPAREL_RAW)
    assert len(_apparel.parse(infile)) == 2

def test_apparel_parse_booleans(tmp_path):
    infile = make_raw(tmp_path, 'app.txt', APPAREL_RAW)
    rows = _apparel.parse(infile)
    assert rows[0]['head'] is True
    assert rows[0]['chest'] is False
    assert rows[1]['feet'] is True

def test_apparel_parse_types_are_bool(tmp_path):
    infile = make_raw(tmp_path, 'app.txt', APPAREL_RAW)
    rows = _apparel.parse(infile)
    for col in ['head', 'chest', 'hands', 'feet', 'shield', 'amulet', 'ring']:
        assert isinstance(rows[0][col], bool)

def test_apparel_parse_wrong_fields_raises(tmp_path):
    bad = make_raw(tmp_path, 'bad.txt', 'Name|True\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _apparel.parse(bad)

def test_apparel_parse_bad_bool_raises(tmp_path):
    bad = make_raw(tmp_path, 'bad.txt', 'Name|Yes|False|False|False|False|False|False\n')
    with pytest.raises(ValueError, match='True or False'):
        _apparel.parse(bad)

def test_apparel_parse_empty_name_raises(tmp_path):
    bad = make_raw(tmp_path, 'bad.txt', '|True|False|False|False|False|False|False\n')
    with pytest.raises(ValueError, match='empty enchantment'):
        _apparel.parse(bad)

def test_apparel_compute_diff_changed_slot(tmp_path):
    modified = [{**APPAREL_SAMPLE[0], 'head': False}] + APPAREL_SAMPLE[1:]
    upsert, delete = _apparel.compute_diff(
        APPAREL_SAMPLE, modified, lambda r: r['enchantment']
    )
    assert len(upsert) == 1 and upsert[0]['head'] is False

def test_apparel_subprocess_creates_json(tmp_path):
    infile = make_raw(tmp_path, 'app.txt', APPAREL_RAW)
    outfile = str(tmp_path / 'app.json')
    result = run(APPAREL_SCRIPT, [infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 2
    assert isinstance(data[0]['head'], bool)

def test_apparel_subprocess_no_change(tmp_path):
    infile = make_raw(tmp_path, 'app.txt', APPAREL_RAW)
    outfile = str(tmp_path / 'app.json')
    run(APPAREL_SCRIPT, [infile, outfile])
    result = run(APPAREL_SCRIPT, [infile, outfile])
    assert 'No changes' in result.stderr

def test_apparel_write_diff_files_sentinel(tmp_path):
    outfile = str(tmp_path / 'app.json')
    _apparel.write_diff_files(outfile, [], [])
    upsert = json.loads((tmp_path / 'app.upsert.json').read_text())
    assert upsert == {}
