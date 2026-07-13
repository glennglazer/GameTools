"""Tests for perks, effects, and apparel SQL loaders."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

PERKS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/perks_sql/create_or_update_skyrim_enchant_perks.py')
EFFECTS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/enchant_effects_sql/create_or_update_skyrim_enchant_effects.py')
APPAREL_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/enchant_apparel_sql/create_or_update_skyrim_enchant_apparel.py')

_perks = load_module(
    'TES/Skyrim/enchanting/perks_sql/create_or_update_skyrim_enchant_perks.py',
    'sk_enchant_perks_sql',
)
_effects = load_module(
    'TES/Skyrim/enchanting/enchant_effects_sql/create_or_update_skyrim_enchant_effects.py',
    'sk_enchant_effects_sql',
)
_apparel = load_module(
    'TES/Skyrim/enchanting/enchant_apparel_sql/create_or_update_skyrim_enchant_apparel.py',
    'sk_enchant_apparel_sql',
)

PERKS_TABLE = _perks.TABLE_NAME    # skyrim_enchant_perks
EFFECTS_TABLE = _effects.TABLE_NAME  # skyrim_enchant_effects
APPAREL_TABLE = _apparel.TABLE_NAME  # skyrim_enchant_apparel

PERKS_SAMPLE = [
    {'name': 'Enchanter (1/5)', 'skill_level': 0, 'prerequisite': 'None',
     'description': 'New enchantments are 20% stronger.'},
    {'name': 'Soul Squeezer', 'skill_level': 20, 'prerequisite': 'Enchanter (1/5)',
     'description': 'Soul gems provide extra magicka.'},
]

EFFECTS_SAMPLE = [
    {'name': 'Absorb Health', 'school': 'Destruction'},
    {'name': 'Banish', 'school': 'Conjuration'},
]

APPAREL_SAMPLE = [
    {'enchantment': 'Fortify Alchemy', 'head': True, 'chest': False,
     'hands': True, 'feet': False, 'shield': False, 'amulet': True, 'ring': True},
    {'enchantment': 'Muffle', 'head': False, 'chest': False,
     'hands': False, 'feet': True, 'shield': False, 'amulet': False, 'ring': False},
]


def run(script, args):
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


def write_diff(directory, stem, upsert, delete):
    (directory / f'{stem}.upsert.json').write_text(json.dumps(upsert))
    (directory / f'{stem}.delete.json').write_text(json.dumps(delete))


# ===========================================================================
# perks SQL loader
# ===========================================================================

def make_perks_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_enchant_perks.json'
    p.write_text(json.dumps(data or PERKS_SAMPLE))
    return str(p)


def create_perks_table(conn):
    conn.execute(
        f"CREATE TABLE {PERKS_TABLE} "
        "(name TEXT, skill_level INTEGER, prerequisite TEXT, description TEXT)"
    )
    conn.commit()


def test_perks_load_diff_file_missing(tmp_path):
    data, found = _perks.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found

def test_perks_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_perks_table(conn)
    conn.execute(f"INSERT INTO {PERKS_TABLE} VALUES ('Enchanter (1/5)', 0, 'None', 'desc')")
    conn.execute(f"INSERT INTO {PERKS_TABLE} VALUES ('Soul Squeezer', 20, 'Enchanter (1/5)', 'desc')")
    conn.commit()
    _perks.apply_deletes(conn.cursor(), PERKS_TABLE, [PERKS_SAMPLE[0]], 'name')
    conn.commit()
    names = [r[0] for r in conn.execute(f"SELECT name FROM {PERKS_TABLE}").fetchall()]
    assert 'Enchanter (1/5)' not in names and 'Soul Squeezer' in names
    conn.close()

def test_perks_apply_upserts(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_perks_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_ep_name ON {PERKS_TABLE} (name)")
    conn.commit()
    _perks.apply_upserts(conn, PERKS_TABLE, PERKS_SAMPLE, 'name')
    count = conn.execute(f"SELECT COUNT(*) FROM {PERKS_TABLE}").fetchone()[0]
    assert count == 2
    conn.close()

def test_perks_upsert_replaces_existing(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_perks_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_ep_name ON {PERKS_TABLE} (name)")
    conn.execute(f"INSERT INTO {PERKS_TABLE} VALUES ('Soul Squeezer', 20, 'Enchanter (1/5)', 'Old desc.')")
    conn.commit()
    updated = [{'name': 'Soul Squeezer', 'skill_level': 20, 'prerequisite': 'Enchanter (1/5)',
                'description': 'New desc.'}]
    _perks.apply_upserts(conn, PERKS_TABLE, updated, 'name')
    val = conn.execute(f"SELECT description FROM {PERKS_TABLE} WHERE name='Soul Squeezer'").fetchone()[0]
    assert val == 'New desc.'
    conn.close()

def test_perks_first_run(tmp_path, tmp_db):
    json_file = make_perks_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_perks', PERKS_SAMPLE, {})
    result = run(PERKS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {PERKS_TABLE}").fetchone()[0]
    conn.close()
    assert count == 2

def test_perks_no_diff_noop(tmp_path, tmp_db):
    json_file = make_perks_json(tmp_path)
    result = run(PERKS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(f"SELECT name FROM sqlite_master WHERE name='{PERKS_TABLE}'").fetchone() is None
    conn.close()

def test_perks_diff_files_removed(tmp_path, tmp_db):
    json_file = make_perks_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_perks', PERKS_SAMPLE, {})
    run(PERKS_SCRIPT, [json_file, tmp_db])
    assert not (tmp_path / 'skyrim_enchant_perks.upsert.json').exists()

def test_perks_bad_db_exits_nonzero(tmp_path):
    json_file = make_perks_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_perks', PERKS_SAMPLE, {})
    result = run(PERKS_SCRIPT, [json_file, '/nonexistent_dir_xyz/db.sqlite3'])
    assert result.returncode != 0


# ===========================================================================
# effects SQL loader
# ===========================================================================

def make_effects_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_enchant_effects.json'
    p.write_text(json.dumps(data or EFFECTS_SAMPLE))
    return str(p)


def create_effects_table(conn):
    conn.execute(f"CREATE TABLE {EFFECTS_TABLE} (name TEXT, school TEXT)")
    conn.commit()


def test_effects_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_effects_table(conn)
    conn.execute(f"INSERT INTO {EFFECTS_TABLE} VALUES ('Absorb Health', 'Destruction')")
    conn.execute(f"INSERT INTO {EFFECTS_TABLE} VALUES ('Banish', 'Conjuration')")
    conn.commit()
    _effects.apply_deletes(conn.cursor(), EFFECTS_TABLE, [EFFECTS_SAMPLE[0]], 'name')
    conn.commit()
    names = [r[0] for r in conn.execute(f"SELECT name FROM {EFFECTS_TABLE}").fetchall()]
    assert 'Absorb Health' not in names and 'Banish' in names
    conn.close()

def test_effects_first_run(tmp_path, tmp_db):
    json_file = make_effects_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_effects', EFFECTS_SAMPLE, {})
    result = run(EFFECTS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {EFFECTS_TABLE}").fetchone()[0]
    conn.close()
    assert count == 2

def test_effects_no_diff_noop(tmp_path, tmp_db):
    json_file = make_effects_json(tmp_path)
    result = run(EFFECTS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(f"SELECT name FROM sqlite_master WHERE name='{EFFECTS_TABLE}'").fetchone() is None
    conn.close()

def test_effects_diff_files_removed(tmp_path, tmp_db):
    json_file = make_effects_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_effects', EFFECTS_SAMPLE, {})
    run(EFFECTS_SCRIPT, [json_file, tmp_db])
    assert not (tmp_path / 'skyrim_enchant_effects.upsert.json').exists()
    assert not (tmp_path / 'skyrim_enchant_effects.delete.json').exists()


# ===========================================================================
# apparel SQL loader
# ===========================================================================

def make_apparel_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_enchant_apparel.json'
    p.write_text(json.dumps(data or APPAREL_SAMPLE))
    return str(p)


def create_apparel_table(conn):
    conn.execute(
        f"CREATE TABLE {APPAREL_TABLE} "
        "(enchantment TEXT, head INTEGER, chest INTEGER, hands INTEGER, "
        "feet INTEGER, shield INTEGER, amulet INTEGER, ring INTEGER)"
    )
    conn.commit()


def test_apparel_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_apparel_table(conn)
    conn.execute(f"INSERT INTO {APPAREL_TABLE} VALUES ('Fortify Alchemy', 1, 0, 1, 0, 0, 1, 1)")
    conn.execute(f"INSERT INTO {APPAREL_TABLE} VALUES ('Muffle', 0, 0, 0, 1, 0, 0, 0)")
    conn.commit()
    _apparel.apply_deletes(conn.cursor(), APPAREL_TABLE, [APPAREL_SAMPLE[0]], 'enchantment')
    conn.commit()
    names = [r[0] for r in conn.execute(f"SELECT enchantment FROM {APPAREL_TABLE}").fetchall()]
    assert 'Fortify Alchemy' not in names and 'Muffle' in names
    conn.close()

def test_apparel_apply_upserts(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_apparel_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_ea_ench ON {APPAREL_TABLE} (enchantment)")
    conn.commit()
    _apparel.apply_upserts(conn, APPAREL_TABLE, APPAREL_SAMPLE, 'enchantment')
    count = conn.execute(f"SELECT COUNT(*) FROM {APPAREL_TABLE}").fetchone()[0]
    assert count == 2
    conn.close()

def test_apparel_first_run(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_apparel', APPAREL_SAMPLE, {})
    result = run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {APPAREL_TABLE}").fetchone()[0]
    conn.close()
    assert count == 2

def test_apparel_first_run_booleans_stored(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_apparel', APPAREL_SAMPLE, {})
    run(APPAREL_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT head, chest, hands FROM {APPAREL_TABLE} WHERE enchantment='Fortify Alchemy'"
    ).fetchone()
    conn.close()
    assert row[0] == 1   # head = True
    assert row[1] == 0   # chest = False
    assert row[2] == 1   # hands = True

def test_apparel_no_diff_noop(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    result = run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{APPAREL_TABLE}'"
    ).fetchone() is None
    conn.close()

def test_apparel_diff_files_removed(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_apparel', APPAREL_SAMPLE, {})
    run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert not (tmp_path / 'skyrim_enchant_apparel.upsert.json').exists()
    assert not (tmp_path / 'skyrim_enchant_apparel.delete.json').exists()

def test_apparel_bad_json_exits_nonzero(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    (tmp_path / 'skyrim_enchant_apparel.upsert.json').write_text('not json')
    (tmp_path / 'skyrim_enchant_apparel.delete.json').write_text('{}')
    result = run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert result.returncode != 0

def test_apparel_bad_db_exits_nonzero(tmp_path):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'skyrim_enchant_apparel', APPAREL_SAMPLE, {})
    result = run(APPAREL_SCRIPT, [json_file, '/nonexistent_dir_xyz/db.sqlite3'])
    assert result.returncode != 0
