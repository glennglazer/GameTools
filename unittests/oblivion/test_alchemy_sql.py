"""Subprocess tests for Oblivion alchemy SQL loader scripts."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
INGREDIENTS_SCRIPT = str(REPO_ROOT / "Oblivion/alchemy/ingredients_sql/create_oblivion_alchemy_ingredients.py")
EFFECTS_SCRIPT = str(REPO_ROOT / "Oblivion/alchemy/ingredients_sql/create_oblivion_alchemy_effects.py")

SAMPLE_INGREDIENTS = [
    {"name": "Alkanet Flower", "weight": 0.1, "value": 1, "ID": "0003365C"},
    {"name": "Boar Meat", "weight": 2.0, "value": 1, "ID": "0003AB19"},
]

SAMPLE_EFFECTS = [
    {"name": "Alkanet Flower", "effect": "Restore Intelligence"},
    {"name": "Alkanet Flower", "effect": "Resist Poison"},
    {"name": "Alkanet Flower", "effect": None},
    {"name": "Alkanet Flower", "effect": None},
]


def run_script(script, args):
    return subprocess.run(
        [sys.executable, script] + args,
        capture_output=True, text=True
    )


# ---------------------------------------------------------------------------
# create_oblivion_alchemy_ingredients.py
# ---------------------------------------------------------------------------

def test_ingredients_creates_table_and_inserts_rows(tmp_path, tmp_db):
    json_file = str(tmp_path / "ingredients.json")
    Path(json_file).write_text(json.dumps(SAMPLE_INGREDIENTS))
    result = run_script(INGREDIENTS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute("SELECT name FROM oblivion_alchemy_ingredients ORDER BY name").fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][0] == "Alkanet Flower"

def test_ingredients_idempotent_on_rerun(tmp_path, tmp_db):
    json_file = str(tmp_path / "ingredients.json")
    Path(json_file).write_text(json.dumps(SAMPLE_INGREDIENTS))
    run_script(INGREDIENTS_SCRIPT, [json_file, tmp_db])
    run_script(INGREDIENTS_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT COUNT(*) FROM oblivion_alchemy_ingredients").fetchone()[0]
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
# create_oblivion_alchemy_effects.py
# ---------------------------------------------------------------------------

def test_effects_creates_table_and_inserts_rows(tmp_path, tmp_db):
    json_file = str(tmp_path / "effects.json")
    Path(json_file).write_text(json.dumps(SAMPLE_EFFECTS))
    result = run_script(EFFECTS_SCRIPT, [json_file, tmp_db])
    assert result.returncode == 0
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute("SELECT name, effect FROM oblivion_alchemy_effects").fetchall()
    conn.close()
    assert len(rows) == 4
    assert ("Alkanet Flower", "Restore Intelligence") in rows

def test_effects_null_effect_stored_as_null(tmp_path, tmp_db):
    json_file = str(tmp_path / "effects.json")
    Path(json_file).write_text(json.dumps(SAMPLE_EFFECTS))
    run_script(EFFECTS_SCRIPT, [json_file, tmp_db])
    conn = sqlite3.connect(tmp_db)
    nulls = conn.execute(
        "SELECT COUNT(*) FROM oblivion_alchemy_effects WHERE effect IS NULL"
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
