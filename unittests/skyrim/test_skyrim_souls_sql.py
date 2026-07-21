"""Unit tests for create_or_update_skyrim_enchant_souls.py"""
import json
import sqlite3
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Skyrim" / "enchanting" / "creature_souls_sql"))
from create_or_update_skyrim_enchant_souls import TABLE_NAME, INDEX_NAME, main

SAMPLE_RECORDS = [
    {"name": "Chicken", "soul_size": 250},
    {"name": "Bear", "soul_size": 500},
    {"name": "Draugr Deathlord", "soul_size": 1000},
    {"name": "Draugr Deathlord", "soul_size": 2000},
    {"name": "Draugr Deathlord", "soul_size": 3000},
    {"name": "NPC", "soul_size": 3000},
]


@pytest.fixture()
def tmp_json(tmp_path):
    p = tmp_path / "sk_souls.json"
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


def test_integer_soul_size_column(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(f"SELECT soul_size FROM {TABLE_NAME}").fetchall()
    for (size,) in rows:
        assert isinstance(size, int)
    conn.close()


def test_multi_level_creature_stored(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    sizes = sorted([r[0] for r in conn.execute(
        f"SELECT soul_size FROM {TABLE_NAME} WHERE name='Draugr Deathlord'"
    ).fetchall()])
    assert sizes == [1000, 2000, 3000]
    conn.close()


def test_npc_entry_stored(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    npc = conn.execute(
        f"SELECT soul_size FROM {TABLE_NAME} WHERE name='NPC'"
    ).fetchone()
    assert npc is not None
    assert npc[0] == 3000
    conn.close()


def test_drop_recreate_replaces_old_schema(tmp_json, tmp_db):
    # Simulate old TEXT schema
    conn = sqlite3.connect(tmp_db)
    conn.execute(f"CREATE TABLE {TABLE_NAME} (name TEXT, soul_size TEXT)")
    conn.execute(f"INSERT INTO {TABLE_NAME} VALUES ('OldCreature', 'petty')")
    conn.commit()
    conn.close()
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    old = conn.execute(
        f"SELECT name FROM {TABLE_NAME} WHERE name='OldCreature'"
    ).fetchone()
    assert old is None
    conn.close()


def test_unique_index_created(tmp_json, tmp_db):
    sys.argv = ["", tmp_json, tmp_db]
    main()
    conn = sqlite3.connect(tmp_db)
    indexes = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()]
    assert INDEX_NAME in indexes
    conn.close()
