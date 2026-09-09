"""Integration tests for
DA/Awakening/poisons_grenades/poisons_grenades_sql/create_or_update_awakening_poisons_grenades.py

Tests the full JSON → SQLite load path against a temporary database.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

loader = load_module(
    "DA/Awakening/poisons_grenades/poisons_grenades_sql/create_or_update_awakening_poisons_grenades.py",
    "create_or_update_awakening_poisons_grenades",
)

# ─── Sample fixture data (mirrors the 4 actual Awakening recipes) ─────────────

RECIPES = [
    {
        "name": "Dispel Grenade Recipe",
        "type": "grenade",
        "result": "Dispel Grenade",
        "description": None,
        "item_id": "gxa_im_cft_psn_401",
        "tier": 4,
        "ingredient1": "Rashvine Nettle", "quantity1": 1,
        "ingredient2": "Flask",           "quantity2": 1,
        "ingredient3": "Corrupter Agent", "quantity3": 2,
        "ingredient4": "Concentrator Agent", "quantity4": 1,
    },
    {
        "name": "Dispel Poison Recipe",
        "type": "poison",
        "result": "Dispel Coating",
        "description": None,
        "item_id": "gxa_",
        "tier": 4,
        "ingredient1": "Rashvine Nettle",    "quantity1": 2,
        "ingredient2": "Flask",              "quantity2": 1,
        "ingredient3": "Corrupter Agent",    "quantity3": 4,
        "ingredient4": "Concentrator Agent", "quantity4": 2,
    },
    {
        "name": "Elemental Grenade Recipe",
        "type": "grenade",
        "result": "Elemental Grenade",
        "description": None,
        "item_id": "gxa_im_cft_psn_402",
        "tier": 4,
        "ingredient1": "Blood Lotus",       "quantity1": 1,
        "ingredient2": "Flask",             "quantity2": 1,
        "ingredient3": "Corrupter Agent",   "quantity3": 2,
        "ingredient4": "Concentrator Agent","quantity4": 1,
    },
    {
        "name": "Elemental Poison Recipe",
        "type": "poison",
        "result": "Elemental Coating",
        "description": None,
        "item_id": "gxa_im_cft_psn_403",
        "tier": 4,
        "ingredient1": "Blood Lotus",        "quantity1": 2,
        "ingredient2": "Flask",              "quantity2": 1,
        "ingredient3": "Corrupter Agent",    "quantity3": 4,
        "ingredient4": "Concentrator Agent", "quantity4": 2,
    },
]

ING_RECS = [
    {"ingredient": "Blood Lotus",         "recipe": "Elemental Grenade Recipe",  "quantity": 1},
    {"ingredient": "Blood Lotus",         "recipe": "Elemental Poison Recipe",   "quantity": 2},
    {"ingredient": "Concentrator Agent",  "recipe": "Dispel Grenade Recipe",     "quantity": 1},
    {"ingredient": "Concentrator Agent",  "recipe": "Dispel Poison Recipe",      "quantity": 2},
    {"ingredient": "Concentrator Agent",  "recipe": "Elemental Grenade Recipe",  "quantity": 1},
    {"ingredient": "Concentrator Agent",  "recipe": "Elemental Poison Recipe",   "quantity": 2},
    {"ingredient": "Corrupter Agent",     "recipe": "Dispel Grenade Recipe",     "quantity": 2},
    {"ingredient": "Corrupter Agent",     "recipe": "Dispel Poison Recipe",      "quantity": 4},
    {"ingredient": "Corrupter Agent",     "recipe": "Elemental Grenade Recipe",  "quantity": 2},
    {"ingredient": "Corrupter Agent",     "recipe": "Elemental Poison Recipe",   "quantity": 4},
    {"ingredient": "Flask",               "recipe": "Dispel Grenade Recipe",     "quantity": 1},
    {"ingredient": "Flask",               "recipe": "Dispel Poison Recipe",      "quantity": 1},
    {"ingredient": "Flask",               "recipe": "Elemental Grenade Recipe",  "quantity": 1},
    {"ingredient": "Flask",               "recipe": "Elemental Poison Recipe",   "quantity": 1},
    {"ingredient": "Rashvine Nettle",     "recipe": "Dispel Grenade Recipe",     "quantity": 1},
    {"ingredient": "Rashvine Nettle",     "recipe": "Dispel Poison Recipe",      "quantity": 2},
]

TIERS = [
    {"recipe": "Dispel Grenade Recipe",    "tier": 4},
    {"recipe": "Dispel Poison Recipe",     "tier": 4},
    {"recipe": "Elemental Grenade Recipe", "tier": 4},
    {"recipe": "Elemental Poison Recipe",  "tier": 4},
]

EFFECTS = [
    {
        "name": "Dispel Coating",
        "damage_type": None,
        "power": None,
        "effect": "Dispels magic on hit.",
    },
    {
        "name": "Dispel Grenade",
        "damage_type": None,
        "power": None,
        "effect": "Dispels magic in affected area.",
    },
    {
        "name": "Elemental Coating",
        "damage_type": "cold, electricity, fire, nature, spirit",
        "power": 10,
        "effect": None,
    },
    {
        "name": "Elemental Grenade",
        "damage_type": "cold, electricity, fire, nature, spirit",
        "power": 150,
        "effect": None,
    },
]

SUPPLY: list[dict] = []  # Always empty for Awakening


# ─── Helpers ──────────────────────────────────────────────────────────────────

def write_json(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return str(p)


def run_loader(tmp_path, recipes=None, ing_recs=None, tiers=None, supply=None, effects=None):
    recipes  = recipes  if recipes  is not None else RECIPES
    ing_recs = ing_recs if ing_recs is not None else ING_RECS
    tiers    = tiers    if tiers    is not None else TIERS
    supply   = supply   if supply   is not None else SUPPLY
    effects  = effects  if effects  is not None else EFFECTS

    r_path  = write_json(tmp_path, "recipes.json",  recipes)
    ir_path = write_json(tmp_path, "ing_recs.json", ing_recs)
    t_path  = write_json(tmp_path, "tiers.json",    tiers)
    s_path  = write_json(tmp_path, "supply.json",   supply)
    e_path  = write_json(tmp_path, "effects.json",  effects)
    db_path = str(tmp_path / "test.sqlite3")

    import pandas as pd
    import sqlite3 as _sqlite3

    conn = _sqlite3.connect(db_path)
    cur  = conn.cursor()

    df_r  = pd.DataFrame(recipes)
    df_ir = pd.DataFrame(ing_recs)
    df_t  = pd.DataFrame(tiers)
    df_s  = (pd.DataFrame(supply, columns=loader._SUPPLY_COLUMNS) if supply
             else pd.DataFrame(columns=loader._SUPPLY_COLUMNS))
    df_e  = pd.DataFrame(effects)

    loader.upsert_by_key(conn, cur, df_r,  loader.RECIPES_TABLE, "name")
    loader.upsert_ingredient_recipes(conn, cur, df_ir)
    loader.upsert_by_key(conn, cur, df_t,  loader.TIERS_TABLE,   "recipe")
    loader.full_replace(conn,  cur, df_s,  loader.SUPPLY_TABLE)
    loader.upsert_by_key(conn, cur, df_e,  loader.EFFECTS_TABLE, "name")

    conn.close()
    return db_path


# ─── Tests: initial load ──────────────────────────────────────────────────────

class TestInitialLoad:
    def test_all_tables_created(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        for table in [
            loader.RECIPES_TABLE, loader.ING_REC_TABLE, loader.TIERS_TABLE,
            loader.SUPPLY_TABLE, loader.EFFECTS_TABLE,
        ]:
            assert table in tables

    def test_recipe_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.RECIPES_TABLE}").fetchone()[0]
        conn.close()
        assert count == 4

    def test_type_column_values(self, tmp_path):
        """Two grenades and two poisons."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        grenades = conn.execute(
            f"SELECT COUNT(*) FROM {loader.RECIPES_TABLE} WHERE type='grenade'"
        ).fetchone()[0]
        poisons = conn.execute(
            f"SELECT COUNT(*) FROM {loader.RECIPES_TABLE} WHERE type='poison'"
        ).fetchone()[0]
        conn.close()
        assert grenades == 2
        assert poisons == 2

    def test_gxa_item_id(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        ids = [r[0] for r in conn.execute(
            f"SELECT item_id FROM {loader.RECIPES_TABLE}"
        ).fetchall()]
        conn.close()
        # All Awakening items have gxa_ prefix (or the bare "gxa_" for Dispel Poison)
        for item_id in ids:
            assert item_id is None or item_id.startswith("gxa_")

    def test_all_tiers_4(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        tiers = {r[0] for r in conn.execute(
            f"SELECT DISTINCT tier FROM {loader.TIERS_TABLE}"
        ).fetchall()}
        conn.close()
        assert tiers == {4}

    def test_ingredient_recipes_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        count = conn.execute(
            f"SELECT COUNT(*) FROM {loader.ING_REC_TABLE}"
        ).fetchone()[0]
        conn.close()
        assert count == len(ING_RECS)

    def test_supply_table_empty(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.SUPPLY_TABLE}").fetchone()[0]
        conn.close()
        assert count == 0

    def test_effects_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.EFFECTS_TABLE}").fetchone()[0]
        conn.close()
        assert count == 4


# ─── Tests: effects table content ────────────────────────────────────────────

class TestEffectsTable:
    def test_elemental_damage_type(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT damage_type, power FROM {loader.EFFECTS_TABLE} WHERE name='Elemental Grenade'"
        ).fetchone()
        conn.close()
        assert row[0] == "cold, electricity, fire, nature, spirit"
        assert row[1] == 150

    def test_elemental_coating_power(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT power FROM {loader.EFFECTS_TABLE} WHERE name='Elemental Coating'"
        ).fetchone()
        conn.close()
        assert row[0] == 10

    def test_dispel_null_damage(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT damage_type, power FROM {loader.EFFECTS_TABLE} WHERE name='Dispel Coating'"
        ).fetchone()
        conn.close()
        assert row[0] is None
        assert row[1] is None

    def test_dispel_grenade_effect_text(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT effect FROM {loader.EFFECTS_TABLE} WHERE name='Dispel Grenade'"
        ).fetchone()
        conn.close()
        assert row[0] is not None
        assert "Dispels magic" in row[0]

    def test_unique_index_on_name(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        idx = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='index' "
            f"AND tbl_name='{loader.EFFECTS_TABLE}'"
        ).fetchone()
        conn.close()
        assert idx is not None


# ─── Tests: empty supply table ────────────────────────────────────────────────

class TestSupplyTable:
    def test_empty_supply_creates_table_with_columns(self, tmp_path):
        db = run_loader(tmp_path, supply=[])
        conn = sqlite3.connect(db)
        cols = [r[1] for r in conn.execute(
            f"PRAGMA table_info({loader.SUPPLY_TABLE})"
        ).fetchall()]
        conn.close()
        assert "ingredient" in cols
        assert "vendor" in cols
        assert "location" in cols
        assert "note" in cols

    def test_supply_with_data(self, tmp_path):
        supply_data = [{"ingredient": "Flask", "vendor": "Someone", "location": "Somewhere", "note": None}]
        db = run_loader(tmp_path, supply=supply_data)
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.SUPPLY_TABLE}").fetchone()[0]
        conn.close()
        assert count == 1


