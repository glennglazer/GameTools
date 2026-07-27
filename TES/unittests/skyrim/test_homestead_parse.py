"""Tests for homestead JSON parsers."""
import json
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_build = load_module(
    "TES/Skyrim/homestead/build_json/skyrim_parse_homestead_build.py",
    "sk_homestead_build",
)
_excl = load_module(
    "TES/Skyrim/homestead/exclusive_exterior_json/skyrim_parse_homestead_exclusive_exterior.py",
    "sk_homestead_excl",
)
_cost = load_module(
    "TES/Skyrim/homestead/steward_cost_json/skyrim_parse_homestead_steward_cost.py",
    "sk_homestead_cost",
)

parse_item_table = _build.parse_item_table
parse_construction_table = _build.parse_construction_table
parse_shrine_bullet = _build.parse_shrine_bullet
parse_steward_costs = _cost.parse_steward_costs

EXCL_RECORDS = _excl.RECORDS

# ── helpers ──────────────────────────────────────────────────────────────────

def soup(html):
    return BeautifulSoup(html, "html.parser")


def mat(record, *cols):
    """Return a dict of only the requested material columns from a record."""
    return {c: record[c] for c in cols if c in record}


# ── parse_item_table ──────────────────────────────────────────────────────────

ITEM_TABLE_HTML = """
<table class="wikitable">
<tr><th>Item</th><th>Sawn Log</th><th>Nails</th><th>Iron Ingot</th></tr>
<tr><th>Barrel</th><td>1</td><td>1</td><td>1</td></tr>
<tr><th>Barrel</th><td>1</td><td>1</td><td>1</td></tr>
<tr><th>Chest</th><td>1</td><td>1</td><td>-</td></tr>
<tr><th>Total</th><th>3</th><th>3</th><th>2</th></tr>
</table>
"""


def test_item_table_basic_record():
    rows = parse_item_table(soup(ITEM_TABLE_HTML), "Cellar_Containers")
    chest = next(r for r in rows if r["section"] == "Chest")
    assert chest["location"] == "Cellar_Containers"
    assert chest["stage"] is None
    assert chest["batch_size"] is None
    assert chest["sawn_log"] == 1
    assert chest["nails"] == 1
    assert chest["iron_ingot"] == 0


def test_item_table_skips_total():
    rows = parse_item_table(soup(ITEM_TABLE_HTML), "Cellar_Containers")
    assert not any(r["section"].lower() == "total" for r in rows)


def test_item_table_enumerates_duplicates():
    rows = parse_item_table(soup(ITEM_TABLE_HTML), "Cellar_Containers")
    sections = [r["section"] for r in rows]
    assert "Barrel_1" in sections
    assert "Barrel_2" in sections
    assert "Barrel" not in sections


def test_item_table_th_values_also_parsed():
    """Some rows use <th> for value cells instead of <td>."""
    html = """
    <table class="wikitable">
    <tr><th>Item</th><th>Sawn Log</th><th>Nails</th></tr>
    <tr><th>Corner Shelf</th><th>1</th><th>3</th></tr>
    </table>
    """
    rows = parse_item_table(soup(html), "Cellar_Shelves")
    assert rows[0]["sawn_log"] == 1
    assert rows[0]["nails"] == 3


def test_item_table_returns_empty_when_no_wikitable():
    rows = parse_item_table(soup("<div>No table here</div>"), "loc")
    assert rows == []


# ── parse_construction_table ──────────────────────────────────────────────────

CONSTRUCTION_HTML = """
<table class="wikitable">
<tr><th>Stage</th><th>Section</th><th>Sawn Log</th><th>Quarried Stone</th><th>Nails</th></tr>
<tr><th>Stage 1</th><td>House, Foundation</td><td>1</td><td>10</td><td>-</td></tr>
<tr><th></th><td>House, Wall Framing</td><td>6</td><td>-</td><td>10</td></tr>
<tr><th>Stage 2</th><td>House, Walls</td><td>2</td><td>-</td><td>8</td></tr>
<tr><th colspan="2">Total</th><td>9</td><td>10</td><td>18</td></tr>
</table>
"""


def test_construction_table_stage_tracking():
    rows = parse_construction_table(soup(CONSTRUCTION_HTML), "Small House")
    assert rows[0]["stage"] == "Stage 1"
    assert rows[1]["stage"] == "Stage 1"   # empty <th> continues Stage 1
    assert rows[2]["stage"] == "Stage 2"


def test_construction_table_section_names():
    rows = parse_construction_table(soup(CONSTRUCTION_HTML), "Small House")
    assert rows[0]["section"] == "House, Foundation"
    assert rows[1]["section"] == "House, Wall Framing"


def test_construction_table_material_values():
    rows = parse_construction_table(soup(CONSTRUCTION_HTML), "Small House")
    assert rows[0]["sawn_log"] == 1
    assert rows[0]["quarried_stone"] == 10
    assert rows[0]["nails"] == 0  # "-" → 0


def test_construction_table_skips_total():
    rows = parse_construction_table(soup(CONSTRUCTION_HTML), "Small House")
    assert len(rows) == 3
    assert not any(r["section"].lower() == "total" for r in rows)


def test_construction_table_cleans_footnote():
    html = """
    <table class="wikitable">
    <tr><th>Stage</th><th>Section</th><th>Sawn Log</th></tr>
    <tr><th>Stage 7</th>
      <td>Main Hall, <a href="/wiki/Cellar">Cellar</a> <small>(optional)</small> †</td>
      <td>8</td></tr>
    </table>
    """
    rows = parse_construction_table(soup(html), "Main Hall")
    assert rows[0]["section"] == "Main Hall, Cellar"
    assert rows[0]["sawn_log"] == 8


