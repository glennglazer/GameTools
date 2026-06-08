"""Tests for Morrowind/alchemy/ingredients_parse/morrowind_parse_wiki_to_json.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "Morrowind/alchemy/ingredients_parse/morrowind_parse_wiki_to_json.py",
    "mw_alchemy_parse",
)
remove_pipe = _mod.remove_pipe
remove_wiki_link = _mod.remove_wiki_link
dash_to_null = _mod.dash_to_null
parse = _mod.parse
write_file = _mod.write_file

# One well-formed Morrowind wiki entry (9 lines: blank|name|weight|value|e1|e2|e3|e4|ID)
VALID_ENTRY = """|
|Alit Hide
|1.0
|5
|Drain Intelligence
|Resist Poison
|Telekinesis
|Detect Animal
|ingred_alit_hide_01
"""

WIKI_LINK_ENTRY = """|
|Bungler's Bane
|1.0
|5
|Drain Speed
|Bungler's Bane (Morrowind)|Blight
|-
|-
|ingred_bunglers_bane_01
"""


# ---------------------------------------------------------------------------
# remove_pipe
# ---------------------------------------------------------------------------

def test_remove_pipe_strips_leading_pipe():
    assert remove_pipe("|Alit Hide") == "Alit Hide"

def test_remove_pipe_no_pipe_returns_unchanged():
    assert remove_pipe("No pipe") == "No pipe"

def test_remove_pipe_none_returns_none():
    assert remove_pipe(None) is None

def test_remove_pipe_multiple_leading_pipes_all_stripped():
    assert remove_pipe("||double") == "double"


# ---------------------------------------------------------------------------
# remove_wiki_link
# ---------------------------------------------------------------------------

def test_remove_wiki_link_extracts_display_name():
    assert remove_wiki_link("Resist Poison (Morrowind)|Resist Poison") == "Resist Poison"

def test_remove_wiki_link_no_pipe_returns_unchanged():
    assert remove_wiki_link("Drain Intelligence") == "Drain Intelligence"

def test_remove_wiki_link_none_returns_none():
    assert remove_wiki_link(None) is None


# ---------------------------------------------------------------------------
# dash_to_null
# ---------------------------------------------------------------------------

def test_dash_to_null_single_dash_returns_none():
    assert dash_to_null("-") is None

def test_dash_to_null_effect_name_unchanged():
    assert dash_to_null("Drain Intelligence") == "Drain Intelligence"

def test_dash_to_null_hyphen_in_word_returns_none():
    # documents current behavior: any '-' in string → None
    assert dash_to_null("anti-magic") is None


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
    assert ing[0]["name"] == "Alit Hide"
    assert ing[0]["weight"] == 1.0
    assert ing[0]["value"] == 5
    assert ing[0]["ID"] == "ingred_alit_hide_01"

def test_parse_single_entry_effects(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f))
    effect_names = [e["effect"] for e in eff]
    assert "Drain Intelligence" in effect_names
    assert "Resist Poison" in effect_names
    assert "Telekinesis" in effect_names
    assert "Detect Animal" in effect_names

def test_parse_wiki_link_in_effect_resolved(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(WIKI_LINK_ENTRY)
    _, eff = parse(str(f))
    effect_names = [e["effect"] for e in eff]
    assert "Blight" in effect_names
    assert "Drain Speed" in effect_names

def test_parse_dash_effect_becomes_none(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(WIKI_LINK_ENTRY)
    _, eff = parse(str(f))
    assert None in [e["effect"] for e in eff]

def test_parse_two_entries(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY + VALID_ENTRY)
    ing, eff = parse(str(f))
    assert len(ing) == 2
    assert len(eff) == 8  # 4 effects per ingredient

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
    data = [{"name": "Alit Hide", "weight": 1.0, "value": 5, "ID": "ingred_alit_hide_01"}]
    write_file(data, outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == data

def test_write_file_overwrites_existing_file(tmp_path):
    outfile = str(tmp_path / "out.json")
    write_file([{"a": 1}], outfile)
    write_file([{"b": 2}], outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == [{"b": 2}]

def test_write_file_bad_path_raises(tmp_path):
    with pytest.raises(OSError):
        write_file([], "/nonexistent_dir_xyz/out.json")
