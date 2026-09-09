"""Integration tests for
DA/Awakening/trap_making/trap_making_sql/create_or_update_awakening_trap_making.py

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
    "DA/Awakening/trap_making/trap_making_sql/create_or_update_awakening_trap_making.py",
    "create_or_update_awakening_trap_making",
)

# ─── Sample fixture data (mirrors the 4 actual Awakening trap-making recipes) ─

RECIPES = [
    {
        "name": "Dispel Trap Plans",
        "result": "Dispel Trap",
        "description": None,
        "item_id": "gxa_im_cft_trp_401",
        "tier": 4,
        "ingredient1": "Rashvine Nettle",    "quantity1": 1,
        "ingredient2": "Corrupter Agent",    "quantity2": 2,
        "ingredient3": "Trap Trigger",       "quantity3": 1,
        "ingredient4": "Concentrator Agent", "quantity4": 1,
    },
    {
        "name": "Elemental Trap Plans",
        "result": "Elemental Trap",
        "description": None,
        "item_id": "gxa_im_cft_trp_402",
        "tier": 4,
        "ingredient1": "Blood Lotus",        "quantity1": 1,
        "ingredient2": "Corrupter Agent",    "quantity2": 2,
        "ingredient3": "Trap Trigger",       "quantity3": 1,
        "ingredient4": "Concentrator Agent", "quantity4": 1,
    },
    {
        "name": "Gravity Trap Plans",
        "result": "Gravity Trap",
        "description": None,
        "item_id": "gxa_im_cft_trp_403",
        "tier": 4,
        "ingredient1": "Glamour Charm",   "quantity1": 4,
        "ingredient2": "Corrupter Agent", "quantity2": 4,
        "ingredient3": "Trap Trigger",    "quantity3": 1,
        "ingredient4": None,              "quantity4": None,
    },
    {
        "name": "Misdirection Cloud Trap Plans",
        "result": "Misdirection Cloud Trap",
        "description": None,
        "item_id": "gxa_im_cft_trp_404",
        "tier": 4,
        "ingredient1": "Madcap Bulb",        "quantity1": 2,
        "ingredient2": "Corrupter Agent",    "quantity2": 2,
        "ingredient3": "Concentrator Agent", "quantity3": 2,
        "ingredient4": "Trap Trigger",       "quantity4": 1,
    },
]

ING_RECS = [
    {"ingredient": "Blood Lotus",        "recipe": "Elemental Trap Plans",           "quantity": 1},
    {"ingredient": "Concentrator Agent", "recipe": "Dispel Trap Plans",              "quantity": 1},
    {"ingredient": "Concentrator Agent", "recipe": "Elemental Trap Plans",           "quantity": 1},
    {"ingredient": "Concentrator Agent", "recipe": "Misdirection Cloud Trap Plans",  "quantity": 2},
    {"ingredient": "Corrupter Agent",    "recipe": "Dispel Trap Plans",              "quantity": 2},
    {"ingredient": "Corrupter Agent",    "recipe": "Elemental Trap Plans",           "quantity": 2},
    {"ingredient": "Corrupter Agent",    "recipe": "Gravity Trap Plans",             "quantity": 4},
    {"ingredient": "Corrupter Agent",    "recipe": "Misdirection Cloud Trap Plans",  "quantity": 2},
    {"ingredient": "Glamour Charm",      "recipe": "Gravity Trap Plans",             "quantity": 4},
    {"ingredient": "Madcap Bulb",        "recipe": "Misdirection Cloud Trap Plans",  "quantity": 2},
    {"ingredient": "Rashvine Nettle",    "recipe": "Dispel Trap Plans",              "quantity": 1},
    {"ingredient": "Trap Trigger",       "recipe": "Dispel Trap Plans",              "quantity": 1},
    {"ingredient": "Trap Trigger",       "recipe": "Elemental Trap Plans",           "quantity": 1},
    {"ingredient": "Trap Trigger",       "recipe": "Gravity Trap Plans",             "quantity": 1},
    {"ingredient": "Trap Trigger",       "recipe": "Misdirection Cloud Trap Plans",  "quantity": 1},
]

TIERS = [
    {"recipe": "Dispel Trap Plans",              "tier": 4},
    {"recipe": "Elemental Trap Plans",           "tier": 4},
    {"recipe": "Gravity Trap Plans",             "tier": 4},
    {"recipe": "Misdirection Cloud Trap Plans",  "tier": 4},
]

EFFECTS = [
    {
        "name": "Dispel Trap",
        "damage_type": None,
        "power": None,
        "effect": "When triggered, this trap dispels all magical effects within a large area. Friendly fire possible.",
    },
    {
        "name": "Elemental Trap",
        "damage_type": "cold, electricity, fire, nature, spirit",
        "power": 200,
        "effect": None,
    },
    {
        "name": "Gravity Trap",
        "damage_type": None,
        "power": None,
        "effect": "When triggered, this trap pulses with waves that pull nearby creatures back to the trap every few seconds. Pulses every 4 seconds. 20 second duration Friendly fire bugged and does not happen.",
    },
    {
        "name": "Misdirection Cloud Trap",
        "damage_type": None,
        "power": None,
        "effect": "When triggered, this trap generates a cloud that causes creatures within to suffer from frustrating inaccuracy. All hits become misses, while critical hits become normal hits. 20 second duration. Friendly fire bugged and does not happen.",
    },
]

SUPPLY: list[dict] = []  # Always empty for Awakening trap-making


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
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")
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


# ─── Module-scoped shared DB (all read-only tests share one load) ─────────────

@pytest.fixture(scope="module")
def db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("shared")
    return run_loader(tmp)


# ─── Tests: initial load ──────────────────────────────────────────────────────

class TestInitialLoad:
    def test_all_tables_created(self, db):
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        for table in [
            loader.RECIPES_TABLE, loader.ING_REC_TABLE, loader.TIERS_TABLE,
            loader.SUPPLY_TABLE, loader.EFFECTS_TABLE,
        ]:
            assert table in tables

    def test_recipe_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.RECIPES_TABLE}").fetchone()[0]
        conn.close()
        assert count == 4

    def test_gxa_item_ids(self, db):
        conn = sqlite3.connect(db)
        ids = [r[0] for r in conn.execute(
            f"SELECT item_id FROM {loader.RECIPES_TABLE}"
        ).fetchall()]
        conn.close()
        for item_id in ids:
            assert item_id is None or item_id.startswith("gxa_")

    def test_all_tiers_4(self, db):
        conn = sqlite3.connect(db)
        tiers = {r[0] for r in conn.execute(
            f"SELECT DISTINCT tier FROM {loader.TIERS_TABLE}"
        ).fetchall()}
        conn.close()
        assert tiers == {4}

    def test_ingredient_recipes_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.ING_REC_TABLE}").fetchone()[0]
        conn.close()
        assert count == 15

    def test_supply_table_empty(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.SUPPLY_TABLE}").fetchone()[0]
        conn.close()
        assert count == 0

    def test_effects_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.EFFECTS_TABLE}").fetchone()[0]
        conn.close()
        assert count == 4

    def test_gravity_has_null_ingredient4(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT ingredient4 FROM {loader.RECIPES_TABLE} WHERE name='Gravity Trap Plans'"
        ).fetchone()
        conn.close()
        assert row[0] is None


# ─── Tests: effects table content ─────────────────────────────────────────────

class TestEffectsTable:
    def test_elemental_damage_type(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT damage_type, power FROM {loader.EFFECTS_TABLE} WHERE name='Elemental Trap'"
        ).fetchone()
        conn.close()
        assert row[0] == "cold, electricity, fire, nature, spirit"
        assert row[1] == 200

    def test_elemental_effect_null(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT effect FROM {loader.EFFECTS_TABLE} WHERE name='Elemental Trap'"
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_dispel_null_damage(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT damage_type, power FROM {loader.EFFECTS_TABLE} WHERE name='Dispel Trap'"
        ).fetchone()
        conn.close()
        assert row[0] is None
        assert row[1] is None

    def test_dispel_effect_text(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT effect FROM {loader.EFFECTS_TABLE} WHERE name='Dispel Trap'"
        ).fetchone()
        conn.close()
        assert row[0] is not None
        assert "dispels" in row[0].lower()

    def test_gravity_has_effect_text(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            f"SELECT effect FROM {loader.EFFECTS_TABLE} WHERE name='Gravity Trap'"
        ).fetchone()
        conn.close()
        assert row[0] is not None
        assert "pulses" in row[0].lower()

    def test_unique_index_on_name(self, db):
        conn = sqlite3.connect(db)
        idx = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='index' "
            f"AND tbl_name='{loader.EFFECTS_TABLE}'"
        ).fetchone()
        conn.close()
        assert idx is not None

    def test_effects_is_not_dual_damage(self, db):
        """Awakening traps have exactly one row each — no dual-damage splitting."""
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.EFFECTS_TABLE}").fetchone()[0]
        conn.close()
        assert count == 4


# ─── Tests: supply table ──────────────────────────────────────────────────────

class TestSupplyTable:
    def test_empty_supply_creates_table_with_columns(self, db):
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
        """Uses custom supply data — needs its own DB."""
        supply_data = [{"ingredient": "Trap Trigger", "vendor": "Alimar", "location": "Dust Town", "note": None}]
        db = run_loader(tmp_path, supply=supply_data)
        conn = sqlite3.connect(db)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.SUPPLY_TABLE}").fetchone()[0]
        conn.close()
        assert count == 1


# ─── Tests: upsert (no duplicates on second load) ─────────────────────────────

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
        """Modifies effect text — uses own DB to avoid contaminating shared fixture."""
        db = run_loader(tmp_path)
        import pandas as pd
        updated_effects = [
            {**e, "effect": "Updated effect text"} if e["name"] == "Gravity Trap" else e
            for e in EFFECTS
        ]
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_e = pd.DataFrame(updated_effects)
        loader.upsert_by_key(conn, cur, df_e, loader.EFFECTS_TABLE, "name")
        effect = conn.execute(
            f"SELECT effect FROM {loader.EFFECTS_TABLE} WHERE name='Gravity Trap'"
        ).fetchone()[0]
        conn.close()
        assert effect == "Updated effect text"

    def test_no_ing_rec_duplicates_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_ir = pd.DataFrame(ING_RECS)
        loader.upsert_ingredient_recipes(conn, cur, df_ir)
        count = conn.execute(f"SELECT COUNT(*) FROM {loader.ING_REC_TABLE}").fetchone()[0]
        conn.close()
        assert count == 15


# ─── Tests: query patterns ─────────────────────────────────────────────────────

class TestQueryPatterns:
    def test_trap_trigger_in_all_recipes(self, db):
        """Trap Trigger is used by all 4 recipes."""
        conn = sqlite3.connect(db)
        recipes = {r[0] for r in conn.execute(
            f"SELECT recipe FROM {loader.ING_REC_TABLE} WHERE ingredient='Trap Trigger'"
        ).fetchall()}
        conn.close()
        assert len(recipes) == 4

    def test_corrupter_agent_in_all_recipes(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(
            f"SELECT COUNT(*) FROM {loader.ING_REC_TABLE} WHERE ingredient='Corrupter Agent'"
        ).fetchone()[0]
        conn.close()
        assert count == 4

    def test_glamour_charm_only_in_gravity(self, db):
        conn = sqlite3.connect(db)
        recipes = [r[0] for r in conn.execute(
            f"SELECT recipe FROM {loader.ING_REC_TABLE} WHERE ingredient='Glamour Charm'"
        ).fetchall()]
        conn.close()
        assert recipes == ["Gravity Trap Plans"]

    def test_effects_join_to_recipes(self, db):
        """Join recipes to effects on result=name."""
        conn = sqlite3.connect(db)
        rows = conn.execute(
            f"SELECT r.name, e.damage_type, e.power "
            f"FROM {loader.RECIPES_TABLE} r "
            f"JOIN {loader.EFFECTS_TABLE} e ON r.result = e.name "
            f"WHERE e.damage_type IS NOT NULL"
        ).fetchall()
        conn.close()
        # Only Elemental Trap has a damage_type
        assert len(rows) == 1
        assert rows[0][0] == "Elemental Trap Plans"
        assert rows[0][2] == 200
