"""Tests for CC parser scripts."""
import json
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_armor = load_module(
    "TES/Skyrim/creation_club/cc_armor_json/skyrim_parse_cc_armor.py",
    "cc_armor_parse",
)
_weapons = load_module(
    "TES/Skyrim/creation_club/cc_weapons_json/skyrim_parse_cc_weapons.py",
    "cc_weapons_parse",
)
_ammo = load_module(
    "TES/Skyrim/creation_club/cc_ammo_json/skyrim_parse_cc_ammo.py",
    "cc_ammo_parse",
)
_homestead = load_module(
    "TES/Skyrim/creation_club/cc_homestead_json/skyrim_parse_cc_homestead.py",
    "cc_homestead_parse",
)

CC_PARSE_DIR = REPO_ROOT / "TES/Skyrim/creation_club/cc_parse"

# ── armor parser ──────────────────────────────────────────────────────────────

AMBER_ARMOR_HTML = """
<div>
<table class="wikitable sortable">
<tr>
  <th></th><th>Name (ID)</th><th></th><th></th><th></th>
  <th colspan="4">Raw Materials</th>
  <th colspan="2">Delta</th><th colspan="2">Ratio</th>
</tr>
<tr>
  <th>Amber</th><th>Moonstone</th><th>Strips</th><th>Firewood</th>
  <th></th><th></th><th></th><th></th>
</tr>
<tr>
  <td></td>
  <td><span id="Amber_Armor"></span>Amber Armor<br/>
  <span class="idall">(<span class="idref"><a>xx</a><span class="idcase">000BC3</span></span>)</span></td>
  <td>30</td><td>1100</td><td>40</td>
  <td>4</td><td>1</td><td>3</td><td>0</td>
  <td>1</td><td>2</td><td>3</td><td>4</td>
</tr>
<tr class="sortbottom"><td colspan="5">Totals</td><td>4</td><td>1</td><td>3</td><td>0</td></tr>
</table>
</div>
"""

DAEDRIC_ARMOR_HTML = """
<div>
<table class="wikitable sortable">
<tr>
  <th></th><th>Name (ID)</th><th></th><th></th><th></th>
  <th colspan="3">Raw Materials</th>
  <th colspan="2">Delta</th><th colspan="2">Ratio</th>
</tr>
<tr>
  <th><img alt="Daedra Heart"/></th>
  <th><img alt="Ebony Ingot"/></th>
  <th><img alt="Leather Strips"/></th>
  <th></th><th></th><th></th><th></th>
</tr>
<tr>
  <td></td>
  <td>Daedric Plate Armor<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">801</span></span>)</span></td>
  <td>50</td><td>3200</td><td>51</td>
  <td>1</td><td>5</td><td>3</td>
  <td>1</td><td>2</td><td>3</td><td>4</td>
</tr>
</table>
</div>
"""

VIGIL_ARMOR_HTML = """
<div>
<table class="wikitable">
<tr>
  <th></th><th>Name (ID)</th><th></th><th></th><th></th>
  <th colspan="3">Raw Materials</th>
  <th colspan="2">Delta</th><th colspan="2">Ratio</th>
</tr>
<tr>
  <th>Steel</th><th>Iron</th><th>Strips</th>
  <th></th><th></th><th></th><th></th>
</tr>
<tr>
  <td></td>
  <td><span id="Vigil_Corrupted_Armor"></span>Vigil Corrupted Armor<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">D7F</span></span>)</span><br/>
  <span id="Vigil_Enforcer_Armor"></span>Vigil Enforcer Armor<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">D61</span></span>)</span></td>
  <td>38</td><td>625</td><td>40</td>
  <td>10</td><td>5</td><td>3</td>
  <td>1</td><td>2</td><td>3</td><td>4</td>
</tr>
</table>
</div>
"""


def test_armor_parses_amber_record():
    recs = _armor.parse_armor_section(AMBER_ARMOR_HTML, "Glass Smithing")
    assert len(recs) == 1
    r = recs[0]
    assert r["piece"] == "Amber Armor"
    assert r["id"] == "xx000BC3"
    assert r["material_perk"] == "Glass Smithing"
    assert r["armor_rating"] == 40
    assert r["weight"] == 30.0
    assert r["value"] == 1100
    assert r["refined_amber"] == 4
    assert r["refined_moonstone"] == 1
    assert r["leather_strips"] == 3


def test_armor_skips_sortbottom():
    recs = _armor.parse_armor_section(AMBER_ARMOR_HTML, "Glass Smithing")
    assert len(recs) == 1  # sortbottom row not included


