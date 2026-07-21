"""Unit tests for oblivion_parse_souls.py"""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Oblivion" / "enchanting" / "souls_json"))
from oblivion_parse_souls import parse_mapping, parse_souls, FIXED_LEVELS

MAPPING_HTML = """
<div class="mw-parser-output">
<table class="wikitable">
<tr><th>Soul Level</th><th>Soul Strength</th></tr>
<tr><td><b>Petty</b></td><td>150</td></tr>
<tr><td><b>Lesser</b></td><td>300</td></tr>
<tr><td><b>Common</b></td><td>800</td></tr>
<tr><td><b>Greater</b></td><td>1200</td></tr>
<tr><td><b>Grand</b></td><td>1600</td></tr>
<tr><td><b>Black</b></td><td>1600</td></tr>
</table>
</div>
"""

CREATURES_HTML = """
<div class="mw-parser-output">
<div style="display:inline-table">
<table class="sortable wikitable">
<tr><th>Creature</th><th>Soul Level</th></tr>
<tr><td>Deer</td><td data-sort-value="1">Petty</td></tr>
<tr><td>Scamp</td><td data-sort-value="2">Lesser</td></tr>
<tr><td>Clannfear</td><td data-sort-value="3">Common</td></tr>
<tr><td>Frost Atronach</td><td data-sort-value="4">Greater</td></tr>
<tr><td>Gloom Wraith</td><td data-sort-value="4.7">Grand</td></tr>
<tr><td>Dremora</td><td data-sort-value="6">Black</td></tr>
<tr><td>NPC(any race)</td><td data-sort-value="6">Black</td></tr>
<tr><td>Vampire</td><td data-sort-value="6">Black</td></tr>
<tr><td>Ghost</td><td data-sort-value="1.5">Pty/LsrL:-1</td></tr>
<tr><td>Goblin Shaman</td><td>leveledL:-5</td></tr>
</table>
</div>
</div>
"""


def test_mapping_parses_all_six_levels():
    mapping = parse_mapping(MAPPING_HTML)
    assert set(mapping.keys()) == {"Petty", "Lesser", "Common", "Greater", "Grand", "Black"}


def test_mapping_values_are_integers():
    mapping = parse_mapping(MAPPING_HTML)
    assert mapping["Petty"] == 150
    assert mapping["Lesser"] == 300
    assert mapping["Common"] == 800
    assert mapping["Greater"] == 1200
    assert mapping["Grand"] == 1600
    assert mapping["Black"] == 1600


def test_fixed_creatures_included():
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(CREATURES_HTML, mapping)
    names = [r["name"] for r in records]
    assert "Deer" in names
    assert "Clannfear" in names
    assert "Gloom Wraith" in names


def test_black_souls_included():
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(CREATURES_HTML, mapping)
    names = [r["name"] for r in records]
    assert "Dremora" in names
    assert "NPC(any race)" in names
    assert "Vampire" in names


def test_black_soul_size_is_1600():
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(CREATURES_HTML, mapping)
    black = {r["name"]: r["soul_size"] for r in records
             if r["name"] in {"Dremora", "NPC(any race)", "Vampire"}}
    assert all(v == 1600 for v in black.values())


def test_leveled_souls_excluded():
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(CREATURES_HTML, mapping)
    names = [r["name"] for r in records]
    assert "Ghost" not in names
    assert "Goblin Shaman" not in names


def test_soul_sizes_are_integers():
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(CREATURES_HTML, mapping)
    for r in records:
        assert isinstance(r["soul_size"], int)


def test_correct_size_mapping():
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(CREATURES_HTML, mapping)
    by_name = {r["name"]: r["soul_size"] for r in records}
    assert by_name["Deer"] == 150
    assert by_name["Scamp"] == 300
    assert by_name["Frost Atronach"] == 1200


def test_deduplication():
    dupe_html = """
    <div><table class="wikitable">
    <tr><th>Creature</th><th>Soul Level</th></tr>
    <tr><td>Deer</td><td>Petty</td></tr>
    <tr><td>Deer</td><td>Petty</td></tr>
    </table></div>
    """
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(dupe_html, mapping)
    assert len([r for r in records if r["name"] == "Deer"]) == 1


def test_all_four_tables_parsed():
    multi_table_html = """
    <div>
    <table class="wikitable"><tr><th>Creature</th><th>Soul Level</th></tr>
    <tr><td>Deer</td><td>Petty</td></tr></table>
    <table class="wikitable"><tr><th>Creature</th><th>Soul Level</th></tr>
    <tr><td>Unicorn</td><td>Greater</td></tr></table>
    </div>
    """
    mapping = parse_mapping(MAPPING_HTML)
    records = parse_souls(multi_table_html, mapping)
    names = [r["name"] for r in records]
    assert "Deer" in names
    assert "Unicorn" in names
