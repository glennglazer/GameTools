"""Integration tests for TES/Oblivion/enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py"""
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

SCRIPT = str(REPO_ROOT / "TES/Oblivion/enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py")

_mod = load_module(
    "TES/Oblivion/enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py",
    "ob_enchant_sql",
)
read_db_rows = _mod.read_db_rows
TABLE_NAME = _mod.TABLE_NAME

SAMPLE_CSV = (
    "SLGM,Oblivion.esm,0x000193,AzurasStar,0.700000,2500\n"
    "SLGM,Oblivion.esm,0x000192,BlackSoulGem,0.500000,500\n"
)


def make_csv(tmp_path, content=SAMPLE_CSV):
    p = tmp_path / "soul_gems.csv"
    p.write_text(content)
    return str(p)


def run_script(args):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True, text=True,
    )


# ---------------------------------------------------------------------------
# read_db_rows (integration — real SQLite)
# ---------------------------------------------------------------------------

def test_read_db_rows_returns_none_when_table_absent(tmp_db):
    conn = sqlite3.connect(tmp_db)
    assert read_db_rows(conn) is None
    conn.close()

def test_read_db_rows_returns_empty_list_for_empty_table(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        f"CREATE TABLE {TABLE_NAME} (ID TEXT, object_index TEXT, weight REAL, value INTEGER)"
    )
    conn.commit()
    assert read_db_rows(conn) == []
    conn.close()

def test_read_db_rows_returns_sorted_rows(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        f"CREATE TABLE {TABLE_NAME} (ID TEXT, object_index TEXT, weight REAL, value INTEGER)"
    )
    conn.execute(f"INSERT INTO {TABLE_NAME} VALUES ('ZZ', '0x1', 0.1, 1)")
    conn.execute(f"INSERT INTO {TABLE_NAME} VALUES ('AA', '0x2', 0.2, 2)")
    conn.commit()
    rows = read_db_rows(conn)
    conn.close()
    assert rows[0]['ID'] == 'AA'
    assert rows[1]['ID'] == 'ZZ'


# ---------------------------------------------------------------------------
# Subprocess: full flow
# ---------------------------------------------------------------------------

def test_first_run_creates_table(tmp_path, tmp_db):
    result = run_script([make_csv(tmp_path), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    names = [r[0] for r in conn.execute(
        f"SELECT ID FROM {TABLE_NAME} ORDER BY ID"
    ).fetchall()]
    conn.close()
    assert names == ['AzurasStar', 'BlackSoulGem']

def test_first_run_row_count(tmp_path, tmp_db):
    run_script([make_csv(tmp_path), tmp_db])
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 2

def test_no_changes_exits_zero_with_message(tmp_path, tmp_db):
    p = make_csv(tmp_path)
    run_script([p, tmp_db])
    result = run_script([p, tmp_db])
    assert result.returncode == 0
    assert 'no changes' in result.stderr.lower()

def test_changes_update_table(tmp_path, tmp_db):
    p = make_csv(tmp_path)
    run_script([p, tmp_db])
    updated = SAMPLE_CSV + "SLGM,Oblivion.esm,0x000194,CommonSoulGem,0.300000,150\n"
    (tmp_path / "soul_gems.csv").write_text(updated)
    result = run_script([p, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 3

def test_changed_value_is_reflected(tmp_path, tmp_db):
    p = make_csv(tmp_path)
    run_script([p, tmp_db])
    updated = "SLGM,Oblivion.esm,0x000193,AzurasStar,0.700000,9999\n"
    (tmp_path / "soul_gems.csv").write_text(updated)
    result = run_script([p, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    val = conn.execute(
        f"SELECT value FROM {TABLE_NAME} WHERE ID='AzurasStar'"
    ).fetchone()[0]
    conn.close()
    assert val == 9999

def test_missing_csv_exits_nonzero(tmp_db):
    result = run_script(["/nonexistent_dir_xyz/soul_gems.csv", tmp_db])
    assert result.returncode != 0

def test_bad_db_path_exits_nonzero(tmp_path):
    result = run_script([make_csv(tmp_path), "/nonexistent_dir_xyz/db.sqlite3"])
    assert result.returncode != 0