def test_armor_icon_only_headers_daedric():
    recs = _armor.parse_armor_section(DAEDRIC_ARMOR_HTML, "Daedric Smithing")
    assert len(recs) == 1
    r = recs[0]
    assert r["piece"] == "Daedric Plate Armor"
    assert r["id"] == "FExxx801"
    assert r["daedra_heart"] == 1
    assert r["ebony_ingot"] == 5
    assert r["leather_strips"] == 3


def test_armor_multi_piece_per_row_vigil():
    recs = _armor.parse_armor_section(VIGIL_ARMOR_HTML, "Steel Smithing")
    assert len(recs) == 2
    names = {r["piece"] for r in recs}
    assert "Vigil Corrupted Armor" in names
    assert "Vigil Enforcer Armor" in names
    for r in recs:
        assert r["steel_ingot"] == 10
        assert r["iron_ingot"] == 5
        assert r["leather_strips"] == 3


def test_armor_zero_fill_unused_columns():
    recs = _armor.parse_armor_section(AMBER_ARMOR_HTML, "Glass Smithing")
    r = recs[0]
    assert r["chitin_plate"] == 0
    assert r["dragon_bone"] == 0
    assert r["netch_leather"] == 0


@pytest.mark.skipif(
    not (CC_PARSE_DIR / "amber_raw.json").exists(),
    reason="cc_parse raw JSON not generated",
)
def test_armor_integration_amber():
    with open(CC_PARSE_DIR / "amber_raw.json") as f:
        data = json.load(f)
    recs = _armor.parse_armor_section(data["sections"]["3"]["html"], "Glass Smithing")
    assert len(recs) == 5  # Amber Armor + Boots + Gauntlets + Helmet + Shield
    names = {r["piece"] for r in recs}
    assert "Amber Armor" in names
    assert "Amber Shield" in names


@pytest.mark.skipif(
    not (CC_PARSE_DIR / "amber_raw.json").exists(),
    reason="cc_parse raw JSON not generated",
)
def test_armor_integration_total_count():
    """All CC armor sections together produce the expected record count."""
    import os
    all_recs = []
    seen = {}
    for page_key, sec_id, perk in _armor.ARMOR_SECTIONS:
        raw_path = CC_PARSE_DIR / f"{page_key}_raw.json"
        if not raw_path.exists():
            continue
        if page_key not in seen:
            seen[page_key] = json.load(open(raw_path))
        data = seen[page_key]
        if sec_id in data.get("sections", {}):
            recs = _armor.parse_armor_section(data["sections"][sec_id]["html"], perk)
            all_recs.extend(recs)
    assert len(all_recs) == 105


# ── weapons parser ────────────────────────────────────────────────────────────

AMBER_WEAPONS_HTML = """
<div>
<table class="wikitable">
<tr>
  <th></th><th>Name (ID)</th><th></th><th></th><th></th><th>Crit.</th><th>Speed</th><th>Reach</th>
  <th colspan="4">Raw Materials</th>
  <th colspan="2">Delta</th><th colspan="2">Ratio</th>
</tr>
<tr>
  <th>Amber</th><th>Moonstone</th><th>Strips</th><th>Firewood</th>
  <th></th><th></th><th></th><th></th>
</tr>
<tr>
  <td></td>
  <td><span id="Amber_Dagger"></span>Amber Dagger<br/>
  <span class="idall">(<span class="idref"><a>xx</a><span class="idcase">000BDD</span></span>)</span></td>
  <td>4.5</td><td>700</td><td>12</td><td>5</td><td>1.3</td><td>0.7</td>
  <td>1</td><td>1</td><td>1</td><td>0</td>
  <td>2.4</td><td>472</td><td>2.14</td><td>3.07</td>
</tr>
<tr class="sortbottom"><td colspan="9">Totals</td><td>1</td><td>1</td><td>1</td><td>0</td></tr>
</table>
</div>
"""

