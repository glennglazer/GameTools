"""Tests for TES/Skyrim/alchemy/perks_sql/create_or_update_skyrim_alchemy_perks.py"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

SCRIPT = str(REPO_ROOT / 'TES/Skyrim/alchemy/perks_sql/create_or_update_skyrim_alchemy_perks.py')

_mod = load_module(
    'TES/Skyrim/alchemy/perks_sql/create_or_update_skyrim_alchemy_perks.py',
    'sk_perks_sql',
)
load_diff_file  = _mod.load_diff_file
apply_deletes   = _mod.apply_deletes
apply_upserts   = _mod.apply_upserts
TABLE_NAME      = _mod.TABLE_NAME

SAMPLE_PERKS = [
    {'name': 'Alchemist (1/5)', 'skill_level': 0, 'prerequisite': 'None',
     'description': 'Potions and poisons are 20% stronger.'},
    {'name': 'Physician', 'skill_level': 20, 'prerequisite': 'Alchemist (1/5)',
     'description': 'Potions restore health 25% more.'},
]


def run_script(args):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True, text=True,
    )


def write_diff_pair(directory: Path, stem: str, upsert_data, delete_data) -> tuple:
    u = directory / f'{stem}.upsert.json'
    d = directory / f'{stem}.delete.json'
    u.write_text(json.dumps(upsert_data))
    d.write_text(json.dumps(delete_data))
    return str(u), str(d)


def make_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_alchemy_perks.json'
    p.write_text(json.dumps(data or SAMPLE_PERKS))
    return str(p)


def create_table(conn):
    conn.execute(
        f"CREATE TABLE {TABLE_NAME} "
        "(name TEXT, skill_level INTEGER, prerequisite TEXT, description TEXT)"
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Importable unit tests
# ---------------------------------------------------------------------------

def test_load_diff_file_missing_returns_false(tmp_path):
    data, found = load_diff_file(str(tmp_path / 'missing.json'))
    assert not found
    assert data == []

def test_load_diff_file_present_returns_data(tmp_path):
    p = tmp_path / 'data.json'
    p.write_text(json.dumps(SAMPLE_PERKS))
    data, found = load_diff_file(str(p))
    assert found
    assert data == SAMPLE_PERKS

def test_load_diff_file_sentinel_dict_returns_empty(tmp_path):
    p = tmp_path / 'empty.json'
    p.write_text('{}')
    data, found = load_diff_file(str(p))
    assert found
    assert data == []

def test_apply_deletes_removes_named_row(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_table(conn)
    conn.execute(f"INSERT INTO {TABLE_NAME} VALUES ('Alchemist (1/5)', 0, 'None', 'Stronger.')")
    conn.execute(f"INSERT INTO {TABLE_NAME} VALUES ('Physician', 20, 'Alchemist (1/5)', 'Restore.')")
    conn.commit()
    apply_deletes(conn.cursor(), TABLE_NAME, [{'name': 'Alchemist (1/5)'}], 'name')
    conn.commit()
    rows = [r[0] for r in conn.execute(f"SELECT name FROM {TABLE_NAME}").fetchall()]
    conn.close()
    assert rows == ['Physician']

def test_apply_upserts_inserts_new_rows(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX sk_ap_name ON {TABLE_NAME} (name)")
    conn.commit()
    apply_upserts(conn, TABLE_NAME, SAMPLE_PERKS, 'name')
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 2

def test_apply_upserts_replaces_existing_row(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX sk_ap_name ON {TABLE_NAME} (name)")
    conn.execute(f"INSERT INTO {TABLE_NAME} VALUES ('Physician', 20, 'Alchemist (1/5)', 'Old desc.')")
    conn.commit()
    apply_upserts(conn, TABLE_NAME, [{'name': 'Physician', 'skill_level': 20,
                                      'prerequisite': 'Alchemist (1/5)', 'description': 'New desc.'}], 'name')
    val = conn.execute(f"SELECT description FROM {TABLE_NAME} WHERE name='Physician'").fetchone()[0]
    conn.close()
    assert val == 'New desc.'


# ---------------------------------------------------------------------------
# Subprocess: full flow
# ---------------------------------------------------------------------------

def test_first_run_creates_table(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', SAMPLE_PERKS, {})
    result = run_script([json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    names = [r[0] for r in conn.execute(
        f"SELECT name FROM {TABLE_NAME} ORDER BY name"
    ).fetchall()]
    conn.close()
    assert 'Alchemist (1/5)' in names
    assert 'Physician' in names

def test_first_run_row_count(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', SAMPLE_PERKS, {})
    run_script([json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 2

def test_no_diff_files_is_noop(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    result = run_script([json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{TABLE_NAME}'"
    ).fetchone() is None
    conn.close()

def test_upsert_adds_new_row(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', SAMPLE_PERKS, {})
    run_script([json_file, tmp_db])
    new_perk = [{'name': 'Purity', 'skill_level': 100, 'prerequisite': 'Snakeblood',
                 'description': 'Removes negative effects.'}]
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', new_perk, {})
    result = run_script([json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    assert count == 3

def test_delete_removes_row(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', SAMPLE_PERKS, {})
    run_script([json_file, tmp_db])
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', {}, [SAMPLE_PERKS[0]])
    result = run_script([json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    names = [r[0] for r in conn.execute(f"SELECT name FROM {TABLE_NAME}").fetchall()]
    conn.close()
    assert 'Alchemist (1/5)' not in names
    assert 'Physician' in names

def test_changed_value_is_reflected(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', SAMPLE_PERKS, {})
    run_script([json_file, tmp_db])
    updated = [{**SAMPLE_PERKS[0], 'skill_level': 99}]
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', updated, {})
    result = run_script([json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    val = conn.execute(
        f"SELECT skill_level FROM {TABLE_NAME} WHERE name='Alchemist (1/5)'"
    ).fetchone()[0]
    conn.close()
    assert val == 99

def test_diff_files_removed_after_success(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    u, d = write_diff_pair(tmp_path, 'skyrim_alchemy_perks', SAMPLE_PERKS, {})
    run_script([json_file, tmp_db])
    assert not Path(u).exists()
    assert not Path(d).exists()

def test_bad_upsert_json_exits_nonzero(tmp_path, tmp_db):
    json_file = make_json(tmp_path)
    (tmp_path / 'skyrim_alchemy_perks.upsert.json').write_text('not json')
    (tmp_path / 'skyrim_alchemy_perks.delete.json').write_text('{}')
    result = run_script([json_file, tmp_db])
    assert result.returncode != 0

def test_bad_db_path_exits_nonzero(tmp_path):
    json_file = make_json(tmp_path)
    write_diff_pair(tmp_path, 'skyrim_alchemy_perks', SAMPLE_PERKS, {})
    result = run_script([json_file, '/nonexistent_dir_xyz/db.sqlite3'])
    assert result.returncode != 0
