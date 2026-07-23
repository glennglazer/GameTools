"""Tests for Oblivion/alchemy/ingredients_json/oblivion_parse_wiki_to_json.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "TES/Oblivion/alchemy/ingredients_json/oblivion_parse_wiki_to_json.py",
    "ob_alchemy_parse",
)
remove_pipe = _mod.remove_pipe
remove_wiki_link = _mod.remove_wiki_link
parse = _mod.parse
load_effects_raw = _mod.load_effects_raw
write_file = _mod.write_file
write_diff_files = _mod.write_diff_files

# One well-formed Oblivion wiki entry (7 lines: blank|name|weight|value|source|effects_csv|ID)
VALID_ENTRY = """|
|Alkanet Flower
|0.1
|1
|Alkanet
|Restore Intelligence,Resist Poison,Light,Damage Fatigue
|0003365C
"""

# Entry with wiki-link effect name and fewer than 4 effects
WIKI_LINK_ENTRY = """|
|Alocasia Fruit
|0.1
|1
|Alocasia
|Alocasia Fruit (Oblivion)|Restore Fatigue,Damage Intelligence
|0003365D
"""


# ---------------------------------------------------------------------------
# remove_pipe
# ---------------------------------------------------------------------------

def test_remove_pipe_strips_leading_pipe():
    assert remove_pipe("|Alkanet Flower") == "Alkanet Flower"

def test_remove_pipe_no_pipe_returns_unchanged():
    assert remove_pipe("No pipe") == "No pipe"

def test_remove_pipe_none_returns_none():
    assert remove_pipe(None) is None


# ---------------------------------------------------------------------------
# remove_wiki_link
# ---------------------------------------------------------------------------

def test_remove_wiki_link_extracts_display_name():
    assert remove_wiki_link("Alocasia Fruit (Oblivion)|Alocasia Fruit") == "Alocasia Fruit"

def test_remove_wiki_link_no_pipe_returns_unchanged():
    assert remove_wiki_link("Restore Intelligence") == "Restore Intelligence"

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
    assert ing[0]["name"] == "Alkanet Flower"
    assert ing[0]["weight"] == 0.1
    assert ing[0]["value"] == 1
    assert ing[0]["ID"] == "0003365C"

def test_parse_single_entry_effects_all_four(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f))
    effect_names = [e["effect"] for e in eff]
    assert "Restore Intelligence" in effect_names
    assert "Resist Poison" in effect_names
    assert "Light" in effect_names
    assert "Damage Fatigue" in effect_names
    assert len(eff) == 4

def test_parse_base_cost_populated_from_lookup(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    # Restore Intelligence expands from Restore Attribute (38.0);
    # Damage Fatigue is a direct entry (4.4).
    lookup = {
        "restore intelligence": 38.0,
        "resist poison": 0.5,
        "light": 0.051,
        "damage fatigue": 4.4,
    }
    _, eff = parse(str(f), effects_lookup=lookup)
    by_effect = {e["effect"]: e["base_cost"] for e in eff}
    assert by_effect["Restore Intelligence"] == 38.0
    assert by_effect["Resist Poison"] == 0.5
    assert by_effect["Light"] == 0.051
    assert by_effect["Damage Fatigue"] == 4.4

def test_parse_base_cost_none_when_no_lookup(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f))
    for e in eff:
        if e["effect"] is not None:
            assert e["base_cost"] is None

def test_parse_fewer_effects_padded_with_none(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(WIKI_LINK_ENTRY)
    _, eff = parse(str(f))
    assert len(eff) == 4
    assert None in [e["effect"] for e in eff]

def test_parse_wiki_link_in_effects_string_resolved(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(WIKI_LINK_ENTRY)
    _, eff = parse(str(f))
    effect_names = [e["effect"] for e in eff if e["effect"] is not None]
    assert "Restore Fatigue" in effect_names

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
    data = [{"name": "Alkanet Flower", "weight": 0.1, "value": 1, "ID": "0003365C"}]
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

def test_write_diff_files_bad_path_raises():
    with pytest.raises(OSError):
        write_diff_files("/nonexistent_dir_xyz/out.json", [], [])


# ---------------------------------------------------------------------------
# parse — error conditions
# ---------------------------------------------------------------------------

MALFORMED_WEIGHT_ENTRY = """|
|Bad Ingredient
|NOT_A_FLOAT
|5
|Source
|Restore Intelligence,Resist Poison,Light,Damage Fatigue
|0003365C
"""

def test_parse_unreadable_file_raises(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    f.chmod(0o000)
    try:
        with pytest.raises(OSError):
            parse(str(f))
    finally:
        f.chmod(0o644)

def test_parse_malformed_weight_raises(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(MALFORMED_WEIGHT_ENTRY)
    with pytest.raises(ValueError):
        parse(str(f))


# ---------------------------------------------------------------------------
# load_effects_raw
# ---------------------------------------------------------------------------

SAMPLE_EFFECTS_RAW = {
    "Restore Attribute": {"base_cost": 38.0},
    "Damage Attribute": {"base_cost": 100.0},
    "Drain Attribute": {"base_cost": 0.7},
    "Fortify Attribute": {"base_cost": 0.6},
    "Absorb Attribute": {"base_cost": 0.95},
    "Restore Health": {"base_cost": 10.0},
    "Restore Fatigue": {"base_cost": 2.0},
    "Shock Damage": {"base_cost": 7.8},
    "Shock Shield": {"base_cost": 0.95},
    "Light": {"base_cost": 0.051},
}


def test_load_effects_raw_missing_file_returns_empty():
    result = load_effects_raw("/nonexistent/path/effects_raw.json")
    assert result == {}

def test_load_effects_raw_direct_entry(tmp_path):
    f = tmp_path / "effects_raw.json"
    f.write_text(json.dumps(SAMPLE_EFFECTS_RAW))
    lookup = load_effects_raw(str(f))
    assert lookup["restore health"] == 10.0
    assert lookup["restore fatigue"] == 2.0
    assert lookup["light"] == 0.051

def test_load_effects_raw_expands_restore_attribute(tmp_path):
    f = tmp_path / "effects_raw.json"
    f.write_text(json.dumps(SAMPLE_EFFECTS_RAW))
    lookup = load_effects_raw(str(f))
    for attr in ["strength", "intelligence", "willpower", "agility",
                 "speed", "endurance", "personality", "luck"]:
        assert lookup[f"restore {attr}"] == 38.0

def test_load_effects_raw_expands_damage_attribute(tmp_path):
    f = tmp_path / "effects_raw.json"
    f.write_text(json.dumps(SAMPLE_EFFECTS_RAW))
    lookup = load_effects_raw(str(f))
    assert lookup["damage agility"] == 100.0
    assert lookup["damage strength"] == 100.0

def test_load_effects_raw_shock_aliases(tmp_path):
    f = tmp_path / "effects_raw.json"
    f.write_text(json.dumps(SAMPLE_EFFECTS_RAW))
    lookup = load_effects_raw(str(f))
    assert lookup["lightning damage"] == 7.8
    assert lookup["lightning shield"] == 0.95
