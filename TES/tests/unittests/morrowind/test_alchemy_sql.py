"""Unit tests for Morrowind alchemy SQL loader scripts (load helpers only)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_ing_mod = load_module(
    "TES/Morrowind/alchemy/ingredients_sql/create_or_update_morrowind_alchemy_ingredients.py",
    "mw_ing_sql",
)

load_json_file = _ing_mod.load_json_file
load_diff_file = _ing_mod.load_diff_file

SAMPLE_INGREDIENTS = [
    {"name": "Alit Hide", "weight": 1.0, "value": 5, "ID": "ingred_alit_hide_01"},
    {"name": "Ash Yam", "weight": 1.0, "value": 2, "ID": "ingred_ash_yam_01"},
]


# ---------------------------------------------------------------------------
# load_json_file / load_diff_file (unit tests — no DB)
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
