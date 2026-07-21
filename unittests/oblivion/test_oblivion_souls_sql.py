"""Unit tests for create_or_update_oblivion_enchant_souls.py"""
import json
import sqlite3
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Oblivion" / "enchanting" / "souls_sql"))
from create_or_update_oblivion_enchant_souls import TABLE_NAME, INDEX_NAME, main

SAMPLE_RECORDS = [
    {"name": "Deer", "soul_size": 150},
    {"name": "Scamp", "soul_size": 300},
    {"name": "Dremora", "soul_size": 1600},
    {"name": "NPC(any race)", "soul_size": 1600},
    {"name": "Vampire", "soul_size": 1600},
]


@pytest.fixture()
def tmp_json(tmp_path):
    p = tmp_path / "ob_souls.json"
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


def test_black_souls_stored(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    black = conn.execute(
        f"SELECT name FROM {TABLE_NAME} WHERE soul_size=1600 ORDER BY name"
    ).fetchall()
    names = [r[0] for r in black]
    assert "Dremora" in names
    assert "NPC(any race)" in names
    assert "Vampire" in names
    conn.close()


def test_integer_soul_size(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(f"SELECT soul_size FROM {TABLE_NAME}").fetchall()
    for (size,) in rows:
        assert isinstance(size, int)
    conn.close()


def test_full_replace_on_second_run(tmp_json, tmp_db, tmp_path):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    updated = [{"name": "Deer", "soul_size": 150}]
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
