"""Tests for Skyrim/alchemy/ingredients_parse/skyrim_parse_wiki_to_json.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Skyrim/alchemy/ingredients_parse/skyrim_parse_wiki_to_json.py",
    "sk_alchemy_parse",
)
remove_pipe = _mod.remove_pipe
remove_wiki_link = _mod.remove_wiki_link
parse = _mod.parse
write_file = _mod.write_file

# One well-formed Skyrim entry (10 lines: blank|name|e1|e2|e3|e4|weight|value|location|ID)
VALID_ENTRY = """|
|Abecean Longfin
|Weakness to Frost (Skyrim)|Weakness to Frost
|Fortify Sneak
|Weakness to Poison (Skyrim)|Weakness to Poison
|Fortify Restoration
|0.5
|15
|Lakes, rivers, streams
|00106E1B
"""

PLAIN_ENTRY = """|
|Bear Claws
|Restore Stamina
|Fortify Health
|Fortify One-handed
|Damage Magicka Regen
|0.1
|3
|Bears
|0003AD57
"""


# ---------------------------------------------------------------------------
# remove_pipe
# ---------------------------------------------------------------------------

def test_remove_pipe_strips_leading_pipe():
    assert remove_pipe("|Abecean Longfin") == "Abecean Longfin"

def test_remove_pipe_no_pipe_returns_unchanged():
    assert remove_pipe("No pipe") == "No pipe"

def test_remove_pipe_none_returns_none():
    assert remove_pipe(None) is None


# ---------------------------------------------------------------------------
# remove_wiki_link
# ---------------------------------------------------------------------------

def test_remove_wiki_link_extracts_display_name():
    assert remove_wiki_link("Weakness to Frost (Skyrim)|Weakness to Frost") == "Weakness to Frost"

def test_remove_wiki_link_no_pipe_returns_unchanged():
    assert remove_wiki_link("Fortify Sneak") == "Fortify Sneak"

def test_remove_wiki_link_none_returns_none():
    assert remove_wiki_link(None) is None


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------

def test_parse_nonexistent_file_returns_empty_dicts():
    ing, eff = parse("/nonexistent/path/to/file.txt")
    assert ing == {}
    assert eff == {}

def test_parse_single_entry_ingredient_fields(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    ing, _ = parse(str(f))
    assert len(ing) == 1
    assert ing[0]["name"] == "Abecean Longfin"
    assert ing[0]["weight"] == 0.5
    assert ing[0]["value"] == 15
    assert ing[0]["ID"] == "00106E1B"

def test_parse_single_entry_all_four_effects(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(PLAIN_ENTRY)
    _, eff = parse(str(f))
    effect_names = [e["effect"] for e in eff]
    assert "Restore Stamina" in effect_names
    assert "Fortify Health" in effect_names
    assert "Fortify One-handed" in effect_names
    assert "Damage Magicka Regen" in effect_names
    assert len(eff) == 4

def test_parse_wiki_link_effects_resolved(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f))
    effect_names = [e["effect"] for e in eff]
    assert "Weakness to Frost" in effect_names
    assert "Weakness to Poison" in effect_names
    assert "Fortify Sneak" in effect_names
    assert "Fortify Restoration" in effect_names

def test_parse_two_entries(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY + VALID_ENTRY)
    ing, eff = parse(str(f))
    assert len(ing) == 2
    assert len(eff) == 8

def test_parse_empty_file_returns_empty_lists(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text("")
    ing, eff = parse(str(f))
    assert ing == []
    assert eff == []


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

def test_write_file_creates_valid_json(tmp_path):
    outfile = str(tmp_path / "out.json")
    data = [{"name": "Abecean Longfin", "weight": 0.5, "value": 15, "ID": "00106E1B"}]
    write_file(data, outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == data

def test_write_file_overwrites_existing_file(tmp_path):
    outfile = str(tmp_path / "out.json")
    write_file([{"a": 1}], outfile)
    write_file([{"b": 2}], outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == [{"b": 2}]

def test_write_file_bad_path_raises():
    with pytest.raises(OSError):
        write_file([], "/nonexistent_dir_xyz/out.json")
