"""Tests for TES/Oblivion/alchemy/apparatus_sql/create_or_update_oblivion_alchemy_apparatus.py"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "TES/Oblivion/alchemy/apparatus_sql/create_or_update_oblivion_alchemy_apparatus.py",
    "ob_apparatus_sql",
)
TABLE_NAME = _mod.TABLE_NAME

SAMPLE_RECORDS = [
    {"id": "00010604", "name": "Alembic", "grade": "Novice",
     "weight": 7.0, "cost": 50, "strength": 0.1},
    {"id": "0006E310", "name": "Alembic", "grade": "Apprentice",
     "weight": 7.25, "cost": 100, "strength": 0.25},
    {"id": "000C7968", "name": "Mortar & Pestle", "grade": "Novice",
     "weight": 1.0, "cost": 25, "strength": 0.1},
    {"id": "000105E3", "name": "Mortar & Pestle", "grade": "Novice",
     "weight": 1.0, "cost": 25, "strength": 0.1},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_script(tmp_db, json_path):
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Oblivion/alchemy/apparatus_sql/create_or_update_oblivion_alchemy_apparatus.py")
    return subprocess.run([_sys.executable, script, json_path, tmp_db],
                          capture_output=True, text=True)


def test_creates_table(tmp_db, make_json):
    result = _run_script(tmp_db, make_json(SAMPLE_RECORDS))
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    assert (TABLE_NAME,) in tables

def test_row_count(tmp_db, make_json):
    _run_script(tmp_db, make_json(SAMPLE_RECORDS))
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 4

def test_values(tmp_db, make_json):
    _run_script(tmp_db, make_json(SAMPLE_RECORDS))
    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT name, grade, weight, cost, strength FROM {TABLE_NAME} WHERE id = ?",
        ("00010604",)
    ).fetchone()
    conn.close()
    assert row == ("Alembic", "Novice", 7.0, 50, 0.1)

def test_cost_column_name(tmp_db, make_json):
    _run_script(tmp_db, make_json(SAMPLE_RECORDS))
    conn = sqlite3.connect(tmp_db)
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()]
    conn.close()
    assert "cost" in cols
    assert "value" not in cols

def test_idempotent(tmp_db, make_json):
    json_path = make_json(SAMPLE_RECORDS)
    _run_script(tmp_db, json_path)
    _run_script(tmp_db, json_path)
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 4

def test_unique_index_on_id(tmp_db, make_json):
    _run_script(tmp_db, make_json(SAMPLE_RECORDS))
    conn = sqlite3.connect(tmp_db)
    indexes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
        (TABLE_NAME,)
    ).fetchall()
    conn.close()
    assert any("apparatus" in str(idx) for idx in indexes)

def test_both_novice_mortars_stored(tmp_db, make_json):
    _run_script(tmp_db, make_json(SAMPLE_RECORDS))
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(
        f"SELECT id FROM {TABLE_NAME} WHERE name = ? AND grade = ?",
        ("Mortar & Pestle", "Novice")
    ).fetchall()
    conn.close()
    assert len(rows) == 2
    ids = {r[0] for r in rows}
    assert "000C7968" in ids
    assert "000105E3" in ids

def test_missing_json_exits_nonzero(tmp_db):
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Oblivion/alchemy/apparatus_sql/create_or_update_oblivion_alchemy_apparatus.py")
    result = subprocess.run(
        [_sys.executable, script, "/nonexistent/path.json", tmp_db],
        capture_output=True, text=True
    )
    assert result.returncode != 0

def test_strength_stored_correctly(tmp_db, make_json):
    records = [{"id": "0006EE64", "name": "Alembic", "grade": "Master",
                "weight": 8.0, "cost": 1000, "strength": 1.0}]
    _run_script(tmp_db, make_json(records))
    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT strength FROM {TABLE_NAME} WHERE id = ?", ("0006EE64",)
    ).fetchone()
    conn.close()
    assert row[0] == 1.0
