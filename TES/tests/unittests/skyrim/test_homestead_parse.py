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
_crafted = load_module(
    "TES/Skyrim/homestead/crafted_components_json/skyrim_parse_homestead_crafted_components.py",
    "sk_homestead_crafted",
)

parse_item_table           = _build.parse_item_table
parse_construction_table   = _build.parse_construction_table
parse_shrine_bullet        = _build.parse_shrine_bullet
parse_type_options_table   = _build.parse_type_options_table
parse_steward_costs        = _cost.parse_steward_costs

EXCL_RECORDS       = _excl.RECORDS
CRAFTED_COMPONENTS = _crafted.CRAFTED_COMPONENTS

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

ITEM_TABLE_TOTALS_HTML = """
<table class="wikitable">
<tr><th>Item</th><th>Sawn Log</th><th>Nails</th></tr>
<tr><th>Lantern</th><td>1</td><td>2</td></tr>
<tr><th>Totals</th><th>1</th><th>2</th></tr>
</table>
"""


def test_item_table_basic_record():
    rows = parse_item_table(soup(ITEM_TABLE_HTML), "Cellar_Containers")
    chest = next(r for r in rows if r["section"] == "Chest")
    assert chest["location"] == "Cellar_Containers"
    assert chest["batch_size"] is None
    assert chest["sawn_log"] == 1
    assert chest["nails"] == 1
    assert chest["iron_ingot"] == 0


def test_item_table_no_stage_key():
    """Stage column was removed; records must not have a 'stage' key."""
    rows = parse_item_table(soup(ITEM_TABLE_HTML), "Cellar_Containers")
    for r in rows:
        assert "stage" not in r


def test_item_table_skips_total():
    rows = parse_item_table(soup(ITEM_TABLE_HTML), "Cellar_Containers")
    assert not any(r["section"].lower() == "total" for r in rows)


def test_item_table_skips_totals_plural():
    """'Totals' (with trailing s) must also be skipped."""
    rows = parse_item_table(soup(ITEM_TABLE_TOTALS_HTML), "Main_Hall_Upstairs_Illumination")
    assert not any(r["section"].lower().startswith("total") for r in rows)
    assert len(rows) == 1
    assert rows[0]["section"] == "Lantern"


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


def test_item_table_steel_ingots_plural():
    """'Steel Ingots' (plural header) must map to steel_ingot column."""
    html = """
    <table class="wikitable">
    <tr><th>Item</th><th>Sawn Log</th><th>Steel Ingots</th></tr>
    <tr><th>Bed Frame</th><td>1</td><td>2</td></tr>
    </table>
    """
    rows = parse_item_table(soup(html), "West_Wing_Bedrooms_Containers")
    assert rows[0]["steel_ingot"] == 2


def test_item_table_sabre_cat_pelt_column():
    """'Sabre Cat Pelt' must map to the sabre_cat_pelt column."""
    html = """
    <table class="wikitable">
    <tr><th>Item</th><th>Leather Strips</th><th>Sabre Cat Pelt</th></tr>
    <tr><th>Mounted Sabre Cat Head</th><td>1</td><td>1</td></tr>
    </table>
    """
    rows = parse_item_table(soup(html), "Entryway")
    assert rows[0]["sabre_cat_pelt"] == 1
    assert rows[0]["leather_strips"] == 1


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


def test_construction_table_no_stage_key():
    """Stage column was removed; records must not have a 'stage' key."""
    rows = parse_construction_table(soup(CONSTRUCTION_HTML), "Small House")
    for r in rows:
        assert "stage" not in r


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


def test_shrine_bullet_no_stage_key():
    rows = parse_shrine_bullet(soup(SHRINE_HTML), "Cellar_Divine_Shrines",
                               "Shrine of Akatosh")
    assert "stage" not in rows[0]


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


# ── parse_type_options_table (entryway style) ─────────────────────────────────

