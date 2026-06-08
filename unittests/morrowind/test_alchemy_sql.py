"""Subprocess tests for Morrowind alchemy SQL loader scripts.

These scripts have no importable functions (all logic is in __main__), so we
test them by running them as subprocesses with temp data files.
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
INGREDIENTS_SCRIPT = str(REPO_ROOT / "Morrowind/alchemy/ingredients_sql/create_morrowind_alchemy_ingredients.py")
EFFECTS_SCRIPT = str(REPO_ROOT / "Morrowind/alchemy/ingredients_sql/create_morrowind_alchemy_effects.py")

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
        capture_output=True, text=True
    )


# ---------------------------------------------------------------------------
# create_morrowind_alchemy_ingredients.py
# ---------------------------------------------------------------------------

def test_ingredients_creates_table_and_inserts_rows(tmp_path, tmp_db):
    json_file = str(tmp_path / "ingredients.json")
    Path(json_file).write_text(json.dumps(SAMPLE_INGREDIENTS))
    result = run_script(INGREDIENTS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute("SELECT name FROM morrowind_alchemy_ingredients ORDER BY name").fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][0] == "Alit Hide"

def test_ingredients_idempotent_on_rerun(tmp_path, tmp_db):
    json_file = str(tmp_path / "ingredients.json")
    Path(json_file).write_text(json.dumps(SAMPLE_INGREDIENTS))
    run_script(INGREDIENTS_SCRIPT, [json_file, tmp_db])
    run_script(INGREDIENTS_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM morrowind_alchemy_ingredients").fetchone()[0]
    conn.close()
    assert count == len(SAMPLE_INGREDIENTS)

def test_ingredients_invalid_json_exits_nonzero(tmp_path, tmp_db):
    bad_json = str(tmp_path / "bad.json")
    Path(bad_json).write_text("not valid json {{")
    result = run_script(INGREDIENTS_SCRIPT, [bad_json, tmp_db])
    assert result.returncode != 0

def test_ingredients_missing_file_exits_nonzero(tmp_db):
    result = run_script(INGREDIENTS_SCRIPT, ["/nonexistent/file.json", tmp_db])
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# create_morrowind_alchemy_effects.py
# ---------------------------------------------------------------------------

def test_effects_creates_table_and_inserts_rows(tmp_path, tmp_db):
    json_file = str(tmp_path / "effects.json")
    Path(json_file).write_text(json.dumps(SAMPLE_EFFECTS))
    result = run_script(EFFECTS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute("SELECT name, effect FROM morrowind_alchemy_effects").fetchall()
    conn.close()
    assert len(rows) == 4
    assert ("Alit Hide", "Drain Intelligence") in rows

def test_effects_null_effect_stored_as_null(tmp_path, tmp_db):
    json_file = str(tmp_path / "effects.json")
    Path(json_file).write_text(json.dumps(SAMPLE_EFFECTS))
    run_script(EFFECTS_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    nulls = conn.execute(
        "SELECT COUNT(*) FROM morrowind_alchemy_effects WHERE effect IS NULL"
    ).fetchone()[0]
    conn.close()
    assert nulls == 2

def test_effects_invalid_json_exits_nonzero(tmp_path, tmp_db):
    bad_json = str(tmp_path / "bad.json")
    Path(bad_json).write_text("{bad}")
    result = run_script(EFFECTS_SCRIPT, [bad_json, tmp_db])
    assert result.returncode != 0

def test_effects_missing_file_exits_nonzero(tmp_db):
    result = run_script(EFFECTS_SCRIPT, ["/nonexistent/file.json", tmp_db])
    assert result.returncode != 0
