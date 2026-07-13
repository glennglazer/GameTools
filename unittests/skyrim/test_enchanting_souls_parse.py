"""Tests for gem_types and creature_souls JSON parsers."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

GEM_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/gem_types_json/skyrim_parse_gem_types_to_json.py')
SOULS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/creature_souls_json/skyrim_parse_creature_souls_to_json.py')

_gem = load_module(
    'TES/Skyrim/enchanting/gem_types_json/skyrim_parse_gem_types_to_json.py',
    'sk_gem_parse',
)
_souls = load_module(
    'TES/Skyrim/enchanting/creature_souls_json/skyrim_parse_creature_souls_to_json.py',
    'sk_souls_parse',
)

GEM_SAMPLE_RAW = (
    "Petty Soul Gem|0.1|10|250|Can hold creature souls below level 4.\n"
    "Lesser Soul Gem|0.2|25|500|Can hold creature souls below level 16.\n"
    "Black Soul Gem|1|500|3000|Can hold any soul, including humanoids.\n"
)

SOULS_SAMPLE_RAW = (
    "Chicken|petty\n"
    "Mudcrab|petty\n"
    "Wolf|lesser\n"
    "Nord|black\n"
)

GEM_SAMPLE = [
    {'name': 'Petty Soul Gem', 'weight': 0.1, 'value': 10, 'capacity': 250,
     'trappable_souls': 'Can hold creature souls below level 4.'},
    {'name': 'Lesser Soul Gem', 'weight': 0.2, 'value': 25, 'capacity': 500,
     'trappable_souls': 'Can hold creature souls below level 16.'},
    {'name': 'Black Soul Gem', 'weight': 1.0, 'value': 500, 'capacity': 3000,
     'trappable_souls': 'Can hold any soul, including humanoids.'},
]

SOULS_SAMPLE = [
    {'creature': 'Chicken', 'soul_size': 'petty'},
    {'creature': 'Mudcrab', 'soul_size': 'petty'},
    {'creature': 'Wolf', 'soul_size': 'lesser'},
    {'creature': 'Nord', 'soul_size': 'black'},
]


def make_gem_raw(tmp_path, content=GEM_SAMPLE_RAW):
    p = tmp_path / 'skyrim_soul_gem_types_raw.txt'
    p.write_text(content)
    return str(p)


def make_souls_raw(tmp_path, content=SOULS_SAMPLE_RAW):
    p = tmp_path / 'skyrim_creature_souls_raw.txt'
    p.write_text(content)
    return str(p)


def run_gem(args):
    return subprocess.run([sys.executable, GEM_SCRIPT] + args, capture_output=True, text=True)


def run_souls(args):
    return subprocess.run([sys.executable, SOULS_SCRIPT] + args, capture_output=True, text=True)


# ===========================================================================
# gem_types parser
# ===========================================================================

def test_gem_parse_correct_count(tmp_path):
    assert len(_gem.parse(make_gem_raw(tmp_path))) == 3

def test_gem_parse_float_weight(tmp_path):
    rows = _gem.parse(make_gem_raw(tmp_path))
    assert isinstance(rows[0]['weight'], float)
    assert rows[0]['weight'] == 0.1

def test_gem_parse_int_weight(tmp_path):
    rows = _gem.parse(make_gem_raw(tmp_path))
    black = next(r for r in rows if r['name'] == 'Black Soul Gem')
    assert isinstance(black['weight'], float)
    assert black['weight'] == 1.0

def test_gem_parse_integer_value(tmp_path):
    rows = _gem.parse(make_gem_raw(tmp_path))
    assert isinstance(rows[0]['value'], int)

def test_gem_parse_wrong_fields_raises(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('Too|few\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _gem.parse(str(bad))

def test_gem_parse_bad_weight_raises(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('Name|NOTFLOAT|10|250|desc\n')
    with pytest.raises(ValueError, match='float'):
        _gem.parse(str(bad))

def test_gem_parse_bad_value_raises(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('Name|0.1|NOTINT|250|desc\n')
    with pytest.raises(ValueError, match='integer'):
        _gem.parse(str(bad))

def test_gem_parse_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        _gem.parse(str(tmp_path / 'missing.txt'))

def test_gem_load_json_safe_missing_returns_empty(tmp_path):
    assert _gem.load_json_safe(str(tmp_path / 'missing.json')) == []

def test_gem_load_json_safe_dict_returns_empty(tmp_path):
    p = tmp_path / 'f.json'
    p.write_text('{}')
    assert _gem.load_json_safe(str(p)) == []

def test_gem_compute_diff_no_change():
    upsert, delete = _gem.compute_diff(GEM_SAMPLE, GEM_SAMPLE, lambda r: r['name'])
    assert upsert == [] and delete == []

def test_gem_compute_diff_new_row():
    new_row = {'name': 'New Gem', 'weight': 0.5, 'value': 100, 'capacity': 1000,
               'trappable_souls': 'All souls.'}
    upsert, delete = _gem.compute_diff(GEM_SAMPLE, GEM_SAMPLE + [new_row], lambda r: r['name'])
    assert len(upsert) == 1 and upsert[0]['name'] == 'New Gem'

def test_gem_subprocess_creates_json(tmp_path):
    infile = make_gem_raw(tmp_path)
    outfile = str(tmp_path / 'out.json')
    result = run_gem([infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 3

def test_gem_subprocess_creates_diff_files(tmp_path):
    infile = make_gem_raw(tmp_path)
    outfile = str(tmp_path / 'out.json')
    run_gem([infile, outfile])
    assert (tmp_path / 'out.upsert.json').exists()
    assert (tmp_path / 'out.delete.json').exists()

def test_gem_subprocess_no_change_exits_zero(tmp_path):
    infile = make_gem_raw(tmp_path)
    outfile = str(tmp_path / 'out.json')
    run_gem([infile, outfile])
    result = run_gem([infile, outfile])
    assert result.returncode == 0
    assert 'No changes' in result.stderr

def test_gem_subprocess_bad_input_exits_nonzero(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('bad|line\n')
    result = run_gem([str(bad), str(tmp_path / 'out.json')])
    assert result.returncode != 0


# ===========================================================================
# creature_souls parser
# ===========================================================================

def test_souls_parse_correct_count(tmp_path):
    assert len(_souls.parse(make_souls_raw(tmp_path))) == 4

def test_souls_parse_fields(tmp_path):
    rows = _souls.parse(make_souls_raw(tmp_path))
    assert rows[0] == {'creature': 'Chicken', 'soul_size': 'petty'}
    assert rows[3] == {'creature': 'Nord', 'soul_size': 'black'}

def test_souls_parse_wrong_fields_raises(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('OnlyOne\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        _souls.parse(str(bad))

def test_souls_parse_invalid_size_raises(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('Chicken|gigantic\n')
    with pytest.raises(ValueError, match='unknown soul_size'):
        _souls.parse(str(bad))

def test_souls_parse_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        _souls.parse(str(tmp_path / 'missing.txt'))

def test_souls_load_json_safe_missing_returns_empty(tmp_path):
    assert _souls.load_json_safe(str(tmp_path / 'missing.json')) == []

def test_souls_compute_diff_composite_key():
    extra = {'creature': 'Dragon', 'soul_size': 'grand'}
    upsert, delete = _souls.compute_diff(SOULS_SAMPLE, SOULS_SAMPLE + [extra], _souls._key)
    assert len(upsert) == 1 and upsert[0]['creature'] == 'Dragon'
    assert delete == []

def test_souls_compute_diff_deleted_row():
    upsert, delete = _souls.compute_diff(SOULS_SAMPLE, SOULS_SAMPLE[:3], _souls._key)
    assert len(delete) == 1 and delete[0]['creature'] == 'Nord'

def test_souls_subprocess_creates_json(tmp_path):
    infile = make_souls_raw(tmp_path)
    outfile = str(tmp_path / 'out.json')
    result = run_souls([infile, outfile])
    assert result.returncode == 0, result.stderr
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 4

def test_souls_subprocess_no_change_exits_zero(tmp_path):
    infile = make_souls_raw(tmp_path)
    outfile = str(tmp_path / 'out.json')
    run_souls([infile, outfile])
    result = run_souls([infile, outfile])
    assert result.returncode == 0
    assert 'No changes' in result.stderr

def test_souls_subprocess_bad_size_exits_nonzero(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('Dragon|colossal\n')
    result = run_souls([str(bad), str(tmp_path / 'out.json')])
    assert result.returncode != 0
