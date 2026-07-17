"""Tests for homestead SQL loaders."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_build_sql = load_module(
    "TES/Skyrim/homestead/build_sql/create_or_update_skyrim_homestead_build.py",
    "sk_homestead_build_sql",
)
_excl_sql = load_module(
    "TES/Skyrim/homestead/exclusive_exterior_sql/create_or_update_skyrim_homestead_exclusive_exterior.py",
    "sk_homestead_excl_sql",
)
_cost_sql = load_module(
    "TES/Skyrim/homestead/steward_cost_sql/create_or_update_skyrim_homestead_steward_cost.py",
    "sk_homestead_cost_sql",
)

BUILD_TABLE = _build_sql.TABLE_NAME
EXCL_TABLE  = _excl_sql.TABLE_NAME
COST_TABLE  = _cost_sql.TABLE_NAME
MATERIAL_COLS = _build_sql.MATERIAL_COLS

BUILD_SCRIPT = str(REPO_ROOT / "TES/Skyrim/homestead/build_sql/create_or_update_skyrim_homestead_build.py")
EXCL_SCRIPT  = str(REPO_ROOT / "TES/Skyrim/homestead/exclusive_exterior_sql/create_or_update_skyrim_homestead_exclusive_exterior.py")
COST_SCRIPT  = str(REPO_ROOT / "TES/Skyrim/homestead/steward_cost_sql/create_or_update_skyrim_homestead_steward_cost.py")


def run(script, args):
    return subprocess.run([sys.executable, script] + args,
                          capture_output=True, text=True)


def _base_build_row(**kwargs):
    row = {"section": "Test Item", "location": "Small House", "stage": "Stage 1"}
    for col in MATERIAL_COLS:
        row[col] = 0
    row.update(kwargs)
    return row


BUILD_SAMPLE = [
    _base_build_row(section="House, Foundation", location="Small House",
                    stage="Stage 1", sawn_log=1, quarried_stone=10),
    _base_build_row(section="Barrel_1", location="Cellar_Containers",
                    stage=None, sawn_log=1, nails=1, iron_ingot=1),
    _base_build_row(section="Shrine of Akatosh", location="Cellar_Divine_Shrines",
                    stage=None, amulet_of_akatosh=1, iron_ingot=1,
                    flawless_amethyst=1, corundum_ingot=1),
]

EXCL_SAMPLE = [
    {"manor": "Lakeview Manor",  "exclusive_exterior": "Apiary"},
    {"manor": "Windstad Manor",  "exclusive_exterior": "Fish Hatchery"},
    {"manor": "Heljarchen Hall", "exclusive_exterior": "Grain Mill"},
]

COST_SAMPLE = [
    {"room": "Small House", "gold_cost": 1000},
    {"room": "Main Hall",   "gold_cost": 3500},
    {"room": "Greenhouse",  "gold_cost": 1500},
]


# ── build table ───────────────────────────────────────────────────────────────

@pytest.fixture
def build_json(tmp_path):
    p = tmp_path / "build.json"
    p.write_text(json.dumps(BUILD_SAMPLE))
    return str(p)


def test_build_table_created(build_json, tmp_db):
    result = run(BUILD_SCRIPT, [build_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()
    cur.execute(f"SELECT name FROM sqlite_master WHERE name='{BUILD_TABLE}'")
    assert cur.fetchone() is not None
    conn.close()


def test_build_table_row_count(build_json, tmp_db):
    run(BUILD_SCRIPT, [build_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {BUILD_TABLE}").fetchone()[0]
    conn.close()
    assert count == len(BUILD_SAMPLE)


def test_build_table_index_exists(build_json, tmp_db):
    run(BUILD_SCRIPT, [build_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type='index' AND name='idx_{BUILD_TABLE}'"
    )
    assert cur.fetchone() is not None
    conn.close()


def test_build_table_material_values(build_json, tmp_db):
    run(BUILD_SCRIPT, [build_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT sawn_log, quarried_stone FROM {BUILD_TABLE} "
        f"WHERE section='House, Foundation'"
    ).fetchone()
    conn.close()
    assert row == (1, 10)


def test_build_table_full_replace_on_rerun(build_json, tmp_db, tmp_path):
    run(BUILD_SCRIPT, [build_json, tmp_db])

    new_data = [_base_build_row(section="Only Row", location="Exterior", stage=None)]
    new_json = str(tmp_path / "new.json")
    Path(new_json).write_text(json.dumps(new_data))
    run(BUILD_SCRIPT, [new_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {BUILD_TABLE}").fetchone()[0]
    section = conn.execute(f"SELECT section FROM {BUILD_TABLE}").fetchone()[0]
    conn.close()
    assert count == 1
    assert section == "Only Row"


def test_build_bad_db_exits_nonzero(build_json):
    result = run(BUILD_SCRIPT, [build_json, "/nonexistent_xyz/db.sqlite3"])
    assert result.returncode != 0


# ── exclusive exterior table ──────────────────────────────────────────────────

@pytest.fixture
def excl_json(tmp_path):
    p = tmp_path / "excl.json"
    p.write_text(json.dumps(EXCL_SAMPLE))
    return str(p)


def test_excl_table_created(excl_json, tmp_db):
    result = run(EXCL_SCRIPT, [excl_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(f"SELECT name FROM sqlite_master WHERE name='{EXCL_TABLE}'")
    assert cur.fetchone() is not None
    conn.close()


def test_excl_table_row_count(excl_json, tmp_db):
    run(EXCL_SCRIPT, [excl_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {EXCL_TABLE}").fetchone()[0]
    conn.close()
    assert count == 3


def test_excl_table_data(excl_json, tmp_db):
    run(EXCL_SCRIPT, [excl_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    val = conn.execute(
        f"SELECT exclusive_exterior FROM {EXCL_TABLE} WHERE manor='Lakeview Manor'"
    ).fetchone()[0]
    conn.close()
    assert val == "Apiary"


def test_excl_table_full_replace_on_rerun(excl_json, tmp_db, tmp_path):
    run(EXCL_SCRIPT, [excl_json, tmp_db])

    new_data = [{"manor": "Only Manor", "exclusive_exterior": "Only Thing"}]
    new_json = str(tmp_path / "new.json")
    Path(new_json).write_text(json.dumps(new_data))
    run(EXCL_SCRIPT, [new_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {EXCL_TABLE}").fetchone()[0]
    conn.close()
    assert count == 1


def test_excl_bad_db_exits_nonzero(excl_json):
    result = run(EXCL_SCRIPT, [excl_json, "/nonexistent_xyz/db.sqlite3"])
    assert result.returncode != 0


# ── steward cost table ────────────────────────────────────────────────────────

@pytest.fixture
def cost_json(tmp_path):
    p = tmp_path / "cost.json"
    p.write_text(json.dumps(COST_SAMPLE))
    return str(p)


def test_cost_table_created(cost_json, tmp_db):
    result = run(COST_SCRIPT, [cost_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(f"SELECT name FROM sqlite_master WHERE name='{COST_TABLE}'")
    assert cur.fetchone() is not None
    conn.close()


def test_cost_table_row_count(cost_json, tmp_db):
    run(COST_SCRIPT, [cost_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {COST_TABLE}").fetchone()[0]
    conn.close()
    assert count == len(COST_SAMPLE)


def test_cost_table_gold_value(cost_json, tmp_db):
    run(COST_SCRIPT, [cost_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    val = conn.execute(
        f"SELECT gold_cost FROM {COST_TABLE} WHERE room='Main Hall'"
    ).fetchone()[0]
    conn.close()
    assert val == 3500


def test_cost_table_full_replace_on_rerun(cost_json, tmp_db, tmp_path):
    run(COST_SCRIPT, [cost_json, tmp_db])

    new_data = [{"room": "Only Room", "gold_cost": 9999}]
    new_json = str(tmp_path / "new.json")
    Path(new_json).write_text(json.dumps(new_data))
    run(COST_SCRIPT, [new_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT count(*) FROM {COST_TABLE}").fetchone()[0]
    conn.close()
    assert count == 1


def test_cost_bad_db_exits_nonzero(cost_json):
    result = run(COST_SCRIPT, [cost_json, "/nonexistent_xyz/db.sqlite3"])
    assert result.returncode != 0
