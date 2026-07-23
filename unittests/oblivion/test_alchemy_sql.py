"""Tests for Oblivion alchemy SQL loader scripts (create_or_update_*)."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

INGREDIENTS_SCRIPT = str(REPO_ROOT / "TES/Oblivion/alchemy/ingredients_sql/create_or_update_oblivion_alchemy_ingredients.py")
EFFECTS_SCRIPT = str(REPO_ROOT / "TES/Oblivion/alchemy/ingredients_sql/create_or_update_oblivion_alchemy_effects.py")

_ing_mod = load_module(
    "TES/Oblivion/alchemy/ingredients_sql/create_or_update_oblivion_alchemy_ingredients.py",
    "ob_ing_sql",
)
_eff_mod = load_module(
    "TES/Oblivion/alchemy/ingredients_sql/create_or_update_oblivion_alchemy_effects.py",
    "ob_eff_sql",
)

load_diff_file = _ing_mod.load_diff_file
apply_deletes = _ing_mod.apply_deletes
apply_deletes_effects = _eff_mod.apply_deletes_effects

TABLE_ING = 'oblivion_alchemy_ingredients'
TABLE_EFF = 'oblivion_alchemy_effects'

SAMPLE_INGREDIENTS = [
    {"name": "Alkanet Flower", "weight": 0.1, "value": 1, "ID": "0003365C"},
    {"name": "Boar Meat", "weight": 2.0, "value": 1, "ID": "0003AB19"},
]
SAMPLE_EFFECTS = [
    {"name": "Alkanet Flower", "effect": "Restore Intelligence", "base_cost": 38.0},
    {"name": "Alkanet Flower", "effect": "Resist Poison", "base_cost": 0.5},
    {"name": "Alkanet Flower", "effect": None, "base_cost": None},
    {"name": "Alkanet Flower", "effect": None, "base_cost": None},
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

def test_apply_deletes_removes_row(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE t (name TEXT)")
    conn.execute("INSERT INTO t VALUES ('Alkanet Flower')")
    conn.execute("INSERT INTO t VALUES ('Boar Meat')")
    conn.commit()
    apply_deletes(conn.cursor(), 't', [{"name": "Alkanet Flower"}], 'name')
    conn.commit()
    rows = [r[0] for r in conn.execute("SELECT name FROM t").fetchall()]
    assert rows == ['Boar Meat']
    conn.close()

def test_apply_deletes_effects_null_safe(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE eff (name TEXT, effect TEXT)")
    conn.execute("INSERT INTO eff VALUES ('Alkanet Flower', NULL)")
    conn.execute("INSERT INTO eff VALUES ('Alkanet Flower', 'Resist Poison')")
    conn.commit()
    apply_deletes_effects(conn.cursor(), 'eff', [{"name": "Alkanet Flower", "effect": None}])
    conn.commit()
    rows = conn.execute("SELECT effect FROM eff").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Resist Poison"
    conn.close()


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
    assert [r[0] for r in rows] == ["Alkanet Flower", "Boar Meat"]

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

def test_ingredients_upsert_updates_changed_row(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    # Update Boar Meat's value
    changed = [{"name": "Boar Meat", "weight": 2.0, "value": 99, "ID": "0003AB19"}]
    write_diff_pair(tmp_path, "ingredients", changed, {})
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    val = conn.execute(
        f"SELECT value FROM {TABLE_ING} WHERE name='Boar Meat'"
    ).fetchone()[0]
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_ING}").fetchone()[0]
    conn.close()
    assert val == 99
    assert count == 2  # no duplicate created

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
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_EFF})").fetchall()]
    conn.close()
    assert len(rows) == 4
    assert ("Alkanet Flower", "Restore Intelligence") in rows
    assert "base_cost" in cols

def test_effects_base_cost_stored(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    write_diff_pair(tmp_path, "effects", SAMPLE_EFFECTS, {})
    run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        f"SELECT base_cost FROM {TABLE_EFF} WHERE effect = 'Restore Intelligence'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == 38.0

def test_effects_schema_migration(tmp_path, tmp_db):
    """Table without base_cost column should be dropped and recreated."""
    conn = sqlite3.connect(tmp_db)
    conn.execute(f"CREATE TABLE {TABLE_EFF} (name TEXT, effect TEXT)")
    conn.execute(f"INSERT INTO {TABLE_EFF} VALUES ('OldIngredient', 'Old Effect')")
    conn.execute(f"CREATE INDEX o_e_name_effect ON {TABLE_EFF} (name, effect)")
    conn.commit()
    conn.close()
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    write_diff_pair(tmp_path, "effects", SAMPLE_EFFECTS, {})
    result = run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_EFF})").fetchall()]
    rows = conn.execute(f"SELECT name FROM {TABLE_EFF}").fetchall()
    conn.close()
    assert "base_cost" in cols
    # Old row is gone; new rows are present
    assert all(r[0] == "Alkanet Flower" for r in rows)

def test_effects_null_effect_stored_as_null(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    write_diff_pair(tmp_path, "effects", SAMPLE_EFFECTS, {})
    run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    conn = sqlite3.connect(tmp_db)
    nulls = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE_EFF} WHERE effect IS NULL"
    ).fetchone()[0]
    conn.close()
    assert nulls == 2

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
