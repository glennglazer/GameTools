"""Tests for compute_diff / load_json_safe / write_diff_files.

These helpers are identical in all five *_to_json.py scripts. We test them
via the Morrowind alchemy script as the representative; the others share the
same code so a single test suite is sufficient.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Morrowind/alchemy/ingredients_json/morrowind_parse_wiki_to_json.py",
    "mw_json_diff",
)
compute_diff = _mod.compute_diff
load_json_safe = _mod.load_json_safe
write_diff_files = _mod.write_diff_files


# ---------------------------------------------------------------------------
# load_json_safe
# ---------------------------------------------------------------------------

def test_load_json_safe_returns_list_for_valid_file(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps([{"name": "Alit Hide"}]))
    assert load_json_safe(str(p)) == [{"name": "Alit Hide"}]

def test_load_json_safe_returns_empty_list_for_missing_file():
    assert load_json_safe("/nonexistent_dir_xyz/missing.json") == []

def test_load_json_safe_returns_empty_list_for_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json {{{")
    assert load_json_safe(str(p)) == []

def test_load_json_safe_returns_empty_list_for_empty_file(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("")
    assert load_json_safe(str(p)) == []


# ---------------------------------------------------------------------------
# compute_diff — keyed by 'name'
# ---------------------------------------------------------------------------

def _key(r):
    return r['name']

def test_compute_diff_identical_data_produces_no_changes():
    data = [{"name": "A", "weight": 1.0}, {"name": "B", "weight": 2.0}]
    upsert, delete = compute_diff(data, data, _key)
    assert upsert == []
    assert delete == []

def test_compute_diff_new_row_appears_in_upsert():
    old = [{"name": "A", "weight": 1.0}]
    new = [{"name": "A", "weight": 1.0}, {"name": "B", "weight": 2.0}]
    upsert, delete = compute_diff(old, new, _key)
    assert len(upsert) == 1
    assert upsert[0]["name"] == "B"
    assert delete == []

def test_compute_diff_removed_row_appears_in_delete():
    old = [{"name": "A"}, {"name": "B"}]
    new = [{"name": "A"}]
    upsert, delete = compute_diff(old, new, _key)
    assert upsert == []
    assert len(delete) == 1
    assert delete[0]["name"] == "B"

def test_compute_diff_changed_row_appears_in_upsert_not_delete():
    old = [{"name": "A", "weight": 1.0}]
    new = [{"name": "A", "weight": 9.9}]
    upsert, delete = compute_diff(old, new, _key)
    assert len(upsert) == 1
    assert upsert[0]["weight"] == 9.9
    assert delete == []

def test_compute_diff_empty_old_all_new_are_upsert():
    new = [{"name": "A"}, {"name": "B"}]
    upsert, delete = compute_diff([], new, _key)
    assert len(upsert) == 2
    assert delete == []

def test_compute_diff_empty_new_all_old_are_delete():
    old = [{"name": "A"}, {"name": "B"}]
    upsert, delete = compute_diff(old, [], _key)
    assert upsert == []
    assert len(delete) == 2

def test_compute_diff_both_empty_produces_no_changes():
    upsert, delete = compute_diff([], [], _key)
    assert upsert == []
    assert delete == []


# ---------------------------------------------------------------------------
# write_diff_files
# ---------------------------------------------------------------------------

def test_write_diff_files_creates_both_files(tmp_path):
    outfile = str(tmp_path / "foo.json")
    Path(outfile).write_text("[]")
    write_diff_files(outfile, [{"name": "A"}], [{"name": "B"}])
    assert (tmp_path / "foo.upsert.json").exists()
    assert (tmp_path / "foo.delete.json").exists()

def test_write_diff_files_upsert_content_correct(tmp_path):
    outfile = str(tmp_path / "ing.json")
    Path(outfile).write_text("[]")
    upsert = [{"name": "New"}]
    write_diff_files(outfile, upsert, [])
    loaded = json.loads((tmp_path / "ing.upsert.json").read_text())
    assert loaded == upsert

def test_write_diff_files_empty_upsert_writes_empty_object(tmp_path):
    outfile = str(tmp_path / "ing.json")
    Path(outfile).write_text("[]")
    write_diff_files(outfile, [], [{"name": "Gone"}])
    loaded = json.loads((tmp_path / "ing.upsert.json").read_text())
    assert loaded == {}

def test_write_diff_files_empty_delete_writes_empty_object(tmp_path):
    outfile = str(tmp_path / "ing.json")
    Path(outfile).write_text("[]")
    write_diff_files(outfile, [{"name": "New"}], [])
    loaded = json.loads((tmp_path / "ing.delete.json").read_text())
    assert loaded == {}

def test_write_diff_files_stem_naming(tmp_path):
    outfile = str(tmp_path / "morrowind_all_ingredients.json")
    Path(outfile).write_text("[]")
    write_diff_files(outfile, [], [])
    assert (tmp_path / "morrowind_all_ingredients.upsert.json").exists()
    assert (tmp_path / "morrowind_all_ingredients.delete.json").exists()


# ---------------------------------------------------------------------------
# Default path constants point at the right sibling directories
# ---------------------------------------------------------------------------

def test_default_infile_points_to_parse_dir():
    expected = REPO_ROOT / 'Morrowind' / 'alchemy' / 'ingredients_parse' / 'morrowind_all_ingredients_raw.txt'
    assert Path(_mod._DEFAULT_INFILE) == expected

def test_default_ing_file_points_to_json_dir():
    expected = REPO_ROOT / 'Morrowind' / 'alchemy' / 'ingredients_json' / 'morrowind_all_ingredients.json'
    assert Path(_mod._DEFAULT_ING_FILE) == expected

def test_default_eff_file_points_to_json_dir():
    expected = REPO_ROOT / 'Morrowind' / 'alchemy' / 'ingredients_json' / 'morrowind_all_effects.json'
    assert Path(_mod._DEFAULT_EFF_FILE) == expected
