"""Tests for Skyrim alchemy SQL loader scripts (create_or_update_*)."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

INGREDIENTS_SCRIPT = str(REPO_ROOT / "TES/Skyrim/alchemy/ingredients_sql/create_or_update_skyrim_alchemy_ingredients.py")
EFFECTS_SCRIPT = str(REPO_ROOT / "TES/Skyrim/alchemy/ingredients_sql/create_or_update_skyrim_alchemy_effects.py")

_ing_mod = load_module(
    "TES/Skyrim/alchemy/ingredients_sql/create_or_update_skyrim_alchemy_ingredients.py",
    "sk_ing_sql",
)
_eff_mod = load_module(
    "TES/Skyrim/alchemy/ingredients_sql/create_or_update_skyrim_alchemy_effects.py",
    "sk_eff_sql",
)

load_diff_file = _ing_mod.load_diff_file
apply_deletes = _ing_mod.apply_deletes
apply_upserts_ingredients = _ing_mod.apply_upserts_ingredients
apply_deletes_effects = _eff_mod.apply_deletes_effects
apply_upserts_effects = _eff_mod.apply_upserts_effects

TABLE_ING = 'skyrim_alchemy_ingredients'
TABLE_EFF = 'skyrim_alchemy_effects'

SAMPLE_INGREDIENTS = [
    {"name": "Abecean Longfin", "weight": 0.5, "value": 15, "ID": "00106E1B"},
    {"name": "Bear Claws", "weight": 0.1, "value": 3, "ID": "0003AD57"},
]
SAMPLE_EFFECTS = [
    {"name": "Abecean Longfin", "effect": "Weakness to Frost",   "base_magnitude": 3},
    {"name": "Abecean Longfin", "effect": "Fortify Sneak",       "base_magnitude": 4},
    {"name": "Abecean Longfin", "effect": "Weakness to Poison",  "base_magnitude": 2},
    {"name": "Abecean Longfin", "effect": "Fortify Restoration", "base_magnitude": 4},
]


def run_script(script, args):
    return subprocess.run(
        [sys.executable, script] + args,
        capture_output=True, text=True,
    )


def write_diff_pair(directory: Path, stem: str, upsert_data, delete_data) -> tuple:
    u = directory / f"{stem}.upsert.json"
    d = directory / f"{stem}.delete.json"
    u.write_text(json.dumps(upsert_data))
    d.write_text(json.dumps(delete_data))
    return str(u), str(d)


# ---------------------------------------------------------------------------
# Importable unit tests
# ---------------------------------------------------------------------------

def test_load_diff_file_missing_returns_false(tmp_path):
    data, found = load_diff_file(str(tmp_path / "missing.json"))
    assert not found
    assert data == []

def test_apply_deletes_removes_correct_row(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE t (name TEXT)")
    conn.execute("INSERT INTO t VALUES ('Abecean Longfin')")
    conn.execute("INSERT INTO t VALUES ('Bear Claws')")
    conn.commit()
    apply_deletes(conn.cursor(), 't', [{"name": "Abecean Longfin"}], 'name')
    conn.commit()
    rows = [r[0] for r in conn.execute("SELECT name FROM t").fetchall()]
    assert rows == ['Bear Claws']
    conn.close()

def test_apply_upserts_ingredients_replaces_existing(tmp_db):
    import pandas as pd
    conn = sqlite3.connect(tmp_db)
    conn.execute('CREATE TABLE t ("index" INTEGER, name TEXT, value INTEGER)')
    conn.execute("INSERT INTO t VALUES (0, 'Abecean Longfin', 15)")
    conn.execute("CREATE UNIQUE INDEX t_name ON t (name)")
    conn.commit()
    apply_upserts_ingredients(conn, 't', [{"name": "Abecean Longfin", "value": 99}], 'name')
    count = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    val = conn.execute("SELECT value FROM t WHERE name='Abecean Longfin'").fetchone()[0]
    conn.close()
    assert count == 1
    assert val == 99

def test_apply_deletes_effects_removes_named_effect(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE eff (name TEXT, effect TEXT, base_magnitude INTEGER)")
    conn.execute("INSERT INTO eff VALUES ('Abecean Longfin', 'Weakness to Frost', 3)")
    conn.execute("INSERT INTO eff VALUES ('Abecean Longfin', 'Fortify Sneak', 4)")
    conn.commit()
    apply_deletes_effects(conn.cursor(), 'eff', [{"name": "Abecean Longfin", "effect": "Weakness to Frost", "base_magnitude": 3}])
    conn.commit()
    rows = conn.execute("SELECT effect FROM eff").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Fortify Sneak"
    conn.close()

def test_apply_upserts_effects_inserts_new_rows(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE eff (name TEXT, effect TEXT, base_magnitude INTEGER)")
    conn.commit()
    apply_upserts_effects(conn, 'eff', [{"name": "Bear Claws", "effect": "Restore Stamina", "base_magnitude": 5}])
    rows = conn.execute("SELECT name, effect, base_magnitude FROM eff").fetchall()
    conn.close()
    assert rows == [("Bear Claws", "Restore Stamina", 5)]


# ---------------------------------------------------------------------------
# Subprocess: ingredients
# ---------------------------------------------------------------------------

def test_ingredients_creates_table_on_first_run(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(f"SELECT name FROM {TABLE_ING} ORDER BY name").fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["Abecean Longfin", "Bear Claws"]

def test_ingredients_no_diff_files_is_noop(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{TABLE_ING}'"
    ).fetchone() is None
    conn.close()

def test_ingredients_upsert_adds_new_row(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    new_row = [{"name": "Blue Butterfly Wing", "weight": 0.1, "value": 2, "ID": "0003AD52"}]
    write_diff_pair(tmp_path, "ingredients", new_row, {})
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_ING}").fetchone()[0]
    conn.close()
    assert count == 3

def test_ingredients_diff_files_removed_after_success(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    u, d = write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert not Path(u).exists()
    assert not Path(d).exists()

def test_ingredients_bad_upsert_json_exits_nonzero(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    (tmp_path / "ingredients.upsert.json").write_text("not json")
    (tmp_path / "ingredients.delete.json").write_text("{}")
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# Subprocess: effects
# ---------------------------------------------------------------------------

def test_effects_creates_table_on_first_run(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    write_diff_pair(tmp_path, "effects", SAMPLE_EFFECTS, {})
    result = run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(f"SELECT name, effect FROM {TABLE_EFF}").fetchall()
    conn.close()
    assert len(rows) == 4
    assert ("Abecean Longfin", "Weakness to Frost") in rows

def test_effects_base_magnitude_stored(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    write_diff_pair(tmp_path, "effects", SAMPLE_EFFECTS, {})
    run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT base_magnitude FROM {TABLE_EFF} WHERE name='Abecean Longfin' AND effect='Weakness to Frost'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == 3

def test_effects_schema_migration_drops_old_table(tmp_path, tmp_db):
    # Simulate a pre-base_magnitude table (old schema, no base_magnitude column).
    conn = sqlite3.connect(tmp_db)
    conn.execute(f"CREATE TABLE {TABLE_EFF} (name TEXT, effect TEXT)")
    conn.execute(f"INSERT INTO {TABLE_EFF} VALUES ('Abecean Longfin', 'Weakness to Frost')")
    conn.execute(f"CREATE UNIQUE INDEX s_e_name_effect ON {TABLE_EFF} (name, effect)")
    conn.commit()
    conn.close()
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    write_diff_pair(tmp_path, "effects", SAMPLE_EFFECTS, {})
    result = run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_EFF})").fetchall()]
    assert 'base_magnitude' in cols
    conn.close()

def test_effects_no_diff_files_is_noop(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    result = run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    assert conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{TABLE_EFF}'"
    ).fetchone() is None
    conn.close()

def test_effects_invalid_json_exits_nonzero(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    (tmp_path / "effects.upsert.json").write_text("{bad}")
    (tmp_path / "effects.delete.json").write_text("{}")
    result = run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode != 0
