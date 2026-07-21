"""Tests for Skyrim/alchemy/ingredients_json/skyrim_parse_wiki_to_json.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "TES/Skyrim/alchemy/ingredients_json/skyrim_parse_wiki_to_json.py",
    "sk_alchemy_parse",
)
remove_pipe = _mod.remove_pipe
remove_wiki_link = _mod.remove_wiki_link
load_effects_raw = _mod.load_effects_raw
parse = _mod.parse
write_file = _mod.write_file
write_diff_files = _mod.write_diff_files

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

def test_write_diff_files_bad_path_raises():
    with pytest.raises(OSError):
        write_diff_files("/nonexistent_dir_xyz/out.json", [], [])


# ---------------------------------------------------------------------------
# load_effects_raw
# ---------------------------------------------------------------------------

SAMPLE_EFFECTS_RAW = {
    "Weakness to Frost": {"base_cost": 0.5, "base_mag": 3, "base_dur": 30},
    "Fortify Sneak":     {"base_cost": 0.5, "base_mag": 4, "base_dur": 60},
    "Weakness to Poison":{"base_cost": 1.0, "base_mag": 2, "base_dur": 30},
    "Fortify Restoration":{"base_cost": 0.5, "base_mag": 4, "base_dur": 60},
}

def test_load_effects_raw_returns_lowercase_keyed_base_mag(tmp_path):
    import json as _json
    p = tmp_path / "effects_raw.json"
    p.write_text(_json.dumps(SAMPLE_EFFECTS_RAW))
    result = load_effects_raw(str(p))
    assert result["weakness to frost"] == 3
    assert result["fortify sneak"] == 4

def test_load_effects_raw_missing_file_returns_empty(tmp_path):
    result = load_effects_raw(str(tmp_path / "nonexistent.json"))
    assert result == {}

def test_load_effects_raw_invalid_json_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    assert load_effects_raw(str(p)) == {}


# ---------------------------------------------------------------------------
# parse — base_magnitude
# ---------------------------------------------------------------------------

def test_parse_effects_always_have_base_magnitude_key(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f))
    for row in eff:
        assert 'base_magnitude' in row

def test_parse_effects_base_magnitude_none_without_lookup(tmp_path):
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f))
    assert all(row['base_magnitude'] is None for row in eff)

def test_parse_effects_base_magnitude_populated_with_lookup(tmp_path):
    import json as _json
    raw = tmp_path / "effects_raw.json"
    raw.write_text(_json.dumps(SAMPLE_EFFECTS_RAW))
    lookup = load_effects_raw(str(raw))
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f), effects_lookup=lookup)
    mags = {row['effect']: row['base_magnitude'] for row in eff}
    assert mags['Weakness to Frost'] == 3
    assert mags['Fortify Sneak'] == 4
    assert mags['Weakness to Poison'] == 2
    assert mags['Fortify Restoration'] == 4

def test_parse_effects_unknown_effect_base_magnitude_none(tmp_path):
    import json as _json
    # lookup with only one of the four effects in VALID_ENTRY
    raw = tmp_path / "effects_raw.json"
    raw.write_text(_json.dumps({"Weakness to Frost": {"base_cost": 0.5, "base_mag": 3, "base_dur": 30}}))
    lookup = load_effects_raw(str(raw))
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f), effects_lookup=lookup)
    mags = {row['effect']: row['base_magnitude'] for row in eff}
    assert mags['Weakness to Frost'] == 3
    assert mags['Fortify Sneak'] is None

def test_parse_effects_lookup_case_insensitive(tmp_path):
    import json as _json
    # UESP uses "Fortify Sneak" — same case here, but test the lower() path
    raw = tmp_path / "effects_raw.json"
    raw.write_text(_json.dumps({"fortify sneak": {"base_cost": 0.5, "base_mag": 4, "base_dur": 60}}))
    # load_effects_raw lowercases keys, so this won't match "Fortify Sneak" from raw
    # because load_effects_raw expects the wiki format, not pre-lowered.
    # But if we pass a pre-built lookup with lowercase keys, parse() still matches.
    lookup = {"fortify sneak": 4}
    f = tmp_path / "raw.txt"
    f.write_text(VALID_ENTRY)
    _, eff = parse(str(f), effects_lookup=lookup)
    mags = {row['effect']: row['base_magnitude'] for row in eff}
    assert mags['Fortify Sneak'] == 4


# ---------------------------------------------------------------------------
# parse — error conditions
# ---------------------------------------------------------------------------

# Malformed entry: weight field (line 6 in Skyrim format) is not a float
MALFORMED_WEIGHT_ENTRY = """|
|Bad Ingredient
|Effect1
|Effect2
|Effect3
|Effect4
|NOT_A_FLOAT
|5
|Location
|ingred_bad_01
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
