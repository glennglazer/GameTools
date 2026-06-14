"""Tests for Morrowind/enchanting/enchant_sql/create_or_update_morrowind_enchant_tables.py."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Morrowind/enchanting/enchant_sql/create_or_update_morrowind_enchant_tables.py",
    "mw_enchant_sql",
)
check_for_files = _mod.check_for_files
load_diff_file = _mod.load_diff_file
apply_deletes = _mod.apply_deletes
FILE_PREFIXES = _mod.FILE_PREFIXES

SCRIPT = str(REPO_ROOT / "Morrowind/enchanting/enchant_sql/create_or_update_morrowind_enchant_tables.py")

SAMPLE_ITEM = [{"ID": "item_01", "Name": "Iron Cuirass", "Value": "100"}]
SAMPLE_ITEM_2 = [{"ID": "item_02", "Name": "Silver Cuirass", "Value": "500"}]


def run_script(args):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True, text=True,
    )


def make_json_dir(tmp_path, prefixes, data=None):
    """Create a directory with one JSON file per prefix."""
    for prefix in prefixes:
        (tmp_path / f"{prefix}.json").write_text(json.dumps(data or SAMPLE_ITEM))
    return str(tmp_path)


def write_diff_pair(directory: Path, stem: str, upsert_data, delete_data) -> tuple:
    u = directory / f"{stem}.upsert.json"
    d = directory / f"{stem}.delete.json"
    u.write_text(json.dumps(upsert_data))
    d.write_text(json.dumps(delete_data))
    return str(u), str(d)


# ---------------------------------------------------------------------------
# Importable unit tests
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

def test_apply_deletes_removes_by_id(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE t (ID TEXT)")
    conn.execute("INSERT INTO t VALUES ('item_01')")
    conn.execute("INSERT INTO t VALUES ('item_02')")
    conn.commit()
    apply_deletes(conn.cursor(), 't', [{"ID": "item_01"}], 'ID')
    conn.commit()
    rows = [r[0] for r in conn.execute("SELECT ID FROM t").fetchall()]
    assert rows == ['item_02']
    conn.close()

def test_apply_deletes_no_match_is_noop(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE t (ID TEXT)")
    conn.execute("INSERT INTO t VALUES ('item_01')")
    conn.commit()
    apply_deletes(conn.cursor(), 't', [{"ID": "item_99"}], 'ID')
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    conn.close()


# ---------------------------------------------------------------------------
# Subprocess: full flow
# ---------------------------------------------------------------------------

def test_enchant_no_diff_files_is_noop(tmp_path, tmp_db):
    make_json_dir(tmp_path, FILE_PREFIXES)
    result = run_script([str(tmp_path), tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert not any(f"morrowind_enchant_{p}" in tables for p in FILE_PREFIXES)

def test_enchant_creates_tables_on_first_run(tmp_path, tmp_db):
    make_json_dir(tmp_path, FILE_PREFIXES)
    for prefix in FILE_PREFIXES:
        write_diff_pair(tmp_path, prefix, SAMPLE_ITEM, {})
    result = run_script([str(tmp_path), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    for prefix in FILE_PREFIXES:
        assert f"morrowind_enchant_{prefix}" in tables

def test_enchant_inserts_rows_on_first_run(tmp_path, tmp_db):
    make_json_dir(tmp_path, FILE_PREFIXES)
    for prefix in FILE_PREFIXES:
        write_diff_pair(tmp_path, prefix, SAMPLE_ITEM, {})
    run_script([str(tmp_path), tmp_db])
    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM morrowind_enchant_armor").fetchone()[0]
    conn.close()
    assert count == 1

def test_enchant_upsert_adds_row(tmp_path, tmp_db):
    make_json_dir(tmp_path, FILE_PREFIXES)
    # First run
    for prefix in FILE_PREFIXES:
        write_diff_pair(tmp_path, prefix, SAMPLE_ITEM, {})
    run_script([str(tmp_path), tmp_db])
    # Second run: upsert new armor row
    write_diff_pair(tmp_path, "armor", SAMPLE_ITEM_2, {})
    result = run_script([str(tmp_path), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM morrowind_enchant_armor").fetchone()[0]
    conn.close()
    assert count == 2

def test_enchant_delete_removes_row(tmp_path, tmp_db):
    make_json_dir(tmp_path, FILE_PREFIXES)
    for prefix in FILE_PREFIXES:
        write_diff_pair(tmp_path, prefix, SAMPLE_ITEM, {})
    run_script([str(tmp_path), tmp_db])
    # Delete the armor row
    write_diff_pair(tmp_path, "armor", {}, [{"ID": "item_01"}])
    result = run_script([str(tmp_path), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM morrowind_enchant_armor").fetchone()[0]
    conn.close()
    assert count == 0

def test_enchant_diff_files_removed_after_success(tmp_path, tmp_db):
    make_json_dir(tmp_path, FILE_PREFIXES)
    paths = []
    for prefix in FILE_PREFIXES:
        u, d = write_diff_pair(tmp_path, prefix, SAMPLE_ITEM, {})
        paths.extend([u, d])
    run_script([str(tmp_path), tmp_db])
    for p in paths:
        assert not Path(p).exists(), f"Expected {p} to be removed"

def test_enchant_missing_json_dir_exits_nonzero(tmp_db):
    result = run_script(["/nonexistent_dir_xyz/", tmp_db])
    assert result.returncode != 0

def test_enchant_bad_upsert_json_exits_nonzero(tmp_path, tmp_db):
    make_json_dir(tmp_path, FILE_PREFIXES)
    (tmp_path / "armor.upsert.json").write_text("not json {{")
    (tmp_path / "armor.delete.json").write_text("{}")
    result = run_script([str(tmp_path), tmp_db])
    assert result.returncode != 0