ENTRYWAY_TABLE_HTML = """
<table class="wikitable">
<tr><th colspan="4">Main Hall, Entryway - Furnishings</th></tr>
<tr><th>Type</th><th>Options</th><th>Materials</th><th>Notes</th></tr>
<tr><td rowspan="2">Containers</td><td>Barrels</td><td>Sawn Log, Nails, Iron Ingot</td><td>Southwest corner.</td></tr>
<tr><td>Dresser</td><td>Sawn Log, 3 Nails, Iron Fittings</td><td>East wall.</td></tr>
<tr><td>Miscellaneous</td><td>Mounted Sabre Cat Head</td><td>Leather Strips, Sabre Cat Pelt</td><td>East wall.</td></tr>
<tr><td>Miscellaneous</td><td>Mounted Sabre Cat Head</td><td>Leather Strips, Sabre Cat Snow Pelt</td><td>West wall.</td></tr>
</table>
"""


def test_type_options_table_basic_records():
    rows = parse_type_options_table(soup(ENTRYWAY_TABLE_HTML), "Entryway")
    names = [r["section"] for r in rows]
    assert "Barrels" in names
    assert "Dresser" in names


def test_type_options_table_materials_parsed():
    rows = parse_type_options_table(soup(ENTRYWAY_TABLE_HTML), "Entryway")
    barrels = next(r for r in rows if r["section"] == "Barrels")
    assert barrels["sawn_log"] == 1
    assert barrels["nails"] == 1
    assert barrels["iron_ingot"] == 1


def test_type_options_table_quantity_prefix():
    """'3 Nails' in free-text materials should parse as nails=3."""
    rows = parse_type_options_table(soup(ENTRYWAY_TABLE_HTML), "Entryway")
    dresser = next(r for r in rows if r["section"] == "Dresser")
    assert dresser["nails"] == 3
    assert dresser["iron_fittings"] == 1


def test_type_options_table_sabre_cat_pelt():
    rows = parse_type_options_table(soup(ENTRYWAY_TABLE_HTML), "Entryway")
    # Two identical item names → enumerated as _1 and _2
    sc1 = next(r for r in rows if r["section"] == "Mounted Sabre Cat Head_1")
    assert sc1["sabre_cat_pelt"] == 1
    assert sc1["leather_strips"] == 1


def test_type_options_table_enumerates_duplicates():
    rows = parse_type_options_table(soup(ENTRYWAY_TABLE_HTML), "Entryway")
    sections = [r["section"] for r in rows]
    assert "Mounted Sabre Cat Head_1" in sections
    assert "Mounted Sabre Cat Head_2" in sections
    assert "Mounted Sabre Cat Head" not in sections


def test_type_options_table_no_stage_key():
    rows = parse_type_options_table(soup(ENTRYWAY_TABLE_HTML), "Entryway")
    for r in rows:
        assert "stage" not in r


