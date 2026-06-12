"""Tests for Morrowind/enchanting/enchant_json/morrowind_parse_enchant_csv_to_json.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Morrowind/enchanting/enchant_json/morrowind_parse_enchant_csv_to_json.py",
    "mw_enchant_parse",
)
write_file = _mod.write_file
check_for_files = _mod.check_for_files
FILE_PREFIXES = _mod.FILE_PREFIXES  # ['armor', 'books', 'clothing', 'weapons']


# ---------------------------------------------------------------------------
# check_for_files
# ---------------------------------------------------------------------------

def test_check_for_files_all_present(tmp_path):
    for prefix in FILE_PREFIXES:
        (tmp_path / f"{prefix}.csv").write_text("ID,Name\n1,Test\n")
    assert check_for_files(str(tmp_path)) is True

def test_check_for_files_one_missing(tmp_path):
    # Create all except 'weapons'
    for prefix in FILE_PREFIXES[:-1]:
        (tmp_path / f"{prefix}.csv").write_text("ID,Name\n1,Test\n")
    assert check_for_files(str(tmp_path)) is False

def test_check_for_files_empty_dir_returns_false(tmp_path):
    assert check_for_files(str(tmp_path)) is False

def test_check_for_files_nonexistent_dir_returns_false():
    assert check_for_files("/nonexistent_dir_xyz/") is False


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

def test_write_file_creates_valid_json(tmp_path):
    outfile = str(tmp_path / "out.json")
    data = [{"ID": "armor_01", "Name": "Iron Cuirass"}]
    write_file(data, outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == data

def test_write_file_overwrites_existing_file(tmp_path):
    outfile = str(tmp_path / "out.json")
    write_file([{"a": 1}], outfile)
    write_file([{"b": 2}], outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == [{"b": 2}]

def test_write_file_bad_path_raises(tmp_path):
    with pytest.raises(OSError):
        write_file([], "/nonexistent_dir_xyz/out.json")
