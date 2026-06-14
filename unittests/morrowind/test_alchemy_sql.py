"""Tests for Morrowind alchemy SQL loader scripts (create_or_update_*)."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

INGREDIENTS_SCRIPT = str(REPO_ROOT / "Morrowind/alchemy/ingredients_sql/create_or_update_morrowind_alchemy_ingredients.py")
EFFECTS_SCRIPT = str(REPO_ROOT / "Morrowind/alchemy/ingredients_sql/create_or_update_morrowind_alchemy_effects.py")

_ing_mod = load_module(
    "Morrowind/alchemy/ingredients_sql/create_or_update_morrowind_alchemy_ingredients.py",
    "mw_ing_sql",
)
_eff_mod = load_module(
    "Morrowind/alchemy/ingredients_sql/create_or_update_morrowind_alchemy_effects.py",
    "mw_eff_sql",
)

load_json_file = _ing_mod.load_json_file
load_diff_file = _ing_mod.load_diff_file
apply_deletes = _ing_mod.apply_deletes
apply_upserts_ingredients = _ing_mod.apply_upserts_ingredients
apply_deletes_effects = _eff_mod.apply_deletes_effects
apply_upserts_effects = _eff_mod.apply_upserts_effects

TABLE_ING = 'morrowind_alchemy_ingredients'
TABLE_EFF = 'morrowind_alchemy_effects'

SAMPLE_INGREDIENTS = [
    {"name": "Alit Hide", "weight": 1.0, "value": 5, "ID": "ingred_alit_hide_01"},
    {"name": "Ash Yam", "weight": 1.0, "value": 2, "ID": "ingred_ash_yam_01"},
]
SAMPLE_EFFECTS = [
    {"name": "Alit Hide", "effect": "Drain Intelligence"},
    {"name": "Alit Hide", "effect": "Resist Poison"},
    {"name": "Alit Hide", "effect": None},
    {"name": "Alit Hide", "effect": None},
]


def run_script(script, args):
    return subprocess.run(
        [sys.executable, script] + args,
        capture_output=True, text=True,
    )


def write_diff_pair(directory: Path, stem: str, upsert_data, delete_data) -> tuple:
    """Write <stem>.upsert.json and <stem>.delete.json; return their paths."""
    u = directory / f"{stem}.upsert.json"
    d = directory / f"{stem}.delete.json"
    u.write_text(json.dumps(upsert_data))
    d.write_text(json.dumps(delete_data))
    return str(u), str(d)


# ---------------------------------------------------------------------------
# load_json_file / load_diff_file (importable unit tests)
# ---------------------------------------------------------------------------

def test_load_json_file_returns_list(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps(SAMPLE_INGREDIENTS))
    assert load_json_file(str(p)) == SAMPLE_INGREDIENTS

def test_load_json_file_treats_empty_object_as_list(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}")
    assert load_json_file(str(p)) == []

def test_load_diff_file_returns_false_when_missing(tmp_path):
    data, found = load_diff_file(str(tmp_path / "nope.json"))
    assert not found
    assert data == []

def test_load_diff_file_returns_true_when_present(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps(SAMPLE_INGREDIENTS))
    data, found = load_diff_file(str(p))
    assert found
    assert data == SAMPLE_INGREDIENTS


# ---------------------------------------------------------------------------
# apply_deletes (importable unit tests)
# ---------------------------------------------------------------------------

def test_apply_deletes_removes_matching_row(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE t (name TEXT)")
    conn.execute("INSERT INTO t VALUES ('A')")
    conn.execute("INSERT INTO t VALUES ('B')")
    conn.commit()
    apply_deletes(conn.cursor(), 't', [{"name": "A"}], 'name')
    conn.commit()
    rows = [r[0] for r in conn.execute("SELECT name FROM t").fetchall()]
    assert rows == ['B']
    conn.close()

def test_apply_deletes_no_match_is_noop(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE t (name TEXT)")
    conn.execute("INSERT INTO t VALUES ('A')")
    conn.commit()
    apply_deletes(conn.cursor(), 't', [{"name": "Z"}], 'name')
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    conn.close()


# ---------------------------------------------------------------------------
# apply_deletes_effects — NULL-safe (importable unit tests)
# ---------------------------------------------------------------------------

def test_apply_deletes_effects_removes_named_effect(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE eff (name TEXT, effect TEXT)")
    conn.execute("INSERT INTO eff VALUES ('A', 'Drain Intelligence')")
    conn.execute("INSERT INTO eff VALUES ('A', 'Resist Poison')")
    conn.commit()
    apply_deletes_effects(conn.cursor(), 'eff', [{"name": "A", "effect": "Drain Intelligence"}])
    conn.commit()
    rows = conn.execute("SELECT effect FROM eff WHERE name='A'").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Resist Poison"
    conn.close()

def test_apply_deletes_effects_null_safe(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE TABLE eff (name TEXT, effect TEXT)")
    conn.execute("INSERT INTO eff VALUES ('A', NULL)")
    conn.execute("INSERT INTO eff VALUES ('A', 'Drain Intelligence')")
    conn.commit()
    apply_deletes_effects(conn.cursor(), 'eff', [{"name": "A", "effect": None}])
    conn.commit()
    rows = conn.execute("SELECT effect FROM eff WHERE name='A'").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Drain Intelligence"
    conn.close()


# ---------------------------------------------------------------------------
# Subprocess: ingredients script (full flow)
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
    assert [r[0] for r in rows] == ["Alit Hide", "Ash Yam"]

def test_ingredients_no_diff_files_is_noop(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    exists = conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{TABLE_ING}'"
    ).fetchone()
    conn.close()
    assert exists is None

def test_ingredients_upsert_adds_new_row(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    # First run: create table
    write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    # Second run: upsert one new row
    new_row = [{"name": "Bittergreen Petals", "weight": 0.1, "value": 5, "ID": "ingred_bg_01"}]
    write_diff_pair(tmp_path, "ingredients", new_row, {})
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_ING}").fetchone()[0]
    conn.close()
    assert count == 3

def test_ingredients_delete_removes_row(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    # Delete one row
    write_diff_pair(tmp_path, "ingredients", {}, [{"name": "Ash Yam"}])
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    names = [r[0] for r in conn.execute(f"SELECT name FROM {TABLE_ING}").fetchall()]
    conn.close()
    assert "Ash Yam" not in names
    assert "Alit Hide" in names

def test_ingredients_diff_files_removed_after_success(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    u, d = write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert not Path(u).exists()
    assert not Path(d).exists()

def test_ingredients_invalid_upsert_json_exits_nonzero(tmp_path, tmp_db):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    (tmp_path / "ingredients.upsert.json").write_text("not json {{")
    (tmp_path / "ingredients.delete.json").write_text("{}")
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode != 0

def test_ingredients_bad_db_path_exits_nonzero(tmp_path):
    json_file = tmp_path / "ingredients.json"
    json_file.write_text(json.dumps(SAMPLE_INGREDIENTS))
    write_diff_pair(tmp_path, "ingredients", SAMPLE_INGREDIENTS, {})
    result = run_script(INGREDIENTS_SCRIPT, [str(json_file), "/nonexistent_dir/db.sqlite3"])
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# Subprocess: effects script (full flow)
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
    assert ("Alit Hide", "Drain Intelligence") in rows

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
    exists = conn.execute(
        f"SELECT name FROM sqlite_master WHERE name='{TABLE_EFF}'"
    ).fetchone()
    conn.close()
    assert exists is None

def test_effects_delete_removes_null_effect(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    write_diff_pair(tmp_path, "effects", SAMPLE_EFFECTS, {})
    run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    # Delete removes ALL rows matching (name, effect) since there is no row-level unique key.
    # Both NULL rows share the same (name=Alit Hide, effect=None) key, so one delete entry
    # removes all of them.
    write_diff_pair(tmp_path, "effects", {}, [{"name": "Alit Hide", "effect": None}])
    result = run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(tmp_db)
    nulls = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE_EFF} WHERE effect IS NULL"
    ).fetchone()[0]
    conn.close()
    assert nulls == 0

def test_effects_invalid_upsert_json_exits_nonzero(tmp_path, tmp_db):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(SAMPLE_EFFECTS))
    (tmp_path / "effects.upsert.json").write_text("{bad}")
    (tmp_path / "effects.delete.json").write_text("{}")
    result = run_script(EFFECTS_SCRIPT, [str(json_file), tmp_db])
    assert result.returncode != 0