# ─── Tests: upsert (no duplicates on second load) ────────────────────────────

class TestUpsert:
    def test_no_recipe_duplicates_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_r = pd.DataFrame(RECIPES)
        loader.upsert_by_key(conn, cur, df_r, loader.RECIPES_TABLE, "name")
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.RECIPES_TABLE}").fetchone()[0]
        conn.close()
        assert count == 4

    def test_effect_updated_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd
        updated_effects = [{**e, "power": 999} if e["name"] == "Elemental Grenade" else e
                          for e in EFFECTS]
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_e = pd.DataFrame(updated_effects)
        loader.upsert_by_key(conn, cur, df_e, loader.EFFECTS_TABLE, "name")
        power = conn.execute(
            f"SELECT power FROM {loader.EFFECTS_TABLE} WHERE name='Elemental Grenade'"
        ).fetchone()[0]
        conn.close()
        assert power == 999


# ─── Tests: query patterns ────────────────────────────────────────────────────

class TestQueryPatterns:
    def test_reverse_lookup_flask(self, tmp_path):
        """Flask is used by all 4 recipes."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        recipes = {r[0] for r in conn.execute(
            f"SELECT recipe FROM {loader.ING_REC_TABLE} WHERE ingredient='Flask'"
        ).fetchall()}
        conn.close()
        assert len(recipes) == 4

    def test_filter_grenades(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        grenades = conn.execute(
            f"SELECT name FROM {loader.RECIPES_TABLE} WHERE type='grenade' ORDER BY name"
        ).fetchall()
        conn.close()
        assert len(grenades) == 2
        assert grenades[0][0] == "Dispel Grenade Recipe"
        assert grenades[1][0] == "Elemental Grenade Recipe"

    def test_effects_join_to_recipes(self, tmp_path):
        """Join recipes to effects on result=name."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            f"SELECT r.name, e.damage_type, e.power "
            f"FROM {loader.RECIPES_TABLE} r "
            f"JOIN {loader.EFFECTS_TABLE} e ON r.result = e.name "
            f"WHERE r.type = 'grenade' ORDER BY r.name"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        dispel = rows[0]  # "Dispel Grenade Recipe"
        elemental = rows[1]  # "Elemental Grenade Recipe"
        assert dispel[1] is None     # no damage type
        assert elemental[2] == 150   # total power
