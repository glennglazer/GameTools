"""Tests for CC SQL loader scripts."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_armor_sql = load_module(
    "TES/Skyrim/creation_club/cc_armor_sql/create_or_update_skyrim_cc_armor.py",
    "cc_armor_sql",
)
_weapons_sql = load_module(
    "TES/Skyrim/creation_club/cc_weapons_sql/create_or_update_skyrim_cc_weapons.py",
    "cc_weapons_sql",
)
_ammo_sql = load_module(
    "TES/Skyrim/creation_club/cc_ammo_sql/create_or_update_skyrim_cc_ammo.py",
    "cc_ammo_sql",
)
_homestead_sql = load_module(
    "TES/Skyrim/creation_club/cc_homestead_sql/create_or_update_skyrim_cc_homestead.py",
    "cc_homestead_sql",
)
_materials_sql = load_module(
    "TES/Skyrim/creation_club/cc_materials_sql/create_or_update_skyrim_cc_materials.py",
    "cc_materials_sql",
)

ARMOR_SCRIPT    = str(REPO_ROOT / "TES/Skyrim/creation_club/cc_armor_sql/create_or_update_skyrim_cc_armor.py")
WEAPONS_SCRIPT  = str(REPO_ROOT / "TES/Skyrim/creation_club/cc_weapons_sql/create_or_update_skyrim_cc_weapons.py")
AMMO_SCRIPT     = str(REPO_ROOT / "TES/Skyrim/creation_club/cc_ammo_sql/create_or_update_skyrim_cc_ammo.py")
HOMESTEAD_SCRIPT= str(REPO_ROOT / "TES/Skyrim/creation_club/cc_homestead_sql/create_or_update_skyrim_cc_homestead.py")
MATERIALS_SCRIPT= str(REPO_ROOT / "TES/Skyrim/creation_club/cc_materials_sql/create_or_update_skyrim_cc_materials.py")

ARMOR_MAT_COLS = _armor_sql.__dict__.get(
    "ARMOR_MAT_COLS", [
        "bone_meal", "chitin_plate", "corundum_ingot", "daedra_heart",
        "dragon_bone", "dragon_scales", "dwarven_metal_ingot", "ebony_ingot",
        "iron_ingot", "leather", "leather_strips", "netch_jelly", "netch_leather",
        "orichalcum_ingot", "quicksilver_ingot", "refined_malachite",
        "refined_moonstone", "stalhrim", "steel_ingot", "void_salts",
        "refined_amber", "madness_ingot", "gold_ingot", "silver_ingot",
    ]
)

WEAPONS_MAT_COLS = [
    "corundum_ingot", "crossbow", "daedra_heart", "dragon_bone",
    "dwarven_crossbow", "dwarven_metal_ingot", "ebony_ingot", "firewood",
    "iron_ingot", "leather_strips", "orichalcum_ingot", "quicksilver_ingot",
    "refined_malachite", "refined_moonstone", "stalhrim", "steel_ingot",
    "refined_amber", "madness_ingot", "gold_ingot", "elven_crossbow", "daedric_crossbow",
]

HOMESTEAD_MAT_COLS = [
    "sawn_log", "quarried_stone", "nails", "clay", "iron_fittings", "lock",
    "hinge", "iron_ingot", "steel_ingot", "glass", "quicksilver_ingot",
    "refined_moonstone", "filled_grand_soul_gem", "gold_ingot", "leather_strips",
    "straw", "goat_horns", "vampire_dust", "deer_hide", "large_antlers",
    "small_antlers", "goat_hide", "horker_tusk", "mudcrab_chitin",
    "slaughterfish_scales", "wolf_pelt", "sabre_cat_tooth", "sabre_cat_snow_pelt",
    "bear_pelt", "amulet_of_akatosh", "amulet_of_arkay", "amulet_of_dibella",
    "amulet_of_julianos", "amulet_of_kynareth", "amulet_of_mara",
    "amulet_of_stendarr", "amulet_of_talos", "amulet_of_zenithar",
    "flawless_amethyst", "flawless_sapphire", "corundum_ingot",
    "orichalcum_ingot", "silver_ingot", "ebony_ingot", "refined_malachite",
    "dragon_bone", "dragon_scales",
]


def run(script, args):
    return subprocess.run(
        [sys.executable, script] + args,
        capture_output=True, text=True,
    )


def _build_armor_table(db_path):
    """Create a minimal skyrim_smithing_armor table."""
    conn = sqlite3.connect(db_path)
    cols = (
        "piece TEXT PRIMARY KEY, material_perk TEXT, armor_rating INTEGER, "
        "weight REAL, value INTEGER, id TEXT, "
        + ", ".join(f"{c} INTEGER DEFAULT 0" for c in ARMOR_MAT_COLS)
    )
    conn.execute(f"CREATE TABLE skyrim_smithing_armor ({cols})")
    conn.commit()
    conn.close()


def _build_weapons_table(db_path):
    conn = sqlite3.connect(db_path)
    cols = (
        "piece TEXT PRIMARY KEY, material_perk TEXT, damage INTEGER, "
        "weight REAL, value INTEGER, id TEXT, "
        + ", ".join(f"{c} INTEGER DEFAULT 0" for c in WEAPONS_MAT_COLS)
    )
    conn.execute(f"CREATE TABLE skyrim_smithing_weapons ({cols})")
    conn.commit()
    conn.close()


def _build_homestead_table(db_path):
    conn = sqlite3.connect(db_path)
    cols = (
        "section TEXT, location TEXT, stage TEXT, batch_size INTEGER, "
        + ", ".join(f"{c} INTEGER DEFAULT 0" for c in HOMESTEAD_MAT_COLS)
    )
    conn.execute(f"CREATE TABLE skyrim_homestead_build ({cols})")
    conn.execute(
        "CREATE UNIQUE INDEX idx_skyrim_homestead_build "
        "ON skyrim_homestead_build(section, location)"
    )
    conn.commit()
    conn.close()


# ── armor SQL loader ──────────────────────────────────────────────────────────

ARMOR_SAMPLE = [
    {"piece": "Amber Armor", "material_perk": "Glass Smithing",
     "armor_rating": 40, "weight": 30.0, "value": 1100, "id": "xx000BC3",
     **{c: 0 for c in ARMOR_MAT_COLS}, "refined_amber": 4, "refined_moonstone": 1},
    {"piece": "Amber Boots", "material_perk": "Glass Smithing",
     "armor_rating": 13, "weight": 5.0, "value": 350, "id": "xx000BC4",
     **{c: 0 for c in ARMOR_MAT_COLS}, "refined_amber": 1, "leather_strips": 2},
]


@pytest.fixture
def armor_json(tmp_path):
    p = tmp_path / "armor.json"
    p.write_text(json.dumps(ARMOR_SAMPLE))
    return str(p)


def test_armor_sql_upsert(armor_json, tmp_db):
    _build_armor_table(tmp_db)
    result = run(ARMOR_SCRIPT, [armor_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT count(*) FROM skyrim_smithing_armor").fetchone()[0]
    conn.close()
    assert count == 2


def test_armor_sql_values(armor_json, tmp_db):
    _build_armor_table(tmp_db)
    run(ARMOR_SCRIPT, [armor_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        "SELECT armor_rating, refined_amber FROM skyrim_smithing_armor "
        "WHERE piece='Amber Armor'"
    ).fetchone()
    conn.close()
    assert row == (40, 4)


def test_armor_sql_idempotent(armor_json, tmp_db):
    _build_armor_table(tmp_db)
    run(ARMOR_SCRIPT, [armor_json, tmp_db])
    run(ARMOR_SCRIPT, [armor_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT count(*) FROM skyrim_smithing_armor").fetchone()[0]
    conn.close()
    assert count == 2  # no duplicates on second run


def test_armor_sql_missing_table_exits_nonzero(armor_json, tmp_db):
    # Don't create the table — loader should error
    conn = sqlite3.connect(tmp_db)
    conn.close()
    result = run(ARMOR_SCRIPT, [armor_json, tmp_db])
    assert result.returncode != 0


def test_armor_sql_bad_db_exits_nonzero(armor_json):
    result = run(ARMOR_SCRIPT, [armor_json, "/nonexistent_xyz/db.sqlite3"])
    assert result.returncode != 0


# ── weapons SQL loader ────────────────────────────────────────────────────────

WEAPONS_SAMPLE = [
    {"piece": "Elven Crossbow", "material_perk": "Elven Smithing",
     "damage": 19, "weight": 14.0, "value": 700, "id": "FExxx801",
     **{c: 0 for c in WEAPONS_MAT_COLS}, "refined_moonstone": 5},
    {"piece": "Enhanced Elven Crossbow", "material_perk": "Elven Smithing",
     "damage": 21, "weight": 14.0, "value": 900, "id": "FExxx809",
     **{c: 0 for c in WEAPONS_MAT_COLS}, "refined_moonstone": 2, "elven_crossbow": 1},
]


@pytest.fixture
def weapons_json(tmp_path):
    p = tmp_path / "weapons.json"
    p.write_text(json.dumps(WEAPONS_SAMPLE))
    return str(p)


def test_weapons_sql_upsert(weapons_json, tmp_db):
    _build_weapons_table(tmp_db)
    result = run(WEAPONS_SCRIPT, [weapons_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT count(*) FROM skyrim_smithing_weapons").fetchone()[0]
    conn.close()
    assert count == 2


def test_weapons_sql_elven_crossbow_col(weapons_json, tmp_db):
    _build_weapons_table(tmp_db)
    run(WEAPONS_SCRIPT, [weapons_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        "SELECT elven_crossbow FROM skyrim_smithing_weapons "
        "WHERE piece='Enhanced Elven Crossbow'"
    ).fetchone()
    conn.close()
    assert row[0] == 1


def test_weapons_sql_idempotent(weapons_json, tmp_db):
    _build_weapons_table(tmp_db)
    run(WEAPONS_SCRIPT, [weapons_json, tmp_db])
    run(WEAPONS_SCRIPT, [weapons_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT count(*) FROM skyrim_smithing_weapons").fetchone()[0]
    conn.close()
    assert count == 2


# ── ammo SQL loader ───────────────────────────────────────────────────────────

AMMO_SAMPLE = [
    {"piece": "Fire Arrow", "type": "arrow", "damage": 8, "weight": 0.0,
     "value": 2, "id": "FExxx802", "batch_size": 10, "material_perk": None,
     "firewood": 1, "void_salts": 0, "fire_salts": 4, "frost_salts": 0,
     "soul_gem_arrowhead": 0, "dragon_bone": 0, "corkbulb_root": 0, "bonemeal": 0},
    {"piece": "Bonemold Bolt", "type": "bolt", "damage": 15, "weight": 0.0,
     "value": 3, "id": "FExxx840", "batch_size": None, "material_perk": "Steel Smithing",
     "firewood": 0, "void_salts": 0, "fire_salts": 0, "frost_salts": 0,
     "soul_gem_arrowhead": 0, "dragon_bone": 0, "corkbulb_root": 0, "bonemeal": 0},
]


@pytest.fixture
def ammo_json(tmp_path):
    p = tmp_path / "ammo.json"
    p.write_text(json.dumps(AMMO_SAMPLE))
    return str(p)


def test_ammo_sql_creates_table(ammo_json, tmp_db):
    result = run(AMMO_SCRIPT, [ammo_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE name='skyrim_smithing_ammo'"
    )
    assert cur.fetchone() is not None
    conn.close()


def test_ammo_sql_row_count(ammo_json, tmp_db):
    run(AMMO_SCRIPT, [ammo_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT count(*) FROM skyrim_smithing_ammo").fetchone()[0]
    conn.close()
    assert count == 2


def test_ammo_sql_values(ammo_json, tmp_db):
    run(AMMO_SCRIPT, [ammo_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        "SELECT type, batch_size, firewood, fire_salts FROM skyrim_smithing_ammo "
        "WHERE piece='Fire Arrow'"
    ).fetchone()
    conn.close()
    assert row == ("arrow", 10, 1, 4)


def test_ammo_sql_null_batch_for_bolts(ammo_json, tmp_db):
    run(AMMO_SCRIPT, [ammo_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    val = conn.execute(
        "SELECT batch_size FROM skyrim_smithing_ammo WHERE piece='Bonemold Bolt'"
    ).fetchone()[0]
    conn.close()
    assert val is None


def test_ammo_sql_index_created(ammo_json, tmp_db):
    run(AMMO_SCRIPT, [ammo_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_skyrim_smithing_ammo'"
    )
    assert cur.fetchone() is not None
    conn.close()


def test_ammo_sql_idempotent(ammo_json, tmp_db):
    run(AMMO_SCRIPT, [ammo_json, tmp_db])
    run(AMMO_SCRIPT, [ammo_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute("SELECT count(*) FROM skyrim_smithing_ammo").fetchone()[0]
    conn.close()
    assert count == 2


# ── homestead SQL loader ──────────────────────────────────────────────────────

def _aquarium_row(**kwargs):
    row = {"section": "Test Item", "location": "Main_Hall_Aquarium",
           "stage": None, "batch_size": None}
    for col in HOMESTEAD_MAT_COLS:
        row[col] = 0
    row.update(kwargs)
    return row


HOMESTEAD_SAMPLE = [
    _aquarium_row(section="Fishing Supplies", sawn_log=1, nails=1, iron_ingot=1),
    _aquarium_row(section="Cupboard", sawn_log=2, nails=4, iron_fittings=1),
]


@pytest.fixture
def homestead_json(tmp_path):
    p = tmp_path / "homestead.json"
    p.write_text(json.dumps(HOMESTEAD_SAMPLE))
    return str(p)


def test_homestead_sql_upsert(homestead_json, tmp_db):
    _build_homestead_table(tmp_db)
    result = run(HOMESTEAD_SCRIPT, [homestead_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(
        "SELECT count(*) FROM skyrim_homestead_build WHERE location='Main_Hall_Aquarium'"
    ).fetchone()[0]
    conn.close()
    assert count == 2


def test_homestead_sql_values(homestead_json, tmp_db):
    _build_homestead_table(tmp_db)
    run(HOMESTEAD_SCRIPT, [homestead_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    row = conn.execute(
        "SELECT sawn_log, nails, iron_ingot FROM skyrim_homestead_build "
        "WHERE section='Fishing Supplies'"
    ).fetchone()
    conn.close()
    assert row == (1, 1, 1)


def test_homestead_sql_replaces_location_on_rerun(homestead_json, tmp_db, tmp_path):
    _build_homestead_table(tmp_db)
    run(HOMESTEAD_SCRIPT, [homestead_json, tmp_db])

    new_data = [_aquarium_row(section="Only Item", sawn_log=5)]
    new_json = str(tmp_path / "new.json")
    Path(new_json).write_text(json.dumps(new_data))
    run(HOMESTEAD_SCRIPT, [new_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(
        "SELECT count(*) FROM skyrim_homestead_build WHERE location='Main_Hall_Aquarium'"
    ).fetchone()[0]
    conn.close()
    assert count == 1  # previous rows replaced


def test_homestead_sql_missing_table_exits_nonzero(homestead_json, tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.close()
    result = run(HOMESTEAD_SCRIPT, [homestead_json, tmp_db])
    assert result.returncode != 0


# ── materials SQL loader ──────────────────────────────────────────────────────

MATERIALS_SAMPLE = [
    {"smithing_category": "Amber",   "crafting_material": "Refined Amber"},
    {"smithing_category": "Golden",  "crafting_material": "Gold Ingot"},
]


@pytest.fixture
def materials_json(tmp_path):
    p = tmp_path / "materials.json"
    p.write_text(json.dumps(MATERIALS_SAMPLE))
    return str(p)


def test_materials_sql_creates_table(materials_json, tmp_db):
    result = run(MATERIALS_SCRIPT, [materials_json, tmp_db])
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE name='skyrim_tempering_materials'"
    )
    assert cur.fetchone() is not None
    conn.close()


def test_materials_sql_row_count(materials_json, tmp_db):
    run(MATERIALS_SCRIPT, [materials_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(
        "SELECT count(*) FROM skyrim_tempering_materials"
    ).fetchone()[0]
    conn.close()
    assert count == 2


def test_materials_sql_values(materials_json, tmp_db):
    run(MATERIALS_SCRIPT, [materials_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    val = conn.execute(
        "SELECT crafting_material FROM skyrim_tempering_materials "
        "WHERE smithing_category='Amber'"
    ).fetchone()[0]
    conn.close()
    assert val == "Refined Amber"


def test_materials_sql_idempotent(materials_json, tmp_db):
    run(MATERIALS_SCRIPT, [materials_json, tmp_db])
    run(MATERIALS_SCRIPT, [materials_json, tmp_db])

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(
        "SELECT count(*) FROM skyrim_tempering_materials"
    ).fetchone()[0]
    conn.close()
    assert count == 2