# ── parse_shrine_bullet ───────────────────────────────────────────────────────

SHRINE_HTML = """
<div>
<h4>Shrine of Akatosh</h4>
<p>Magicka regenerates 10% faster</p>
<ul>
<li>1 x <a href="/wiki/Amulet_of_Akatosh">Amulet of Akatosh</a></li>
<li>1 x Iron Ingot</li>
<li>1 x <a href="/wiki/Flawless_Amethyst">Flawless Amethyst</a></li>
<li>1 x <a href="/wiki/Corundum_Ingot">Corundum Ingot</a></li>
</ul>
</div>
"""


def test_shrine_bullet_section_title():
    rows = parse_shrine_bullet(soup(SHRINE_HTML), "Cellar_Divine_Shrines",
                               "Shrine of Akatosh")
    assert len(rows) == 1
    assert rows[0]["section"] == "Shrine of Akatosh"
    assert rows[0]["location"] == "Cellar_Divine_Shrines"


def test_shrine_bullet_materials():
    rows = parse_shrine_bullet(soup(SHRINE_HTML), "Cellar_Divine_Shrines",
                               "Shrine of Akatosh")
    r = rows[0]
    assert r["amulet_of_akatosh"] == 1
    assert r["iron_ingot"] == 1
    assert r["flawless_amethyst"] == 1
    assert r["corundum_ingot"] == 1
    assert r["sawn_log"] == 0


def test_shrine_bullet_returns_empty_when_no_ul():
    rows = parse_shrine_bullet(soup("<div><h4>Shrine</h4></div>"),
                               "Cellar_Divine_Shrines", "Shrine of X")
    assert rows == []


# ── exclusive exterior (hardcoded records) ────────────────────────────────────

def test_exclusive_exterior_count():
    assert len(EXCL_RECORDS) == 3


def test_exclusive_exterior_manors():
    manors = {r["manor"] for r in EXCL_RECORDS}
    assert manors == {"Lakeview Manor", "Windstad Manor", "Heljarchen Hall"}


def test_exclusive_exterior_mapping():
    by_manor = {r["manor"]: r["exclusive_exterior"] for r in EXCL_RECORDS}
    assert by_manor["Lakeview Manor"] == "Apiary"
    assert by_manor["Windstad Manor"] == "Fish Hatchery"
    assert by_manor["Heljarchen Hall"] == "Grain Mill"


# ── steward cost parser ───────────────────────────────────────────────────────

TRIVIA_HTML = """
<ul>
<li>Some other trivia point.</li>
<li>The Dragonborn can pay the steward to deal with the furnishings process,
and the furnishings will appear over time. The cost to upgrade each room is:
<ul>
<li>Small House: 1,000 <img alt="Gold"/></li>
<li>Main Hall: 3,500 <img alt="Gold"/></li>
<li>Enchanter&#39;s Tower: 2,500 <img alt="Gold"/></li>
</ul>
</li>
</ul>
"""


def test_steward_cost_parses_rooms():
    records = parse_steward_costs(TRIVIA_HTML)
    names = [r["room"] for r in records]
    assert "Small House" in names
    assert "Main Hall" in names


def test_steward_cost_parses_gold():
    records = parse_steward_costs(TRIVIA_HTML)
    by_room = {r["room"]: r["gold_cost"] for r in records}
    assert by_room["Small House"] == 1000
    assert by_room["Main Hall"] == 3500
    assert by_room["Enchanter's Tower"] == 2500


def test_steward_cost_count():
    records = parse_steward_costs(TRIVIA_HTML)
    assert len(records) == 3


# ── integration: raw JSON → records ──────────────────────────────────────────

RAW_DIR = REPO_ROOT / "TES/Skyrim/homestead"


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_count():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    assert len(records) == 164


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_pk_unique():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    keys = [(r["section"], r["location"]) for r in records]
    assert len(keys) == len(set(keys)), "Duplicate (section, location) pairs found"


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_shrine_akatosh():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    r = next((x for x in records if x["section"] == "Shrine of Akatosh"), None)
    assert r is not None
    assert r["amulet_of_akatosh"] == 1
    assert r["iron_ingot"] == 1
    assert r["flawless_amethyst"] == 1


@pytest.mark.skipif(
    not (RAW_DIR / "steward_cost_json/steward_cost_records.json").exists(),
    reason="steward_cost_records.json not yet generated",
)
def test_steward_cost_full_list():
    with open(RAW_DIR / "steward_cost_json/steward_cost_records.json") as f:
        records = json.load(f)
    assert len(records) == 12
    rooms = [r["room"] for r in records]
    assert "Kitchen" in rooms
    assert "Armory" in rooms


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_crafted_components_present():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    crafted = [r for r in records if r.get("location") == "Crafted_Component"]
    names = {r["section"] for r in crafted}
    assert names == {"Nails", "Hinge", "Iron Fittings", "Lock"}


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_crafted_batch_sizes():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    crafted = {r["section"]: r for r in records if r.get("location") == "Crafted_Component"}
    assert crafted["Nails"]["batch_size"] == 10
    assert crafted["Hinge"]["batch_size"] == 2
    assert crafted["Iron Fittings"]["batch_size"] == 1
    assert crafted["Lock"]["batch_size"] == 1


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_crafted_materials():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    crafted = {r["section"]: r for r in records if r.get("location") == "Crafted_Component"}
    assert crafted["Nails"]["iron_ingot"] == 1
    assert crafted["Lock"]["iron_ingot"] == 1
    assert crafted["Lock"]["corundum_ingot"] == 1


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_non_crafted_batch_size_null():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    build_rows = [r for r in records if r.get("location") != "Crafted_Component"]
    assert all(r.get("batch_size") is None for r in build_rows)
