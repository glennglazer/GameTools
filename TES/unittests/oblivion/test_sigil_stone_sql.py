"""Unit tests for create_or_update_oblivion_sigil_stone.py"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent /
                       "TES" / "Oblivion" / "enchanting" / "sigil_stone_sql"))
from create_or_update_oblivion_sigil_stone import _upsert_table, STONES_TABLE, WEAPONS_TABLE, ARMOR_TABLE

STONES_SAMPLE = [
    {"form_id": "00041FB1", "weapon_effect": "Absorb Agility", "armor_effect": "Fortify Agility"},
    {"form_id": "00041FB2", "weapon_effect": "Absorb Agility", "armor_effect": "Fortify Agility"},
]

WEAPONS_SAMPLE = [
    {"form_id": "00041FB1",
     "descendent_magnitude": 5,  "descendent_charges": 40,
     "subjacent_magnitude": None, "subjacent_charges": None,
     "latent_magnitude": None,    "latent_charges": None,
     "ascendent_magnitude": None, "ascendent_charges": None,
     "transcendent_magnitude": None, "transcendent_charges": None},
    {"form_id": "00041FB2",
     "descendent_magnitude": None, "descendent_charges": None,
     "subjacent_magnitude": 10,  "subjacent_charges": 35,
     "latent_magnitude": None,   "latent_charges": None,
     "ascendent_magnitude": None,"ascendent_charges": None,
     "transcendent_magnitude": None, "transcendent_charges": None},
]

ARMOR_SAMPLE = [
    {"form_id": "00041FB1",
     "descendent_magnitude": 7,
     "subjacent_magnitude": None,
     "latent_magnitude": None,
     "ascendent_magnitude": None,
     "transcendent_magnitude": None},
    {"form_id": "00041FB2",
     "descendent_magnitude": None,
     "subjacent_magnitude": 8,
     "latent_magnitude": None,
     "ascendent_magnitude": None,
     "transcendent_magnitude": None},
]

NIGHT_EYE_ARMOR = [
    {"form_id": "00042083",
     "descendent_magnitude": None,
     "subjacent_magnitude": None,
     "latent_magnitude": None,
     "ascendent_magnitude": None,
     "transcendent_magnitude": None},
]


def test_stones_table_created():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", STONES_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{STONES_TABLE} ON {STONES_TABLE} (form_id)")
    rows = conn.execute(f"SELECT * FROM {STONES_TABLE}").fetchall()
    assert len(rows) == 2
    conn.close()


def test_stones_columns():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", STONES_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{STONES_TABLE} ON {STONES_TABLE} (form_id)")
    cols = [d[0] for d in conn.execute(f"SELECT * FROM {STONES_TABLE}").description]
    assert "form_id" in cols
    assert "weapon_effect" in cols
    assert "armor_effect" in cols
    conn.close()


def test_stones_values():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", STONES_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{STONES_TABLE} ON {STONES_TABLE} (form_id)")
    row = conn.execute(
        f"SELECT weapon_effect, armor_effect FROM {STONES_TABLE} WHERE form_id='00041FB1'"
    ).fetchone()
    assert row == ("Absorb Agility", "Fortify Agility")
    conn.close()


def test_weapons_table_created():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, WEAPONS_TABLE, f"idx_{WEAPONS_TABLE}", WEAPONS_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{WEAPONS_TABLE} ON {WEAPONS_TABLE} (form_id)")
    rows = conn.execute(f"SELECT * FROM {WEAPONS_TABLE}").fetchall()
    assert len(rows) == 2
    conn.close()


def test_weapons_descendent_populated():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, WEAPONS_TABLE, f"idx_{WEAPONS_TABLE}", WEAPONS_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{WEAPONS_TABLE} ON {WEAPONS_TABLE} (form_id)")
    row = conn.execute(
        f"SELECT descendent_magnitude, descendent_charges FROM {WEAPONS_TABLE} WHERE form_id='00041FB1'"
    ).fetchone()
    assert row == (5, 40)
    conn.close()


def test_weapons_other_levels_null():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, WEAPONS_TABLE, f"idx_{WEAPONS_TABLE}", WEAPONS_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{WEAPONS_TABLE} ON {WEAPONS_TABLE} (form_id)")
    row = conn.execute(
        f"SELECT subjacent_magnitude, latent_magnitude, ascendent_magnitude, transcendent_magnitude "
        f"FROM {WEAPONS_TABLE} WHERE form_id='00041FB1'"
    ).fetchone()
    assert all(v is None for v in row)
    conn.close()


def test_armor_table_created():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, ARMOR_TABLE, f"idx_{ARMOR_TABLE}", ARMOR_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{ARMOR_TABLE} ON {ARMOR_TABLE} (form_id)")
    rows = conn.execute(f"SELECT * FROM {ARMOR_TABLE}").fetchall()
    assert len(rows) == 2
    conn.close()


def test_armor_descendent_populated():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, ARMOR_TABLE, f"idx_{ARMOR_TABLE}", ARMOR_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{ARMOR_TABLE} ON {ARMOR_TABLE} (form_id)")
    val = conn.execute(
        f"SELECT descendent_magnitude FROM {ARMOR_TABLE} WHERE form_id='00041FB1'"
    ).fetchone()[0]
    assert val == 7
    conn.close()


def test_armor_other_levels_null():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, ARMOR_TABLE, f"idx_{ARMOR_TABLE}", ARMOR_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{ARMOR_TABLE} ON {ARMOR_TABLE} (form_id)")
    row = conn.execute(
        f"SELECT subjacent_magnitude, latent_magnitude, ascendent_magnitude, transcendent_magnitude "
        f"FROM {ARMOR_TABLE} WHERE form_id='00041FB1'"
    ).fetchone()
    assert all(v is None for v in row)
    conn.close()


def test_night_eye_armor_all_null():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, ARMOR_TABLE, f"idx_{ARMOR_TABLE}", NIGHT_EYE_ARMOR,
                  f"CREATE UNIQUE INDEX idx_{ARMOR_TABLE} ON {ARMOR_TABLE} (form_id)")
    row = conn.execute(f"SELECT * FROM {ARMOR_TABLE} WHERE form_id='00042083'").fetchone()
    # form_id is first column; all magnitude columns should be NULL
    assert row[0] == "00042083"
    assert all(v is None for v in row[1:])
    conn.close()


def test_upsert_replaces_on_second_run():
    conn = sqlite3.connect(":memory:")
    index_sql = f"CREATE UNIQUE INDEX idx_{STONES_TABLE} ON {STONES_TABLE} (form_id)"
    _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", STONES_SAMPLE, index_sql)
    # Run again with different effect names
    updated = [
        {"form_id": "00041FB1", "weapon_effect": "NEW_EFFECT", "armor_effect": "NEW_ARMOR"},
        {"form_id": "00041FB2", "weapon_effect": "NEW_EFFECT", "armor_effect": "NEW_ARMOR"},
    ]
    _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", updated, index_sql)
    row = conn.execute(
        f"SELECT weapon_effect FROM {STONES_TABLE} WHERE form_id='00041FB1'"
    ).fetchone()
    assert row[0] == "NEW_EFFECT"
    total = conn.execute(f"SELECT COUNT(*) FROM {STONES_TABLE}").fetchone()[0]
    assert total == 2
    conn.close()


def test_unique_index_created():
    conn = sqlite3.connect(":memory:")
    _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", STONES_SAMPLE,
                  f"CREATE UNIQUE INDEX idx_{STONES_TABLE} ON {STONES_TABLE} (form_id)")
    idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (f"idx_{STONES_TABLE}",)
    ).fetchone()
    assert idx is not None
    conn.close()


def test_join_stones_to_weapon_magnitudes():
    """Verify that JOINing stones + weapon_magnitudes on form_id returns the right magnitude."""
    conn = sqlite3.connect(":memory:")
    index_sql_s = f"CREATE UNIQUE INDEX idx_{STONES_TABLE} ON {STONES_TABLE} (form_id)"
    index_sql_w = f"CREATE UNIQUE INDEX idx_{WEAPONS_TABLE} ON {WEAPONS_TABLE} (form_id)"
    _upsert_table(conn, STONES_TABLE, f"idx_{STONES_TABLE}", STONES_SAMPLE, index_sql_s)
    _upsert_table(conn, WEAPONS_TABLE, f"idx_{WEAPONS_TABLE}", WEAPONS_SAMPLE, index_sql_w)
    row = conn.execute(
        f"SELECT s.weapon_effect, w.descendent_magnitude "
        f"FROM {STONES_TABLE} s JOIN {WEAPONS_TABLE} w ON s.form_id = w.form_id "
        f"WHERE s.form_id = '00041FB1'"
    ).fetchone()
    assert row == ("Absorb Agility", 5)
    conn.close()
