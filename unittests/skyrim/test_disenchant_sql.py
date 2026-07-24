"""Tests for skyrim_enchant_disenchant_apparel and _weapons SQL loaders."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

APPAREL_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/disenchant_apparel_sql/create_or_update_skyrim_enchant_disenchant_apparel.py')
WEAPONS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/disenchant_weapons_sql/create_or_update_skyrim_enchant_disenchant_weapons.py')

_apparel = load_module(
    'TES/Skyrim/enchanting/disenchant_apparel_sql/create_or_update_skyrim_enchant_disenchant_apparel.py',
    'sk_disenchant_apparel_sql',
)
_weapons = load_module(
    'TES/Skyrim/enchanting/disenchant_weapons_sql/create_or_update_skyrim_enchant_disenchant_weapons.py',
    'sk_disenchant_weapons_sql',
)

APPAREL_TABLE = _apparel.TABLE_NAME
WEAPONS_TABLE = _weapons.TABLE_NAME

APPAREL_SAMPLE = [
    {'effect': 'Fortify Alchemy', 'item': 'Bracers of Alchemy', 'note': 'All levels of enchantment'},
    {'effect': 'Fortify Alchemy', 'item': "Muiri's Ring", 'note': None},
]

WEAPONS_SAMPLE = [
    {'effect': 'Absorb Health', 'item': 'All weapons of Absorption', 'note': None},
    {'effect': 'Absorb Health', 'item': 'Blade of Woe', 'note': None},
    {'effect': 'Absorb Magicka', 'item': 'Drainspell Bow', 'note': 'Has unique version of effect.'},
]


def run(script, args):
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


def write_diff(directory, stem, upsert, delete):
    (directory / f'{stem}.upsert.json').write_text(json.dumps(upsert))
    (directory / f'{stem}.delete.json').write_text(json.dumps(delete))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _create_apparel_table(conn):
    conn.execute(
        f'CREATE TABLE {APPAREL_TABLE} '
        '(effect TEXT, item TEXT, note TEXT)'
    )
    conn.commit()


def _create_weapons_table(conn):
    conn.execute(
        f'CREATE TABLE {WEAPONS_TABLE} '
        '(effect TEXT, item TEXT, note TEXT)'
    )
    conn.commit()


# ===========================================================================
# Apparel SQL loader
# ===========================================================================

def make_apparel_json(tmp_path, data=None):
    p = tmp_path / 'disenchant_apparel.json'
    p.write_text(json.dumps(data or APPAREL_SAMPLE))
    return str(p)


def test_apparel_load_diff_file_missing(tmp_path):
    data, found = _apparel.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found


def test_apparel_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    _create_apparel_table(conn)
    conn.execute(f"INSERT INTO {APPAREL_TABLE} VALUES ('Fortify Alchemy', 'Bracers of Alchemy', 'All levels of enchantment')")
    conn.execute(f"INSERT INTO {APPAREL_TABLE} VALUES ('Fortify Alchemy', 'Muiri''s Ring', NULL)")
    conn.commit()
    _apparel.apply_deletes(conn.cursor(), APPAREL_TABLE, [APPAREL_SAMPLE[0]])
    conn.commit()
    items = [r[0] for r in conn.execute(f'SELECT item FROM {APPAREL_TABLE}').fetchall()]
    assert 'Bracers of Alchemy' not in items
    assert "Muiri's Ring" in items
    conn.close()


def test_apparel_apply_upserts(tmp_db):
    conn = sqlite3.connect(tmp_db)
    _create_apparel_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_edap_ef_it ON {APPAREL_TABLE} (effect, item)")
    conn.commit()
    _apparel.apply_upserts(conn, APPAREL_TABLE, APPAREL_SAMPLE)
    count = conn.execute(f'SELECT COUNT(*) FROM {APPAREL_TABLE}').fetchone()[0]
    assert count == 2
    conn.close()


def test_apparel_upsert_replaces_existing(tmp_db):
    conn = sqlite3.connect(tmp_db)
    _create_apparel_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_edap_ef_it ON {APPAREL_TABLE} (effect, item)")
    conn.execute(f"INSERT INTO {APPAREL_TABLE} VALUES ('Fortify Alchemy', 'Bracers of Alchemy', 'old note')")
    conn.commit()
    _apparel.apply_upserts(conn, APPAREL_TABLE, [{'effect': 'Fortify Alchemy', 'item': 'Bracers of Alchemy', 'note': 'new note'}])
    val = conn.execute(f"SELECT note FROM {APPAREL_TABLE} WHERE item='Bracers of Alchemy'").fetchone()[0]
    assert val == 'new note'
    conn.close()


def test_apparel_first_run(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'disenchant_apparel', APPAREL_SAMPLE, {})
    result = run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f'SELECT COUNT(*) FROM {APPAREL_TABLE}').fetchone()[0]
    conn.close()
    assert count == 2


def test_apparel_first_run_null_note_stored(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'disenchant_apparel', APPAREL_SAMPLE, {})
    run(APPAREL_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    note = conn.execute(
        f"SELECT note FROM {APPAREL_TABLE} WHERE item=\"Muiri's Ring\""
    ).fetchone()[0]
    conn.close()
    assert note is None


def test_apparel_no_diff_noop(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    result = run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(f"SELECT name FROM sqlite_master WHERE name='{APPAREL_TABLE}'").fetchone() is None
    conn.close()


def test_apparel_diff_files_removed(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'disenchant_apparel', APPAREL_SAMPLE, {})
    run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert not (tmp_path / 'disenchant_apparel.upsert.json').exists()
    assert not (tmp_path / 'disenchant_apparel.delete.json').exists()


def test_apparel_composite_key_index(tmp_path, tmp_db):
    """Unique index enforces (effect, item) composite key."""
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'disenchant_apparel', APPAREL_SAMPLE, {})
    run(APPAREL_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    idx = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type='index' AND name='s_edap_ef_it'"
    ).fetchone()
    conn.close()
    assert idx is not None


def test_apparel_bad_json_exits_nonzero(tmp_path, tmp_db):
    json_file = make_apparel_json(tmp_path)
    (tmp_path / 'disenchant_apparel.upsert.json').write_text('not json')
    (tmp_path / 'disenchant_apparel.delete.json').write_text('{}')
    result = run(APPAREL_SCRIPT, [json_file, tmp_db])
    assert result.returncode != 0


def test_apparel_bad_db_exits_nonzero(tmp_path):
    json_file = make_apparel_json(tmp_path)
    write_diff(tmp_path, 'disenchant_apparel', APPAREL_SAMPLE, {})
    result = run(APPAREL_SCRIPT, [json_file, '/nonexistent_dir_xyz/db.sqlite3'])
    assert result.returncode != 0


# ===========================================================================
# Weapons SQL loader
# ===========================================================================

def make_weapons_json(tmp_path, data=None):
    p = tmp_path / 'disenchant_weapons.json'
    p.write_text(json.dumps(data or WEAPONS_SAMPLE))
    return str(p)


def test_weapons_load_diff_file_missing(tmp_path):
    data, found = _weapons.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found


def test_weapons_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    _create_weapons_table(conn)
    conn.execute(f"INSERT INTO {WEAPONS_TABLE} VALUES ('Absorb Health', 'All weapons of Absorption', NULL)")
    conn.execute(f"INSERT INTO {WEAPONS_TABLE} VALUES ('Absorb Health', 'Blade of Woe', NULL)")
    conn.commit()
    _weapons.apply_deletes(conn.cursor(), WEAPONS_TABLE, [WEAPONS_SAMPLE[0]])
    conn.commit()
    items = [r[0] for r in conn.execute(f'SELECT item FROM {WEAPONS_TABLE}').fetchall()]
    assert 'All weapons of Absorption' not in items
    assert 'Blade of Woe' in items
    conn.close()


def test_weapons_apply_upserts(tmp_db):
    conn = sqlite3.connect(tmp_db)
    _create_weapons_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_edwp_ef_it ON {WEAPONS_TABLE} (effect, item)")
    conn.commit()
    _weapons.apply_upserts(conn, WEAPONS_TABLE, WEAPONS_SAMPLE)
    count = conn.execute(f'SELECT COUNT(*) FROM {WEAPONS_TABLE}').fetchone()[0]
    assert count == 3
    conn.close()


def test_weapons_first_run(tmp_path, tmp_db):
    json_file = make_weapons_json(tmp_path)
    write_diff(tmp_path, 'disenchant_weapons', WEAPONS_SAMPLE, {})
    result = run(WEAPONS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f'SELECT COUNT(*) FROM {WEAPONS_TABLE}').fetchone()[0]
    conn.close()
    assert count == 3


def test_weapons_first_run_note_stored(tmp_path, tmp_db):
    json_file = make_weapons_json(tmp_path)
    write_diff(tmp_path, 'disenchant_weapons', WEAPONS_SAMPLE, {})
    run(WEAPONS_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    note = conn.execute(
        f"SELECT note FROM {WEAPONS_TABLE} WHERE item='Drainspell Bow'"
    ).fetchone()[0]
    conn.close()
    assert note == 'Has unique version of effect.'


def test_weapons_no_diff_noop(tmp_path, tmp_db):
    json_file = make_weapons_json(tmp_path)
    result = run(WEAPONS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(f"SELECT name FROM sqlite_master WHERE name='{WEAPONS_TABLE}'").fetchone() is None
    conn.close()


def test_weapons_diff_files_removed(tmp_path, tmp_db):
    json_file = make_weapons_json(tmp_path)
    write_diff(tmp_path, 'disenchant_weapons', WEAPONS_SAMPLE, {})
    run(WEAPONS_SCRIPT, [json_file, tmp_db])
    assert not (tmp_path / 'disenchant_weapons.upsert.json').exists()
    assert not (tmp_path / 'disenchant_weapons.delete.json').exists()


def test_weapons_composite_key_index(tmp_path, tmp_db):
    json_file = make_weapons_json(tmp_path)
    write_diff(tmp_path, 'disenchant_weapons', WEAPONS_SAMPLE, {})
    run(WEAPONS_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    idx = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type='index' AND name='s_edwp_ef_it'"
    ).fetchone()
    conn.close()
    assert idx is not None


def test_weapons_bad_db_exits_nonzero(tmp_path):
    json_file = make_weapons_json(tmp_path)
    write_diff(tmp_path, 'disenchant_weapons', WEAPONS_SAMPLE, {})
    result = run(WEAPONS_SCRIPT, [json_file, '/nonexistent_dir_xyz/db.sqlite3'])
    assert result.returncode != 0