def test_type_options_table_returns_empty_when_no_wikitable():
    rows = parse_type_options_table(soup("<div>No table here</div>"), "Entryway")
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
<li>Storage Room: 1,500 <img alt="Gold"/></li>
</ul>
</li>
</ul>
"""


def test_steward_cost_parses_rooms():
    records = parse_steward_costs(TRIVIA_HTML)
    names = [r["room"] for r in records]
    assert "Small House" in names
    assert "Main Hall" in names


def test_steward_cost_maps_wing_names():
    """Room names must be mapped to build-table location prefixes."""
    records = parse_steward_costs(TRIVIA_HTML)
    by_wiki = {r["room"] for r in records}
    # "Enchanter's Tower" → "West_Wing_Enchanter's_Tower"
    assert "West_Wing_Enchanter's_Tower" in by_wiki
    assert "Enchanter's Tower" not in by_wiki
    # "Storage Room" → "North_Wing_Storage_Room"
    assert "North_Wing_Storage_Room" in by_wiki
    assert "Storage Room" not in by_wiki


def test_steward_cost_parses_gold():
    records = parse_steward_costs(TRIVIA_HTML)
    by_room = {r["room"]: r["gold_cost"] for r in records}
    assert by_room["Small House"] == 1000
    assert by_room["Main Hall"] == 3500
    assert by_room["West_Wing_Enchanter's_Tower"] == 2500


def test_steward_cost_count():
    records = parse_steward_costs(TRIVIA_HTML)
    assert len(records) == 4


# ── crafted components (hardcoded) ────────────────────────────────────────────

def test_crafted_components_count():
    assert len(CRAFTED_COMPONENTS) == 4


def test_crafted_components_names_lowercase():
    """Names must be lowercase (to match build table references like 'nails' col)."""
    for c in CRAFTED_COMPONENTS:
        assert c["name"] == c["name"].lower(), f"Name not lowercase: {c['name']}"


def test_crafted_components_batch_sizes():
    by_name = {c["name"]: c for c in CRAFTED_COMPONENTS}
    assert by_name["nails"]["batch_size"] == 10
    assert by_name["hinge"]["batch_size"] == 2
    assert by_name["iron fittings"]["batch_size"] == 1
    assert by_name["lock"]["batch_size"] == 1


def test_crafted_components_materials():
    by_name = {c["name"]: c for c in CRAFTED_COMPONENTS}
    assert by_name["nails"]["iron_ingot"] == 1
    assert by_name["lock"]["iron_ingot"] == 1
    assert by_name["lock"]["corundum_ingot"] == 1


# ── integration: raw JSON → records ──────────────────────────────────────────

RAW_DIR = REPO_ROOT / "TES/Skyrim/homestead"


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_minimum_count():
    """With wing furnishings added the record count is well above the old 164."""
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    assert len(records) >= 200


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
def test_build_records_no_stage_column():
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    for r in records:
        assert "stage" not in r


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_wing_locations_renamed():
    """Wing locations must use West/North/East naming, not Tower/Room/Downstairs."""
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    locations = {r["location"] for r in records}
    assert "West_Wing" in locations
    assert "North_Wing" in locations
    assert "East_Wing" in locations
    assert "Tower" not in locations
    assert "Room with Outdoor Patio" not in locations
    assert "Downstairs Room" not in locations


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_wing_furnishings_present():
    """At least one furnishing row for each wing must exist."""
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    locations = {r["location"] for r in records}
    assert any(loc.startswith("West_Wing_") and loc != "West_Wing" for loc in locations)
    assert any(loc.startswith("North_Wing_") and loc != "North_Wing" for loc in locations)
    assert any(loc.startswith("East_Wing_") and loc != "East_Wing" for loc in locations)


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_entryway_present():
    """Entryway rows from UESP must be included."""
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    entryway_rows = [r for r in records if r["location"] == "Entryway"]
    assert len(entryway_rows) >= 5


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
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_no_crafted_components():
    """Crafted components (Nails, etc.) must not be in build_records.json."""
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    crafted_locations = [r for r in records if r.get("location") == "Crafted_Component"]
    assert crafted_locations == []


@pytest.mark.skipif(
    not (RAW_DIR / "build_json/build_records.json").exists(),
    reason="build_records.json not yet generated",
)
def test_build_records_no_main_hall_aquarium():
    """Aquarium must be under Cellar_Aquarium, not Main_Hall_Aquarium."""
    with open(RAW_DIR / "build_json/build_records.json") as f:
        records = json.load(f)
    bad = [r for r in records if r.get("location") == "Main_Hall_Aquarium"]
    assert bad == []


@pytest.mark.skipif(
    not (RAW_DIR / "steward_cost_json/steward_cost_records.json").exists(),
    reason="steward_cost_records.json not yet generated",
)
def test_steward_cost_full_list():
    with open(RAW_DIR / "steward_cost_json/steward_cost_records.json") as f:
        records = json.load(f)
    assert len(records) == 12
    rooms = [r["room"] for r in records]
    # Rooms should have build-table names
    assert "North_Wing_Storage_Room" in rooms
    assert "East_Wing_Kitchen" in rooms
    assert "East_Wing_Armory" in rooms
    assert "West_Wing_Greenhouse" in rooms
    # Original wiki names must not appear
    assert "Storage Room" not in rooms
    assert "Kitchen" not in rooms
    assert "Armory" not in rooms
    assert "Greenhouse" not in rooms
