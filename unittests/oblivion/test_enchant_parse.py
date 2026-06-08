"""Tests for:
  - Oblivion/enchanting/enchant_parse/oblivion_parse_csv_to_json.py
  - Oblivion/enchanting/enchant_parse/MGEF.py
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_csv_mod = load_module(
    "Oblivion/enchanting/enchant_parse/oblivion_parse_csv_to_json.py",
    "ob_enchant_parse",
)
write_file = _csv_mod.write_file
check_for_files = _csv_mod.check_for_files
FILE_PREFIXES = _csv_mod.FILE_PREFIXES  # ['soul_gems']

_mgef_mod = load_module(
    "Oblivion/enchanting/enchant_parse/MGEF.py",
    "ob_mgef",
)
MGEF = _mgef_mod.MGEF
mgef_write_file = _mgef_mod.write_file

SOUL_GEM_CSV = (
    "SLGM,Oblivion.esm,0x000193,AzurasStar,0.700000,2500\n"
    "SLGM,Oblivion.esm,0x000192,BlackSoulGem,0.500000,500\n"
)


# ---------------------------------------------------------------------------
# check_for_files (oblivion_parse_csv_to_json)
# ---------------------------------------------------------------------------

def test_check_for_files_soul_gems_present(tmp_path):
    (tmp_path / "soul_gems.csv").write_text(SOUL_GEM_CSV)
    assert check_for_files(str(tmp_path)) is True

def test_check_for_files_soul_gems_missing(tmp_path):
    assert check_for_files(str(tmp_path)) is False

def test_check_for_files_nonexistent_dir_returns_false():
    assert check_for_files("/nonexistent_dir_xyz/") is False


# ---------------------------------------------------------------------------
# write_file (oblivion_parse_csv_to_json)
# ---------------------------------------------------------------------------

def test_write_file_creates_valid_json(tmp_path):
    outfile = str(tmp_path / "out.json")
    data = [{"Editor ID": "AzurasStar", "Weight": "0.700000", "Value": "2500"}]
    write_file(data, outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == data

def test_write_file_overwrites_existing_file(tmp_path):
    outfile = str(tmp_path / "out.json")
    write_file([{"a": 1}], outfile)
    write_file([{"b": 2}], outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == [{"b": 2}]

def test_write_file_bad_path_raises():
    with pytest.raises(OSError):
        write_file([], "/nonexistent_dir_xyz/out.json")


# ---------------------------------------------------------------------------
# MGEF data structure
# ---------------------------------------------------------------------------

def test_mgef_is_dict():
    assert isinstance(MGEF, dict)

def test_mgef_has_entries():
    assert len(MGEF) > 0

def test_mgef_keys_are_four_char_strings():
    for key in MGEF:
        assert isinstance(key, str)
        assert len(key) == 4

def test_mgef_values_are_three_element_lists():
    for key, val in MGEF.items():
        assert isinstance(val, list), f"Expected list for {key}"
        assert len(val) == 3, f"Expected 3 elements for {key}"

def test_mgef_value_structure_school_name_cost():
    for key, val in MGEF.items():
        school, name, cost = val
        assert isinstance(school, int), f"School should be int for {key}"
        assert isinstance(name, str), f"Name should be str for {key}"
        assert isinstance(cost, (int, float)), f"Cost should be numeric for {key}"

def test_mgef_known_entry_absorb_attribute():
    assert "ABAT" in MGEF
    assert MGEF["ABAT"][1] == "Absorb Attribute"

def test_mgef_unknown_key_raises_key_error():
    with pytest.raises(KeyError):
        _ = MGEF["XXXX"]


# ---------------------------------------------------------------------------
# write_file (MGEF.py)
# ---------------------------------------------------------------------------

def test_mgef_write_file_creates_valid_json(tmp_path):
    outfile = str(tmp_path / "mgef.json")
    sample = {"ABAT": [5, "Absorb Attribute", 0.95]}
    mgef_write_file(sample, outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == sample

def test_mgef_write_file_bad_path_raises():
    with pytest.raises(OSError):
        mgef_write_file({}, "/nonexistent_dir_xyz/mgef.json")
