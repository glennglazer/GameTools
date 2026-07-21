"""Unit tests for skyrim_parse_creature_souls_to_json.py"""
import json
import sys
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Skyrim" / "enchanting" / "creature_souls_json"))
from skyrim_parse_creature_souls_to_json import parse_mapping, parse_souls

MAPPING_HTML = """
<div class="mw-parser-output">
<table class="wikitable">
<tr><th>Soul Level</th><th>Charge Capacity</th><th>Creature Level</th></tr>
<tr><td>Petty</td><td>250</td><td>1-3</td></tr>
<tr><td>Lesser</td><td>500</td><td>4-15</td></tr>
<tr><td>Common</td><td>1000</td><td>16-27</td></tr>
<tr><td>Greater</td><td>2000</td><td>28-37</td></tr>
<tr><td>Grand</td><td>3000</td><td>38+ or NPC</td></tr>
</table>
<table class="wikitable">
<tr><th>Creature</th><th>Soul Level</th></tr>
<tr><td>Chicken</td><td>Petty</td></tr>
<tr><td>Bear</td><td>Lesser</td></tr>
<tr><td>Frost Troll</td><td>Common</td></tr>
<tr><td>Giant</td><td>Greater</td></tr>
<tr><td>Mammoth</td><td>Grand</td></tr>
<tr><td>Magic Anomaly</td><td>LeveledL:1.75x</td></tr>
<tr><td rowspan="2">Corrupted Shade</td><td>Leveled</td></tr>
<tr><td>Petty</td></tr>
<tr><td rowspan="3">Draugr Deathlord</td><td>Common</td></tr>
<tr><td>Greater</td></tr>
<tr><td>Grand</td></tr>
<tr><td>Falmer Nightprowler</td><td>Common (Shaman)</td></tr>
<tr><td rowspan="2">Frostbite Spider</td><td>Petty</td></tr>
<tr><td>Lesser</td></tr>
<tr><td>Dwarven Centurion</td><td>No soul (Resists Soul Trap)</td></tr>
</table>
</div>
"""


@pytest.fixture()
def soup():
    return BeautifulSoup(MAPPING_HTML, "html.parser")


def test_mapping_parses_all_levels(soup):
    mapping = parse_mapping(soup)
    assert set(mapping.keys()) == {"Petty", "Lesser", "Common", "Greater", "Grand"}


def test_mapping_values(soup):
    mapping = parse_mapping(soup)
    assert mapping["Petty"] == 250
    assert mapping["Grand"] == 3000


def test_fixed_souls_included(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    names = [r["name"] for r in records]
    assert "Chicken" in names
    assert "Mammoth" in names


def test_leveled_excluded(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    names = [r["name"] for r in records]
    assert "Magic Anomaly" not in names


def test_no_soul_excluded(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    names = [r["name"] for r in records]
    assert "Dwarven Centurion" not in names


def test_rowspan_leveled_filtered_fixed_kept(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    corrupted = [r for r in records if r["name"] == "Corrupted Shade"]
    assert len(corrupted) == 1
    assert corrupted[0]["soul_size"] == 250


def test_rowspan_multiple_fixed_levels(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    deathlord = sorted([r["soul_size"] for r in records if r["name"] == "Draugr Deathlord"])
    assert deathlord == [1000, 2000, 3000]


def test_parenthetical_stripped(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    nightprowler = [r for r in records if r["name"] == "Falmer Nightprowler"]
    assert len(nightprowler) == 1
    assert nightprowler[0]["soul_size"] == 1000


def test_rowspan_two_fixed_levels(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    spider = sorted([r["soul_size"] for r in records if r["name"] == "Frostbite Spider"])
    assert spider == [250, 500]


def test_npc_black_soul_added(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    npc = [r for r in records if r["name"] == "NPC"]
    assert len(npc) == 1
    assert npc[0]["soul_size"] == 3000


def test_soul_sizes_are_integers(soup):
    mapping = parse_mapping(soup)
    records = parse_souls(soup, mapping)
    for r in records:
        assert isinstance(r["soul_size"], int)
