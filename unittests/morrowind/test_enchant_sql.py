"""Subprocess tests for Morrowind/enchanting/enchant_sql/create_morrowind_enchant_tables.py.

Also tests the importable check_for_files function in that module.
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Morrowind/enchanting/enchant_sql/create_morrowind_enchant_tables.py",
    "mw_enchant_sql",
)
check_for_files = _mod.check_for_files
FILE_PREFIXES = _mod.FILE_PREFIXES  # ['armor','books','clothing','weapons','soul_gems','magic_effects','magic_schools']

SCRIPT = str(REPO_ROOT / "Morrowind/enchanting/enchant_sql/create_morrowind_enchant_tables.py")

SAMPLE_ITEM = [{"ID": "item_01", "Name": "Test Item", "Value": 100}]


def run_script(args):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True, text=True
    )


def make_json_dir(tmp_path, prefixes):
    """Create a dir containing one minimal JSON file per prefix."""
    for prefix in prefixes:
        (tmp_path / f"{prefix}.json").write_text(json.dumps(SAMPLE_ITEM))
    return str(tmp_path)


# ---------------------------------------------------------------------------
# check_for_files (importable function)
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
# create_morrowind_enchant_tables.py (subprocess)
# ---------------------------------------------------------------------------

def test_enchant_sql_creates_tables(tmp_path, tmp_db):
    json_dir = make_json_dir(tmp_path, FILE_PREFIXES)
    result = run_script([json_dir, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    for prefix in FILE_PREFIXES:
        assert f"morrowind_enchant_{prefix}" in tables

def test_enchant_sql_inserts_rows(tmp_path, tmp_db):
    json_dir = make_json_dir(tmp_path, FILE_PREFIXES)
    run_script([json_dir, tmp_db])
    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM morrowind_enchant_armor").fetchone()[0]
    conn.close()
    assert count == 1

def test_enchant_sql_missing_json_dir_exits_nonzero(tmp_db):
    result = run_script(["/nonexistent_dir_xyz/", tmp_db])
    assert result.returncode != 0
