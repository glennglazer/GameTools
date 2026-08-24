"""Unit tests for Morrowind enchant SQL loader (check_for_files and load_diff_file only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_mod = load_module(
    "TES/Morrowind/enchanting/enchant_sql/create_or_update_morrowind_enchant_tables.py",
    "mw_enchant_sql",
)
check_for_files = _mod.check_for_files
load_diff_file = _mod.load_diff_file
FILE_PREFIXES = _mod.FILE_PREFIXES


# ---------------------------------------------------------------------------
# check_for_files (unit tests — filesystem only, no DB)
# ---------------------------------------------------------------------------

def test_check_for_files_all_present(tmp_path):
    for prefix in FILE_PREFIXES:
        (tmp_path / f"{prefix}.json").write_text("[]")
    assert check_for_files(str(tmp_path)) is True

def test_check_for_files_one_missing(tmp_path):
    for prefix in FILE_PREFIXES[:-1]:
        (tmp_path / f"{prefix}.json").write_text("[]")
    assert check_for_files(str(tmp_path)) is False

def test_check_for_files_empty_dir_returns_false(tmp_path):
    assert check_for_files(str(tmp_path)) is False

def test_check_for_files_nonexistent_dir_returns_false():
    assert check_for_files("/nonexistent_dir_xyz/") is False


# ---------------------------------------------------------------------------
# load_diff_file (unit tests — filesystem only, no DB)
# ---------------------------------------------------------------------------

def test_load_diff_file_missing_returns_false(tmp_path):
    data, found = load_diff_file(str(tmp_path / "missing.json"))
    assert not found
    assert data == []

def test_load_diff_file_empty_sentinel_returns_empty_list(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}")
    data, found = load_diff_file(str(p))
    assert found
    assert data == []
