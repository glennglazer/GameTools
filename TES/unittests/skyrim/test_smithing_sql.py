"""Tests for all 5 smithing SQL loaders."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

PERKS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/perks_sql/create_or_update_skyrim_smithing_perks.py')
ARMOR_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/armor_sql/create_or_update_skyrim_smithing_armor.py')
WEAPON_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/weapons_sql/create_or_update_skyrim_smithing_weapons.py')
IMPROVE_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/improvement_sql/create_or_update_skyrim_smithing_improvement.py')
MATS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/smithing/materials_sql/create_or_update_skyrim_smithing_materials.py')

_perks = load_module('TES/Skyrim/smithing/perks_sql/create_or_update_skyrim_smithing_perks.py', 'sk_sp_sql')
_armor = load_module('TES/Skyrim/smithing/armor_sql/create_or_update_skyrim_smithing_armor.py', 'sk_sa_sql')
_weapon = load_module('TES/Skyrim/smithing/weapons_sql/create_or_update_skyrim_smithing_weapons.py', 'sk_sw_sql')
_improve = load_module('TES/Skyrim/smithing/improvement_sql/create_or_update_skyrim_smithing_improvement.py', 'sk_si_sql')
_mats = load_module('TES/Skyrim/smithing/materials_sql/create_or_update_skyrim_smithing_materials.py', 'sk_sm_sql')

PERKS_TABLE = _perks.TABLE_NAME
ARMOR_TABLE = _armor.TABLE_NAME
WEAPON_TABLE = _weapon.TABLE_NAME
IMPROVE_TABLE = _improve.TABLE_NAME
MATS_TABLE = _mats.TABLE_NAME

PERKS_SAMPLE = [
    {'name': 'Steel Smithing', 'skill_level': 0, 'prerequisite': 'None',
     'description': 'Can create steel armor.'},
    {'name': 'Arcane Blacksmith', 'skill_level': 60, 'prerequisite': 'Steel Smithing',
     'description': 'Magical armor can now be improved.'},
]

IMPROVE_SAMPLE = [
    {'quality': 'Fine', 'skill_without_perk': 14, 'skill_with_perk': 14,
     'armor_effect': '+2', 'weapon_effect': '+1'},
    {'quality': 'Legendary', 'skill_without_perk': 168, 'skill_with_perk': 91,
     'armor_effect': '+20', 'weapon_effect': '+10'},
]

MATS_SAMPLE = [
    {'smithing_category': 'Iron', 'crafting_material': 'Iron Ingot'},
    {'smithing_category': 'Studded', 'crafting_material': 'Iron Ingot'},
    {'smithing_category': 'Steel', 'crafting_material': 'Steel Ingot'},
]

_ARMOR_MAT_COLS = [
    'bone_meal', 'chitin_plate', 'corundum_ingot', 'daedra_heart',
    'dragon_bone', 'dragon_scales', 'dwarven_metal_ingot', 'ebony_ingot',
    'iron_ingot', 'leather', 'leather_strips', 'netch_jelly', 'netch_leather',
    'orichalcum_ingot', 'quicksilver_ingot', 'refined_malachite',
    'refined_moonstone', 'stalhrim', 'steel_ingot', 'void_salts',
]

ARMOR_SAMPLE = [
    dict({'piece': 'Steel Armor', 'material_perk': 'Steel Smithing',
          'armor_rating': 34, 'weight': 35.0, 'value': 275, 'id': '0001395C',
          'leather_strips': 3, 'iron_ingot': 1, 'steel_ingot': 3},
         **{col: 0 for col in _ARMOR_MAT_COLS
            if col not in ('leather_strips', 'iron_ingot', 'steel_ingot')}),
]

_WEAPON_MAT_COLS = [
    'corundum_ingot', 'crossbow', 'daedra_heart', 'dragon_bone',
    'dwarven_crossbow', 'dwarven_metal_ingot', 'ebony_ingot', 'firewood',
    'iron_ingot', 'leather_strips', 'orichalcum_ingot', 'quicksilver_ingot',
    'refined_malachite', 'refined_moonstone', 'stalhrim', 'steel_ingot',
]

WEAPON_SAMPLE = [
    dict({'piece': 'Steel Dagger', 'material_perk': 'Steel Smithing',
          'damage': 5, 'weight': 2.5, 'value': 25, 'id': '0001397E',
          'leather_strips': 1, 'iron_ingot': 1, 'steel_ingot': 1},
         **{col: 0 for col in _WEAPON_MAT_COLS
            if col not in ('leather_strips', 'iron_ingot', 'steel_ingot')}),
]


def run(script, args):
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


def write_diff(directory, stem, upsert, delete):
    (directory / f'{stem}.upsert.json').write_text(json.dumps(upsert))
    (directory / f'{stem}.delete.json').write_text(json.dumps(delete))


# ---------------------------------------------------------------------------
# perks SQL loader
# ---------------------------------------------------------------------------

def make_perks_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_smithing_perks.json'
    p.write_text(json.dumps(data or PERKS_SAMPLE))
    return str(p)


def create_perks_table(conn):
    conn.execute(
        f"CREATE TABLE {PERKS_TABLE} "
        "(name TEXT, skill_level INTEGER, prerequisite TEXT, description TEXT)"
    )
    conn.commit()


def test_perks_load_diff_missing(tmp_path):
    data, found = _perks.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found

def test_perks_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_perks_table(conn)
    conn.execute(f"INSERT INTO {PERKS_TABLE} VALUES ('Steel Smithing', 0, 'None', 'desc')")
    conn.execute(f"INSERT INTO {PERKS_TABLE} VALUES ('Arcane Blacksmith', 60, 'Steel Smithing', 'desc')")
    conn.commit()
    _perks.apply_deletes(conn.cursor(), PERKS_TABLE, [PERKS_SAMPLE[0]], 'name')
    conn.commit()
    names = [r[0] for r in conn.execute(f"SELECT name FROM {PERKS_TABLE}").fetchall()]
    assert 'Steel Smithing' not in names and 'Arcane Blacksmith' in names
    conn.close()

def test_perks_apply_upserts(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_perks_table(conn)
    conn.execute(f"CREATE UNIQUE INDEX s_sp_name ON {PERKS_TABLE} (name)")
    conn.commit()
    _perks.apply_upserts(conn, PERKS_TABLE, PERKS_SAMPLE, 'name')
    count = conn.execute(f"SELECT COUNT(*) FROM {PERKS_TABLE}").fetchone()[0]
    assert count == 2
    conn.close()

def test_perks_first_run(tmp_path, tmp_db):
    json_file = make_perks_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_perks', PERKS_SAMPLE, {})
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
    write_diff(tmp_path, 'skyrim_smithing_perks', PERKS_SAMPLE, {})
    run(PERKS_SCRIPT, [json_file, tmp_db])
    assert not (tmp_path / 'skyrim_smithing_perks.upsert.json').exists()

def test_perks_bad_db_exits_nonzero(tmp_path):
    json_file = make_perks_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_perks', PERKS_SAMPLE, {})
    result = run(PERKS_SCRIPT, [json_file, '/nonexistent_xyz/db.sqlite3'])
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# improvement SQL loader
# ---------------------------------------------------------------------------

def make_improve_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_smithing_improvement.json'
    p.write_text(json.dumps(data or IMPROVE_SAMPLE))
    return str(p)


def create_improve_table(conn):
    conn.execute(
        f"CREATE TABLE {IMPROVE_TABLE} "
        "(quality TEXT, skill_without_perk INTEGER, skill_with_perk INTEGER, "
        "armor_effect TEXT, weapon_effect TEXT)"
    )
    conn.commit()


def test_improve_first_run(tmp_path, tmp_db):
    json_file = make_improve_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_improvement', IMPROVE_SAMPLE, {})
    result = run(IMPROVE_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {IMPROVE_TABLE}").fetchone()[0]
    conn.close()
    assert count == 2

def test_improve_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_improve_table(conn)
    conn.execute(f"INSERT INTO {IMPROVE_TABLE} VALUES ('Fine', 14, 14, '+2', '+1')")
    conn.execute(f"INSERT INTO {IMPROVE_TABLE} VALUES ('Legendary', 168, 91, '+20', '+10')")
    conn.commit()
    _improve.apply_deletes(conn.cursor(), IMPROVE_TABLE, [IMPROVE_SAMPLE[0]], 'quality')
    conn.commit()
    quals = [r[0] for r in conn.execute(f"SELECT quality FROM {IMPROVE_TABLE}").fetchall()]
    assert 'Fine' not in quals and 'Legendary' in quals
    conn.close()

def test_improve_no_diff_noop(tmp_path, tmp_db):
    json_file = make_improve_json(tmp_path)
    result = run(IMPROVE_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{IMPROVE_TABLE}'"
    ).fetchone() is None
    conn.close()


# ---------------------------------------------------------------------------
# materials SQL loader
# ---------------------------------------------------------------------------

def make_mats_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_smithing_materials.json'
    p.write_text(json.dumps(data or MATS_SAMPLE))
    return str(p)


def create_mats_table(conn):
    conn.execute(
        f"CREATE TABLE {MATS_TABLE} (smithing_category TEXT, crafting_material TEXT)"
    )
    conn.commit()


def test_mats_first_run(tmp_path, tmp_db):
    json_file = make_mats_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_materials', MATS_SAMPLE, {})
    result = run(MATS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {MATS_TABLE}").fetchone()[0]
    conn.close()
    assert count == 3

def test_mats_apply_deletes_composite_key(tmp_db):
    conn = sqlite3.connect(tmp_db)
    create_mats_table(conn)
    conn.execute(f"INSERT INTO {MATS_TABLE} VALUES ('Iron', 'Iron Ingot')")
    conn.execute(f"INSERT INTO {MATS_TABLE} VALUES ('Steel', 'Steel Ingot')")
    conn.commit()
    _mats.apply_deletes(conn.cursor(), MATS_TABLE,
                        [{'smithing_category': 'Iron', 'crafting_material': 'Iron Ingot'}])
    conn.commit()
    rows = conn.execute(f"SELECT smithing_category FROM {MATS_TABLE}").fetchall()
    assert len(rows) == 1 and rows[0][0] == 'Steel'
    conn.close()

def test_mats_no_diff_noop(tmp_path, tmp_db):
    json_file = make_mats_json(tmp_path)
    result = run(MATS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{MATS_TABLE}'"
    ).fetchone() is None
    conn.close()

def test_mats_diff_files_removed(tmp_path, tmp_db):
    json_file = make_mats_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_materials', MATS_SAMPLE, {})
    run(MATS_SCRIPT, [json_file, tmp_db])
    assert not (tmp_path / 'skyrim_smithing_materials.upsert.json').exists()


# ---------------------------------------------------------------------------
# armor SQL loader
# ---------------------------------------------------------------------------

def make_armor_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_smithing_armor.json'
    p.write_text(json.dumps(data or ARMOR_SAMPLE))
    return str(p)


def test_armor_first_run(tmp_path, tmp_db):
    json_file = make_armor_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_armor', ARMOR_SAMPLE, {})
    result = run(ARMOR_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {ARMOR_TABLE}").fetchone()[0]
    conn.close()
    assert count == 1

def test_armor_apply_deletes(tmp_db):
    conn = sqlite3.connect(tmp_db)
    col_defs = ', '.join(
        ['piece TEXT', 'material_perk TEXT', 'armor_rating INTEGER',
         'weight REAL', 'value INTEGER', 'id TEXT'] +
        [f'{col} INTEGER' for col in _ARMOR_MAT_COLS]
    )
    conn.execute(f"CREATE TABLE {ARMOR_TABLE} ({col_defs})")
    vals = ['Steel Armor', 'Steel Smithing', 34, 35.0, 275, 'ABC'] + [0] * len(_ARMOR_MAT_COLS)
    conn.execute(f"INSERT INTO {ARMOR_TABLE} VALUES ({','.join(['?']*len(vals))})", vals)
    conn.commit()
    _armor.apply_deletes(conn.cursor(), ARMOR_TABLE, [ARMOR_SAMPLE[0]], 'piece')
    conn.commit()
    count = conn.execute(f"SELECT COUNT(*) FROM {ARMOR_TABLE}").fetchone()[0]
    assert count == 0
    conn.close()

def test_armor_no_diff_noop(tmp_path, tmp_db):
    json_file = make_armor_json(tmp_path)
    result = run(ARMOR_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{ARMOR_TABLE}'"
    ).fetchone() is None
    conn.close()

def test_armor_bad_db_exits_nonzero(tmp_path):
    json_file = make_armor_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_armor', ARMOR_SAMPLE, {})
    result = run(ARMOR_SCRIPT, [json_file, '/nonexistent_xyz/db.sqlite3'])
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# weapons SQL loader
# ---------------------------------------------------------------------------

def make_weapon_json(tmp_path, data=None):
    p = tmp_path / 'skyrim_smithing_weapons.json'
    p.write_text(json.dumps(data or WEAPON_SAMPLE))
    return str(p)


def test_weapon_first_run(tmp_path, tmp_db):
    json_file = make_weapon_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_weapons', WEAPON_SAMPLE, {})
    result = run(WEAPON_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {WEAPON_TABLE}").fetchone()[0]
    conn.close()
    assert count == 1

def test_weapon_no_diff_noop(tmp_path, tmp_db):
    json_file = make_weapon_json(tmp_path)
    result = run(WEAPON_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{WEAPON_TABLE}'"
    ).fetchone() is None
    conn.close()

def test_weapon_bad_db_exits_nonzero(tmp_path):
    json_file = make_weapon_json(tmp_path)
    write_diff(tmp_path, 'skyrim_smithing_weapons', WEAPON_SAMPLE, {})
    result = run(WEAPON_SCRIPT, [json_file, '/nonexistent_xyz/db.sqlite3'])
    assert result.returncode != 0