ELVEN_WEAPONS_HTML = """
<div>
<table class="wikitable">
<tr>
  <th></th><th>Name (ID)</th><th></th><th></th><th></th><th>Crit.</th><th>Speed</th><th>Reach</th>
  <th colspan="5">Raw Materials</th>
  <th colspan="2">Delta</th><th colspan="2">Ratio</th>
</tr>
<tr>
  <th>Moonstone</th><th>Quicksilver</th><th>Iron</th><th>Strips</th><th>Other</th>
  <th></th><th></th><th></th><th></th>
</tr>
<tr>
  <td></td>
  <td><span id="Elven_Dagger"></span>Elven Dagger<br/>
  <span class="idall">(<span class="idref"><a>00</a><span class="idcase">01399e</span></span>)</span></td>
  <td>4</td><td>95</td><td>10</td><td>4</td><td>1.3</td><td>0.7</td>
  <td>1</td><td>0</td><td>0</td><td>0</td><td></td>
  <td>1</td><td>2</td><td>3</td><td>4</td>
</tr>
<tr>
  <td></td>
  <td><span id="Elven_Crossbow"></span>Elven Crossbow<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">801</span></span>)</span></td>
  <td>14</td><td>700</td><td>19</td><td>7</td><td>0.75</td><td>1</td>
  <td>5</td><td>0</td><td>0</td><td>0</td><td></td>
  <td>1</td><td>2</td><td>3</td><td>4</td>
</tr>
<tr>
  <td></td>
  <td><span id="Enhanced_Elven_Crossbow"></span>Enhanced Elven Crossbow<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">809</span></span>)</span></td>
  <td>14</td><td>900</td><td>21</td><td>7</td><td>0.75</td><td>1</td>
  <td>2</td><td>0</td><td>0</td><td>0</td><td>1 Elven Crossbow</td>
  <td>1</td><td>2</td><td>3</td><td>4</td>
</tr>
</table>
</div>
"""

MADNESS_WEAPONS_HTML = """
<div>
<table class="wikitable">
<tr>
  <th>Name</th><th>ID</th><th></th><th></th><th></th><th>Crit.</th><th>Speed</th><th>Reach</th>
  <th colspan="3">Raw Materials</th>
  <th colspan="2">Delta</th><th colspan="2">Ratio</th>
</tr>
<tr>
  <th>Madness</th><th>Ebony</th><th>Strips</th>
  <th></th><th></th><th></th><th></th>
</tr>
<tr>
  <td>Madness Dagger</td>
  <td><span class="idall">(<span class="idref"><a>xx</a><span class="idcase">000BE6</span></span>)</span></td>
  <td>7</td><td>800</td><td>13</td><td>5</td><td>1.3</td><td>0.7</td>
  <td>1</td><td>1</td><td>1</td>
  <td>1</td><td>2</td><td>3</td><td>4</td>
</tr>
</table>
</div>
"""


def test_weapons_parses_amber_dagger():
    recs = _weapons.parse_weapons_section(AMBER_WEAPONS_HTML, "Glass Smithing")
    assert len(recs) == 1
    r = recs[0]
    assert r["piece"] == "Amber Dagger"
    assert r["damage"] == 12
    assert r["refined_amber"] == 1
    assert r["refined_moonstone"] == 1
    assert r["leather_strips"] == 1
    assert r["firewood"] == 0


def test_weapons_crossbow_only_filter():
    recs = _weapons.parse_weapons_section(
        ELVEN_WEAPONS_HTML, "Elven Smithing", crossbow_only=True)
    assert len(recs) == 2
    names = {r["piece"] for r in recs}
    assert "Elven Crossbow" in names
    assert "Enhanced Elven Crossbow" in names
    assert "Elven Dagger" not in names


def test_weapons_other_col_elven_crossbow():
    recs = _weapons.parse_weapons_section(
        ELVEN_WEAPONS_HTML, "Elven Smithing", crossbow_only=True)
    by_name = {r["piece"]: r for r in recs}
    assert by_name["Elven Crossbow"]["refined_moonstone"] == 5
    assert by_name["Elven Crossbow"]["elven_crossbow"] == 0
    assert by_name["Enhanced Elven Crossbow"]["refined_moonstone"] == 2
    assert by_name["Enhanced Elven Crossbow"]["elven_crossbow"] == 1


def test_weapons_split_format_madness():
    recs = _weapons.parse_weapons_section(MADNESS_WEAPONS_HTML, "Ebony Smithing")
    assert len(recs) == 1
    r = recs[0]
    assert r["piece"] == "Madness Dagger"
    assert r["madness_ingot"] == 1
    assert r["ebony_ingot"] == 1
    assert r["leather_strips"] == 1


def test_weapons_skips_sortbottom():
    recs = _weapons.parse_weapons_section(AMBER_WEAPONS_HTML, "Glass Smithing")
    assert len(recs) == 1


