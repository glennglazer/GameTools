"""Tests for TES/Skyrim/alchemy/perks_json/skyrim_parse_perks_to_json.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

SCRIPT = str(REPO_ROOT / 'TES/Skyrim/alchemy/perks_json/skyrim_parse_perks_to_json.py')

_mod = load_module(
    'TES/Skyrim/alchemy/perks_json/skyrim_parse_perks_to_json.py',
    'sk_perks_parse',
)
parse           = _mod.parse
load_json_safe  = _mod.load_json_safe
compute_diff    = _mod.compute_diff
write_file      = _mod.write_file
write_diff_files = _mod.write_diff_files

SAMPLE_RAW = (
    "Alchemist (1/5)|0|None|Potions and poisons are 20% stronger.\n"
    "Alchemist (2/5)|20|Alchemist (1/5)|Potions and poisons are 40% stronger.\n"
    "Physician|20|Alchemist (1/5)|Potions you mix that restore health or stamina are 25% more powerful.\n"
)

SAMPLE_PERKS = [
    {'name': 'Alchemist (1/5)', 'skill_level': 0, 'prerequisite': 'None',
     'description': 'Potions and poisons are 20% stronger.'},
    {'name': 'Alchemist (2/5)', 'skill_level': 20, 'prerequisite': 'Alchemist (1/5)',
     'description': 'Potions and poisons are 40% stronger.'},
    {'name': 'Physician', 'skill_level': 20, 'prerequisite': 'Alchemist (1/5)',
     'description': 'Potions you mix that restore health or stamina are 25% more powerful.'},
]


def make_raw_file(tmp_path, content=SAMPLE_RAW):
    p = tmp_path / 'skyrim_alchemy_perks_raw.txt'
    p.write_text(content)
    return str(p)


def run_script(args):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True, text=True,
    )


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------

def test_parse_returns_correct_count(tmp_path):
    assert len(parse(make_raw_file(tmp_path))) == 3

def test_parse_first_row_fields(tmp_path):
    perks = parse(make_raw_file(tmp_path))
    assert perks[0]['name'] == 'Alchemist (1/5)'
    assert perks[0]['skill_level'] == 0
    assert perks[0]['prerequisite'] == 'None'
    assert perks[0]['description'] == 'Potions and poisons are 20% stronger.'

def test_parse_skill_level_is_int(tmp_path):
    perks = parse(make_raw_file(tmp_path))
    assert isinstance(perks[0]['skill_level'], int)

def test_parse_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        parse(str(tmp_path / 'nonexistent.txt'))

def test_parse_wrong_field_count_raises(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('TooFew|fields\n')
    with pytest.raises(ValueError, match='pipe-separated'):
        parse(str(bad))

def test_parse_non_integer_skill_level_raises(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('Alchemist (1/5)|NOTINT|None|Some description.\n')
    with pytest.raises(ValueError, match='not an integer'):
        parse(str(bad))


# ---------------------------------------------------------------------------
# load_json_safe
# ---------------------------------------------------------------------------

def test_load_json_safe_missing_file_returns_empty(tmp_path):
    assert load_json_safe(str(tmp_path / 'missing.json')) == []

def test_load_json_safe_invalid_json_returns_empty(tmp_path):
    p = tmp_path / 'bad.json'
    p.write_text('{not valid json')
    assert load_json_safe(str(p)) == []

def test_load_json_safe_dict_returns_empty(tmp_path):
    p = tmp_path / 'dict.json'
    p.write_text('{}')
    assert load_json_safe(str(p)) == []

def test_load_json_safe_valid_list(tmp_path):
    p = tmp_path / 'ok.json'
    p.write_text(json.dumps(SAMPLE_PERKS))
    assert load_json_safe(str(p)) == SAMPLE_PERKS


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------

def test_compute_diff_no_change():
    upsert, delete = compute_diff(SAMPLE_PERKS, SAMPLE_PERKS, lambda r: r['name'])
    assert upsert == []
    assert delete == []

def test_compute_diff_new_row():
    new_perk = {'name': 'Purity', 'skill_level': 100, 'prerequisite': 'Snakeblood',
                'description': 'Removes negative effects.'}
    upsert, delete = compute_diff(SAMPLE_PERKS, SAMPLE_PERKS + [new_perk], lambda r: r['name'])
    assert len(upsert) == 1
    assert upsert[0]['name'] == 'Purity'
    assert delete == []

def test_compute_diff_deleted_row():
    upsert, delete = compute_diff(SAMPLE_PERKS, SAMPLE_PERKS[:2], lambda r: r['name'])
    assert upsert == []
    assert len(delete) == 1
    assert delete[0]['name'] == 'Physician'

def test_compute_diff_changed_row():
    modified = [{**SAMPLE_PERKS[0], 'skill_level': 5}] + SAMPLE_PERKS[1:]
    upsert, delete = compute_diff(SAMPLE_PERKS, modified, lambda r: r['name'])
    assert len(upsert) == 1
    assert upsert[0]['skill_level'] == 5
    assert delete == []


# ---------------------------------------------------------------------------
# write_diff_files
# ---------------------------------------------------------------------------

def test_write_diff_files_creates_both_files(tmp_path):
    outfile = str(tmp_path / 'perks.json')
    write_diff_files(outfile, SAMPLE_PERKS[:1], SAMPLE_PERKS[1:2])
    assert (tmp_path / 'perks.upsert.json').exists()
    assert (tmp_path / 'perks.delete.json').exists()

def test_write_diff_files_empty_upsert_writes_sentinel(tmp_path):
    outfile = str(tmp_path / 'perks.json')
    write_diff_files(outfile, [], [])
    upsert = json.loads((tmp_path / 'perks.upsert.json').read_text())
    assert upsert == {}

def test_write_diff_files_bad_path_raises():
    with pytest.raises(OSError):
        write_diff_files('/nonexistent_dir_xyz/perks.json', [], [])


# ---------------------------------------------------------------------------
# Subprocess: full flow
# ---------------------------------------------------------------------------

def test_subprocess_produces_json_file(tmp_path):
    infile = make_raw_file(tmp_path)
    outfile = str(tmp_path / 'perks.json')
    result = run_script([infile, outfile])
    assert result.returncode == 0, result.stderr
    assert Path(outfile).exists()
    data = json.loads(Path(outfile).read_text())
    assert len(data) == 3

def test_subprocess_produces_diff_files(tmp_path):
    infile = make_raw_file(tmp_path)
    outfile = str(tmp_path / 'perks.json')
    run_script([infile, outfile])
    assert (tmp_path / 'perks.upsert.json').exists()
    assert (tmp_path / 'perks.delete.json').exists()

def test_subprocess_no_change_exits_zero(tmp_path):
    infile = make_raw_file(tmp_path)
    outfile = str(tmp_path / 'perks.json')
    run_script([infile, outfile])
    result = run_script([infile, outfile])
    assert result.returncode == 0
    assert 'No changes' in result.stderr

def test_subprocess_missing_input_exits_nonzero(tmp_path):
    result = run_script([str(tmp_path / 'missing.txt'), str(tmp_path / 'out.json')])
    assert result.returncode != 0

def test_subprocess_invalid_raw_exits_nonzero(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('only|three|fields\n')
    result = run_script([str(bad), str(tmp_path / 'out.json')])
    assert result.returncode != 0
