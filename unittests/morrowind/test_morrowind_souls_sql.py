"""Unit tests for create_or_update_morrowind_enchant_souls.py"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Morrowind" / "enchanting" / "souls_sql"))
from create_or_update_morrowind_enchant_souls import TABLE_NAME, INDEX_NAME, main

SAMPLE_RECORDS = [
    {"name": "Mudcrab", "soul_size": 5},
    {"name": "Scamp", "soul_size": 10},
    {"name": "Scamp", "soul_size": 100},
    {"name": "Ancestor Ghost", "soul_size": 100},
]


@pytest.fixture()
def tmp_json(tmp_path):
    p = tmp_path / "souls.json"
    p.write_text(json.dumps(SAMPLE_RECORDS))
    return str(p)


@pytest.fixture()
def tmp_db(tmp_path):
    return str(tmp_path / "test.sqlite3")


def test_creates_table(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert TABLE_NAME in tables
    conn.close()


def test_row_count(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    n = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    assert n == len(SAMPLE_RECORDS)
    conn.close()


def test_integer_soul_size(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(f"SELECT soul_size FROM {TABLE_NAME}").fetchall()
    for (size,) in rows:
        assert isinstance(size, int)
    conn.close()


def test_composite_key_allows_same_name_different_size(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    scamps = conn.execute(
        f"SELECT soul_size FROM {TABLE_NAME} WHERE name='Scamp' ORDER BY soul_size"
    ).fetchall()
    assert [s for (s,) in scamps] == [10, 100]
    conn.close()


def test_full_replace_on_second_run(tmp_json, tmp_db, tmp_path):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    updated = [{"name": "Mudcrab", "soul_size": 5}]
    p2 = tmp_path / "updated.json"
    p2.write_text(json.dumps(updated))
    sys.argv = ["", str(p2), tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    n = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    assert n == 1
    conn.close()


def test_unique_index_created(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    indexes = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()]
    assert INDEX_NAME in indexes
    conn.close()