@pytest.mark.skipif(
    not (CC_PARSE_DIR / "amber_raw.json").exists(),
    reason="cc_parse raw JSON not generated",
)
def test_weapons_integration_total_count():
    seen = {}
    all_recs = []
    for page_key, sec_id, perk, cb_only in _weapons.WEAPONS_SECTIONS:
        raw_path = CC_PARSE_DIR / f"{page_key}_raw.json"
        if not raw_path.exists():
            continue
        if page_key not in seen:
            seen[page_key] = json.load(open(raw_path))
        data = seen[page_key]
        if sec_id in data.get("sections", {}):
            recs = _weapons.parse_weapons_section(
                data["sections"][sec_id]["html"], perk, cb_only)
            all_recs.extend(recs)
    assert len(all_recs) == 40


# ── ammo parser ───────────────────────────────────────────────────────────────

ARCANE_AMMO_HTML = """
<div>
<table class="wikitable">
<tr>
  <th></th><th>Name (ID)</th><th></th><th></th><th></th>
  <th colspan="2">Raw Materials</th>
  <th>Enchantment/Notes</th>
</tr>
<tr><th>Firewood</th><th>Other</th></tr>
<tr>
  <td></td>
  <td><span id="Fire_Arrow"></span>Fire Arrow<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">802</span></span>)</span></td>
  <td>0</td><td>2</td><td>8</td>
  <td>1</td><td>4|Fire Salts|Makes 10 arrows</td>
  <td>Some enchantment notes</td>
</tr>
<tr>
  <td></td>
  <td><span id="Bound_Arrow"></span>Bound Arrow<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">80D</span></span>)</span></td>
  <td>0</td><td>0</td><td>32</td>
  <td></td><td></td>
  <td>Spell arrow notes</td>
</tr>
</table>
</div>
"""

RARE_AMMO_HTML = """
<div>
<table class="wikitable">
<tr><th></th><th>Name (ID)</th><th></th><th></th><th></th><th>Notes</th><th>Speed</th><th>Gravity</th></tr>
<tr>
  <td></td>
  <td><span id="Bonemold_Bolt"></span>Bonemold Bolt<br/>
  <span class="idall">(<span class="idref"><span class="idcase">FE</span><a>xxx</a><span class="idcase">840</span></span>)</span></td>
  <td>0</td><td>3</td><td>15</td>
  <td>Can be forged using bonemeal and the Steel Smithing perk.</td>
  <td>5400</td><td>0.35</td>
</tr>
</table>
</div>
"""


def test_ammo_arcane_parses_fire_arrow():
    recs = _ammo.parse_arcane_archer_ammo(ARCANE_AMMO_HTML)
    assert len(recs) == 1  # Bound Arrow excluded
    r = recs[0]
    assert r["piece"] == "Fire Arrow"
    assert r["type"] == "arrow"
    assert r["damage"] == 8
    assert r["batch_size"] == 10
    assert r["firewood"] == 1
    assert r["fire_salts"] == 4
    assert r["material_perk"] is None


def test_ammo_arcane_excludes_bound_arrow():
    recs = _ammo.parse_arcane_archer_ammo(ARCANE_AMMO_HTML)
    assert all(r["piece"] != "Bound Arrow" for r in recs)


def test_ammo_rare_curios_parses_bolt():
    recs = _ammo.parse_rare_curios_ammo(RARE_AMMO_HTML, "bolt")
    assert len(recs) == 1
    r = recs[0]
    assert r["piece"] == "Bonemold Bolt"
    assert r["type"] == "bolt"
    assert r["damage"] == 15
    assert r["material_perk"] == "Steel Smithing"
    assert r["batch_size"] is None
    # All material columns should be 0 (not in table)
    assert r["bonemeal"] == 0
    assert r["firewood"] == 0


@pytest.mark.skipif(
    not (CC_PARSE_DIR / "arcane_archer_pack_items_raw.json").exists(),
    reason="cc_parse raw JSON not generated",
)
def test_ammo_integration_arcane_archer():
    with open(CC_PARSE_DIR / "arcane_archer_pack_items_raw.json") as f:
        data = json.load(f)
    recs = _ammo.parse_arcane_archer_ammo(data["sections"]["1"]["html"])
    assert len(recs) == 6  # Telekinesis, Soul Stealer, Fire, Ice, Lightning, Bone
    names = {r["piece"] for r in recs}
    assert "Fire Arrow" in names
    assert "Bone Arrow" in names
    assert "Bound Arrow" not in names


@pytest.mark.skipif(
    not (CC_PARSE_DIR / "arcane_archer_pack_items_raw.json").exists(),
    reason="cc_parse raw JSON not generated",
)
def test_ammo_integration_bone_arrow_perk():
    with open(CC_PARSE_DIR / "arcane_archer_pack_items_raw.json") as f:
        data = json.load(f)
    recs = _ammo.parse_arcane_archer_ammo(data["sections"]["1"]["html"])
    bone = next(r for r in recs if r["piece"] == "Bone Arrow")
    assert bone["material_perk"] == "Dragon Smithing"
    assert bone["dragon_bone"] == 10
    assert bone["batch_size"] == 10


