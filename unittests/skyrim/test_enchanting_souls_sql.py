"""Tests for skyrim_enchant_soulgems SQL loader."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

GEM_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/gem_types_sql/create_or_update_skyrim_enchant_soulgems.py')

_gem = load_module(
    'TES/Skyrim/enchanting/gem_types_sql/create_or_update_skyrim_enchant_soulgems.py',
    'sk_gem_sql',
)

GEM_TABLE = _gem.TABLE_NAME   # skyrim_enchant_soulgems

GEM_SAMPLE = [
    {'name': 'Petty Soul Gem', 'weight': 0.1, 'value': 10, 'capacity': 250,
     'trappable_souls': 'Creature souls below level 4.'},
    {'name': 'Grand Soul Gem', 'weight': 0.5, 'value': 200, 'capacity': 3000,
     'trappable_souls': 'Any non-humanoid soul.'},
]


def run_gem(args):
    return subprocess.run([sys.executable, GEM_SCRIPT] + args, capture_output=True, text=True)


def write_diff(directory, stem, upsert, delete):
    (directory / f'{stem}.upsert.json').write_text(json.dumps(upsert))
    (directory / f'{stem}.delete.json').write_text(json.dumps(delete))


# ===========================================================================
# gem_types SQL loader
# ===========================================================================

def make_gem_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_enchant_soulgems.json'
    p.write_text(json.dumps(data or GEM_SAMPLE))
    return str(p)


def create_gem_table(conn):
    conn.execute(
        f"CREATE TABLE {GEM_TABLE} "
        "(name TEXT, weight REAL, value INTEGER, capacity INTEGER, trappable_souls TEXT)"
    )
    conn.commit()


def test_gem_load_diff_file_missing(tmp_path):
    data, found = _gem.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found

def test_gem_load_diff_file_sentinel_dict(tmp_path):
    p = tmp_path / 'f.json'
    p.write_text('{}')
    data, found = _gem.load_diff_file(str(p))
    assert found
    assert data == []

def test_gem_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_gem_table(conn)
    conn.execute(f"INSERT INTO {GEM_TABLE} VALUES ('Petty Soul Gem', 0.1, 10, 250, 'desc')")
    conn.execute(f"INSERT INTO {GEM_TABLE} VALUES ('Grand Soul Gem', 0.5, 200, 3000, 'desc')")
    conn.commit()
    _gem.apply_deletes(conn.cursor(), GEM_TABLE, [GEM_SAMPLE[0]], 'name')
    conn.commit()
    names = [r[0] for r in conn.execute(f"SELECT name FROM {GEM_TABLE}").fetchall()]
    assert 'Petty Soul Gem' not in names
    assert 'Grand Soul Gem' in names
    conn.close()

def test_gem_apply_upserts(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_gem_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_esg_name ON {GEM_TABLE} (name)")
    conn.commit()
    _gem.apply_upserts(conn, GEM_TABLE, GEM_SAMPLE, 'name')
    count = conn.execute(f"SELECT COUNT(*) FROM {GEM_TABLE}").fetchone()[0]
    assert count == 2
    conn.close()

def test_gem_first_run(tmp_path, tmp_db):
    json_file = make_gem_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_soulgems', GEM_SAMPLE, {})
    result = run_gem([json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {GEM_TABLE}").fetchone()[0]
    conn.close()
    assert count == 2

def test_gem_no_diff_files_noop(tmp_path, tmp_db):
    json_file = make_gem_json(tmp_path)
    result = run_gem([json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(f"SELECT name FROM sqlite_master WHERE name='{GEM_TABLE}'").fetchone() is None
    conn.close()

def test_gem_diff_files_removed(tmp_path, tmp_db):
    json_file = make_gem_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_soulgems', GEM_SAMPLE, {})
    run_gem([json_file, tmp_db])
    assert not (tmp_path / 'skyrim_enchant_soulgems.upsert.json').exists()

def test_gem_bad_db_exits_nonzero(tmp_path):
    json_file = make_gem_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_soulgems', GEM_SAMPLE, {})
    result = run_gem([json_file, '/nonexistent_dir_xyz/db.sqlite3'])
    assert result.returncode != 0
