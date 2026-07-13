"""Tests for TES/Oblivion/enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py"""
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
read_csv = _mod.read_csv
read_db_rows = _mod.read_db_rows
rows_match = _mod.rows_match
TABLE_NAME = _mod.TABLE_NAME

SAMPLE_CSV = (
    "SLGM,Oblivion.esm,0x000193,AzurasStar,0.700000,2500\n"
    "SLGM,Oblivion.esm,0x000192,BlackSoulGem,0.500000,500\n"
)
SAMPLE_ROWS = [
    {'ID': 'AzurasStar',   'object_index': '0x000193', 'weight': 0.7,  'value': 2500},
    {'ID': 'BlackSoulGem', 'object_index': '0x000192', 'weight': 0.5,  'value':  500},
]


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
# read_csv (importable unit tests)
# ---------------------------------------------------------------------------

def test_read_csv_returns_correct_row_count(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert len(rows) == 2

def test_read_csv_maps_columns_correctly(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert rows[0]['ID'] == 'AzurasStar'
    assert rows[0]['object_index'] == '0x000193'
    assert rows[0]['weight'] == 0.7
    assert rows[0]['value'] == 2500

def test_read_csv_weight_is_float(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert isinstance(rows[0]['weight'], float)

def test_read_csv_value_is_int(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert isinstance(rows[0]['value'], int)

def test_read_csv_missing_file_raises():
    with pytest.raises(OSError):
        read_csv("/nonexistent_dir_xyz/soul_gems.csv")

def test_read_csv_bad_value_field_raises(tmp_path):
    bad_csv = "SLGM,Oblivion.esm,0x000193,AzurasStar,0.700000,NOT_AN_INT\n"
    with pytest.raises(ValueError):
        read_csv(make_csv(tmp_path, bad_csv))


# ---------------------------------------------------------------------------
# read_db_rows (importable unit tests)
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
# rows_match (importable unit tests)
# ---------------------------------------------------------------------------

def test_rows_match_identical_data():
    db_rows = sorted(SAMPLE_ROWS, key=lambda r: r['ID'])
    assert rows_match(SAMPLE_ROWS, db_rows) is True

def test_rows_match_different_value():
    db_rows = [{'ID': 'AzurasStar', 'object_index': '0x000193', 'weight': 0.7, 'value': 9999}]
    assert rows_match(SAMPLE_ROWS[:1], db_rows) is False

def test_rows_match_different_row_count():
    db_rows = sorted(SAMPLE_ROWS, key=lambda r: r['ID'])
    assert rows_match(SAMPLE_ROWS[:1], db_rows) is False

def test_rows_match_empty_vs_empty():
    assert rows_match([], []) is True


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
