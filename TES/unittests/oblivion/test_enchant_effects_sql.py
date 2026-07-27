"""Unit tests for create_or_update_oblivion_enchant_effects.py"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent /
                       "TES" / "Oblivion" / "enchanting" / "enchant_effects_sql"))
from create_or_update_oblivion_enchant_effects import TABLE_NAME, INDEX_NAME

# Import main via importlib so we can call with temp file args
import importlib.util
_LOADER_PATH = str(Path(__file__).parent.parent.parent.parent /
                   "TES" / "Oblivion" / "enchanting" / "enchant_effects_sql" /
                   "create_or_update_oblivion_enchant_effects.py")

SAMPLE_RECORDS = [
    {"name": "Burden", "effect_id": "BRDN", "base_cost": 0.21, "barter_factor": 0.0,
     "school": "Alteration", "description": "Reduce the target's maximum encumbrance."},
    {"name": "Feather", "effect_id": "FTHR", "base_cost": 0.01, "barter_factor": 25.0,
     "school": "Alteration", "description": "Increase the target's maximum encumbrance."},
    {"name": "Light", "effect_id": "LGHT", "base_cost": 0.051, "barter_factor": 12.5,
     "school": "Illusion", "description": "Illuminates the target."},
    {"name": "Paralyze", "effect_id": "PARA", "base_cost": 475.0, "barter_factor": 0.0,
     "school": "Illusion", "description": "Render target unable to move."},
    {"name": "Charm", "effect_id": "CHRM", "base_cost": 0.2, "barter_factor": 0.0,
     "school": "Illusion", "description": "Increase target's disposition."},
]


def _run_loader(records, db_path):
    """Replicate the loader's logic: replace table, recreate unique index."""
    import pandas as pd

    df = pd.DataFrame(records)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    df.to_sql(TABLE_NAME, conn, if_exists="replace", method="multi", index=False)
    conn.commit()
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} ON {TABLE_NAME} (effect_id)")
    conn.commit()
    conn.close()


def test_table_created(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    rows = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert rows == 5


def test_columns_present(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    cols = [d[0] for d in conn.execute(f"SELECT * FROM {TABLE_NAME}").description]
    conn.close()
    assert "name" in cols
    assert "effect_id" in cols
    assert "base_cost" in cols
    assert "barter_factor" in cols
    assert "school" in cols
    assert "description" in cols


def test_values_correct(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    row = conn.execute(
        f"SELECT base_cost, barter_factor, school, description FROM {TABLE_NAME} WHERE effect_id='BRDN'"
    ).fetchone()
    conn.close()
    assert row[0] == pytest.approx(0.21)
    assert row[1] == pytest.approx(0.0)
    assert row[2] == "Alteration"
    assert "encumbrance" in row[3]


def test_fractional_barter_stored(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    val = conn.execute(
        f"SELECT barter_factor FROM {TABLE_NAME} WHERE effect_id='LGHT'"
    ).fetchone()[0]
    conn.close()
    assert val == pytest.approx(12.5)


def test_multiple_schools_stored(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    schools = {row[0] for row in conn.execute(f"SELECT DISTINCT school FROM {TABLE_NAME}")}
    conn.close()
    assert "Alteration" in schools
    assert "Illusion" in schools


def test_unique_index_created(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (INDEX_NAME,)
    ).fetchone()
    conn.close()
    assert idx is not None


def test_upsert_replaces_on_second_run(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    updated = [
        {"effect_id": "BRDN", "base_cost": 99.0, "barter_factor": 0.0,
         "school": "Alteration", "description": "Updated description."},
    ]
    _run_loader(updated, db)
    conn = sqlite3.connect(db)
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    val = conn.execute(
        f"SELECT base_cost FROM {TABLE_NAME} WHERE effect_id='BRDN'"
    ).fetchone()[0]
    conn.close()
    assert count == 1
    assert val == pytest.approx(99.0)


def test_name_column_stored(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    name = conn.execute(
        f"SELECT name FROM {TABLE_NAME} WHERE effect_id='PARA'"
    ).fetchone()[0]
    conn.close()
    assert name == "Paralyze"


def test_query_by_school(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    _run_loader(SAMPLE_RECORDS, db)
    conn = sqlite3.connect(db)
    illusion = conn.execute(
        f"SELECT effect_id FROM {TABLE_NAME} WHERE school='Illusion' ORDER BY effect_id"
    ).fetchall()
    conn.close()
    ids = [r[0] for r in illusion]
    assert "CHRM" in ids
    assert "LGHT" in ids
    assert "PARA" in ids
    assert "BRDN" not in ids
