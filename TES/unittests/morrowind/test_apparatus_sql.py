"""Tests for TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py",
    "mw_apparatus_sql",
)
TABLE_NAME = _mod.TABLE_NAME

SAMPLE_RECORDS = [
    {"id": "apparatus_a_mortar_01", "name": "Apprentice's Mortar and Pestle",
     "weight": 5.0, "value": 100, "quality": 0.5},
    {"id": "apparatus_j_mortar_01", "name": "Journeyman's Mortar and Pestle",
     "weight": 4.0, "value": 400, "quality": 1.0},
    {"id": "apparatus_a_alembic_01", "name": "Apprentice's Alembic",
     "weight": 10.0, "value": 50, "quality": 0.5},
]


def _run(records, tmp_db):
    import pandas as pd
    import sqlite3 as sq3
    df = pd.DataFrame(records)
    ids = [(r["id"],) for r in records]
    conn = sq3.connect(tmp_db)
    cur = conn.cursor()
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
    table_exists = cur.fetchone() is not None
    if table_exists:
        cur.executemany(f"DELETE FROM {TABLE_NAME} WHERE id = ?", ids)
        conn.commit()
    df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)
    if not table_exists:
        cur.execute(f"CREATE UNIQUE INDEX idx_test ON {TABLE_NAME} (id)")
        conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_creates_table(tmp_db, make_json):
    json_path = make_json(SAMPLE_RECORDS)
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py")
    result = subprocess.run([_sys.executable, script, json_path, tmp_db],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    assert (TABLE_NAME,) in tables

def test_row_count(tmp_db, make_json):
    json_path = make_json(SAMPLE_RECORDS)
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py")
    subprocess.run([_sys.executable, script, json_path, tmp_db], capture_output=True)
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 3

def test_values(tmp_db, make_json):
    json_path = make_json(SAMPLE_RECORDS)
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py")
    subprocess.run([_sys.executable, script, json_path, tmp_db], capture_output=True)
    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT id, name, weight, value, quality FROM {TABLE_NAME} WHERE id = ?",
        ("apparatus_a_mortar_01",)
    ).fetchone()
    conn.close()
    assert row == ("apparatus_a_mortar_01", "Apprentice's Mortar and Pestle", 5.0, 100, 0.5)

def test_idempotent(tmp_db, make_json):
    json_path = make_json(SAMPLE_RECORDS)
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py")
    subprocess.run([_sys.executable, script, json_path, tmp_db], capture_output=True)
    subprocess.run([_sys.executable, script, json_path, tmp_db], capture_output=True)
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 3

def test_unique_index_created(tmp_db, make_json):
    json_path = make_json(SAMPLE_RECORDS)
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py")
    subprocess.run([_sys.executable, script, json_path, tmp_db], capture_output=True)
    conn = sqlite3.connect(tmp_db)
    indexes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
        (TABLE_NAME,)
    ).fetchall()
    conn.close()
    assert any("apparatus" in str(idx) for idx in indexes)

def test_missing_json_exits_nonzero(tmp_db):
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py")
    result = subprocess.run(
        [_sys.executable, script, "/nonexistent/path.json", tmp_db],
        capture_output=True, text=True
    )
    assert result.returncode != 0

def test_quality_stored_correctly(tmp_db, make_json):
    records = [{"id": "apparatus_g_mortar_01", "name": "Grandmaster's Mortar and Pestle",
                "weight": 2.0, "value": 4000, "quality": 1.5}]
    json_path = make_json(records)
    import subprocess, sys as _sys
    script = str(REPO_ROOT / "TES/Morrowind/alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py")
    subprocess.run([_sys.executable, script, json_path, tmp_db], capture_output=True)
    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT quality FROM {TABLE_NAME} WHERE id = ?",
        ("apparatus_g_mortar_01",)
    ).fetchone()
    conn.close()
    assert row[0] == 1.5