# ── homestead parser ──────────────────────────────────────────────────────────

AQUARIUM_HTML = """
<div>
<table class="wikitable">
<tr><td colspan="5">Main Hall, Aquarium - Furnishings</td></tr>
<tr><th>Type</th><th>Options</th><th>Materials</th><th>Notes</th></tr>
<tr>
  <td>Containers</td><td>Fishing Supplies</td>
  <td>Sawn Log, Nails, Iron Ingot</td><td>East wall note</td>
</tr>
<tr>
  <td></td><td>Cupboard</td>
  <td>2 Sawn Log, 4 Nails, Iron Fittings</td><td>South wall note</td>
</tr>
<tr>
  <td>Misc</td><td>Mounted Mudcrab</td>
  <td>Leather Strips, 2 Mudcrab Chitin</td><td>North wall</td>
</tr>
<tr>
  <td colspan="2">Total Materials:</td>
  <td>3 Sawn Log, 5 Nails, 1 Iron Ingot, 1 Iron Fittings, 1 Leather Strips, 2 Mudcrab Chitin</td>
  <td></td>
</tr>
</table>
</div>
"""


def test_homestead_parses_single_material():
    recs = _homestead.parse_aquarium_section(AQUARIUM_HTML)
    fishing = next(r for r in recs if r["section"] == "Fishing Supplies")
    assert fishing["sawn_log"] == 1
    assert fishing["nails"] == 1
    assert fishing["iron_ingot"] == 1
    assert fishing["location"] == "Main_Hall_Aquarium"
    assert fishing["stage"] is None
    assert fishing["batch_size"] is None


def test_homestead_parses_qty_prefix():
    recs = _homestead.parse_aquarium_section(AQUARIUM_HTML)
    cupboard = next(r for r in recs if r["section"] == "Cupboard")
    assert cupboard["sawn_log"] == 2
    assert cupboard["nails"] == 4
    assert cupboard["iron_fittings"] == 1


def test_homestead_parses_multi_material():
    recs = _homestead.parse_aquarium_section(AQUARIUM_HTML)
    crab = next(r for r in recs if r["section"] == "Mounted Mudcrab")
    assert crab["leather_strips"] == 1
    assert crab["mudcrab_chitin"] == 2


def test_homestead_skips_total_row():
    recs = _homestead.parse_aquarium_section(AQUARIUM_HTML)
    assert not any(r["section"].lower().startswith("total") for r in recs)


def test_homestead_enumerates_duplicates():
    html = """
    <table class="wikitable">
    <tr><td colspan="4">Title</td></tr>
    <tr><th>Type</th><th>Options</th><th>Materials</th><th>Notes</th></tr>
    <tr><td>Misc</td><td>Fish Plaque</td><td>Sawn Log, Nails</td><td>East</td></tr>
    <tr><td></td><td>Fish Plaque</td><td>Sawn Log, Nails</td><td>West</td></tr>
    <tr><td></td><td>Fish Plaque</td><td>Sawn Log, Nails</td><td>South</td></tr>
    </table>
    """
    recs = _homestead.parse_aquarium_section(html)
    sections = [r["section"] for r in recs]
    assert "Fish Plaque_1" in sections
    assert "Fish Plaque_2" in sections
    assert "Fish Plaque_3" in sections
    assert "Fish Plaque" not in sections


@pytest.mark.skipif(
    not (CC_PARSE_DIR / "main_hall_raw.json").exists(),
    reason="cc_parse raw JSON not generated",
)
def test_homestead_integration_aquarium_count():
    with open(CC_PARSE_DIR / "main_hall_raw.json") as f:
        data = json.load(f)
    recs = _homestead.parse_aquarium_section(data["sections"]["9"]["html"])
    assert len(recs) == 18


@pytest.mark.skipif(
    not (CC_PARSE_DIR / "main_hall_raw.json").exists(),
    reason="cc_parse raw JSON not generated",
)
def test_homestead_integration_aquarium_location():
    with open(CC_PARSE_DIR / "main_hall_raw.json") as f:
        data = json.load(f)
    recs = _homestead.parse_aquarium_section(data["sections"]["9"]["html"])
    assert all(r["location"] == "Main_Hall_Aquarium" for r in recs)
