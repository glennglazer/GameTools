"""Integration tests for DA/Awakening/herbalism/herbalism_sql/create_or_update_awakening_herbalism.py"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

loader = load_module(
    "DA/Awakening/herbalism/herbalism_sql/create_or_update_awakening_herbalism.py",
    "create_or_update_awakening_herbalism",
)

# ─── Fixture data ─────────────────────────────────────────────────────────────

RECIPES = [
    {
        "name": "Lesser Stamina Draught Recipe",
        "result": "Lesser Stamina Draught",
        "description": None,
        "item_id": "gxa_im_cft_hrb_101",
        "tier": 4,
        "ingredient1": "Deep Mushroom", "quantity1": 1,
        "ingredient2": "Flask",         "quantity2": 1,
        "ingredient3": None, "quantity3": None,
        "ingredient4": None, "quantity4": None,
    },
    {
        "name": "Master Health Poultice Recipe",
        "result": "Master Health Poultice",
        "description": None,
        "item_id": "gxa_im_cft_hrb_405",
        "tier": 4,
        "ingredient1": "Elfroot",            "quantity1": 8,
        "ingredient2": "Flask",              "quantity2": 1,
        "ingredient3": "Distillation Agent", "quantity3": 8,
        "ingredient4": "Concentrator Agent", "quantity4": 8,
    },
    {
        "name": "Superb Lyrium Potion Recipe",
        "result": "Superb Lyrium Potion",
        "description": None,
        "item_id": "gxa_im_cft_hrb_403",
        "tier": 4,
        "ingredient1": "Lyrium Dust",        "quantity1": 6,
        "ingredient2": "Flask",              "quantity2": 1,
        "ingredient3": "Distillation Agent", "quantity3": 4,
        "ingredient4": "Concentrator Agent", "quantity4": 4,
    },
]

ING_RECS = [
    {"ingredient": "Concentrator Agent", "recipe": "Master Health Poultice Recipe",  "quantity": 8},
    {"ingredient": "Concentrator Agent", "recipe": "Superb Lyrium Potion Recipe",    "quantity": 4},
    {"ingredient": "Deep Mushroom",      "recipe": "Lesser Stamina Draught Recipe",  "quantity": 1},
    {"ingredient": "Distillation Agent", "recipe": "Master Health Poultice Recipe",  "quantity": 8},
    {"ingredient": "Distillation Agent", "recipe": "Superb Lyrium Potion Recipe",    "quantity": 4},
    {"ingredient": "Elfroot",            "recipe": "Master Health Poultice Recipe",  "quantity": 8},
    {"ingredient": "Flask",              "recipe": "Lesser Stamina Draught Recipe",  "quantity": 1},
    {"ingredient": "Flask",              "recipe": "Master Health Poultice Recipe",  "quantity": 1},
    {"ingredient": "Flask",              "recipe": "Superb Lyrium Potion Recipe",    "quantity": 1},
    {"ingredient": "Lyrium Dust",        "recipe": "Superb Lyrium Potion Recipe",    "quantity": 6},
]

TIERS = [
    {"recipe": "Lesser Stamina Draught Recipe",   "tier": 4},
    {"recipe": "Master Health Poultice Recipe",   "tier": 4},
    {"recipe": "Superb Lyrium Potion Recipe",     "tier": 4},
]

SUPPLY: list[dict] = []  # no Awakening supply data yet

EFFECTS = [
    {"name": "Lesser Stamina Draught", "type": "Stamina", "power": 50.0,  "effects": "Instantly restores (50 + SP) stamina"},
    {"name": "Master Health Poultice", "type": "Health",  "power": 300.0, "effects": "Instantly restores (50 + SP) * 6 health"},
    {"name": "Superb Lyrium Potion",   "type": "Mana",    "power": 250.0, "effects": "Instantly restores (50 + SP) * 5 mana"},
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def run_loader(tmp_path, recipes=None, ing_recs=None, tiers=None, supply=None, effects=None):
    import pandas as pd
    import sqlite3 as _sqlite3

    recipes  = recipes  or RECIPES
    ing_recs = ing_recs or ING_RECS
    tiers    = tiers    or TIERS
    supply   = supply   if supply  is not None else SUPPLY
    effects  = effects  if effects is not None else EFFECTS

    db_path = str(tmp_path / "test.sqlite3")
    conn = _sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")
    cur  = conn.cursor()

    loader.upsert_by_key(conn, cur, pd.DataFrame(recipes), loader.RECIPES_TABLE, "name")
    loader.upsert_ingredient_recipes(conn, cur, pd.DataFrame(ing_recs))
    loader.upsert_by_key(conn, cur, pd.DataFrame(tiers), loader.TIERS_TABLE, "recipe")
    df_supply = pd.DataFrame(supply, columns=loader._SUPPLY_COLUMNS) if supply else \
                pd.DataFrame(columns=loader._SUPPLY_COLUMNS)
    loader.full_replace(conn, cur, df_supply, loader.SUPPLY_TABLE)
    loader.upsert_by_key(conn, cur, pd.DataFrame(effects), loader.EFFECTS_TABLE, "name")

    conn.close()
    return db_path


# ─── Module-scoped shared DB (all read-only tests share one load) ─────────────

@pytest.fixture(scope="module")
def db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("shared")
    return run_loader(tmp)


# ─── Initial load ─────────────────────────────────────────────────────────────

class TestInitialLoad:
    def test_all_tables_created(self, db):
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "awakening_herbalism_recipes" in tables
        assert "awakening_herbalism_ingredient_recipes" in tables
        assert "awakening_herbalism_tiers" in tables
        assert "awakening_herbalism_unlimited_supply" in tables
        assert "awakening_herbalism_potion_effects" in tables

    def test_recipe_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM awakening_herbalism_recipes").fetchone()[0]
        conn.close()
        assert n == 3

    def test_result_column(self, db):
        conn = sqlite3.connect(db)
        result = conn.execute(
            "SELECT result FROM awakening_herbalism_recipes WHERE name='Master Health Poultice Recipe'"
        ).fetchone()[0]
        conn.close()
        assert result == "Master Health Poultice"

    def test_gxa_item_id(self, db):
        conn = sqlite3.connect(db)
        item_id = conn.execute(
            "SELECT item_id FROM awakening_herbalism_recipes WHERE name='Lesser Stamina Draught Recipe'"
        ).fetchone()[0]
        conn.close()
        assert item_id == "gxa_im_cft_hrb_101"

    def test_all_recipes_tier_4(self, db):
        conn = sqlite3.connect(db)
        tiers = conn.execute("SELECT DISTINCT tier FROM awakening_herbalism_tiers").fetchall()
        conn.close()
        assert tiers == [(4,)]

    def test_ingredient_recipes_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM awakening_herbalism_ingredient_recipes").fetchone()[0]
        conn.close()
        assert n == 10

    def test_supply_table_empty(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM awakening_herbalism_unlimited_supply").fetchone()[0]
        conn.close()
        assert n == 0

    def test_effects_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM awakening_herbalism_potion_effects").fetchone()[0]
        conn.close()
        assert n == 3


# ─── Effects table ────────────────────────────────────────────────────────────

class TestEffectsTable:
    def test_stamina_type_stored(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type, power FROM awakening_herbalism_potion_effects WHERE name='Lesser Stamina Draught'"
        ).fetchone()
        conn.close()
        assert row[0] == "Stamina"
        assert row[1] == 50.0

    def test_health_type_stored(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type, power FROM awakening_herbalism_potion_effects WHERE name='Master Health Poultice'"
        ).fetchone()
        conn.close()
        assert row[0] == "Health"
        assert row[1] == 300.0

    def test_mana_type_stored(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type, power FROM awakening_herbalism_potion_effects WHERE name='Superb Lyrium Potion'"
        ).fetchone()
        conn.close()
        assert row[0] == "Mana"
        assert row[1] == 250.0

    def test_effects_text_stored(self, db):
        conn = sqlite3.connect(db)
        effects = conn.execute(
            "SELECT effects FROM awakening_herbalism_potion_effects WHERE name='Superb Lyrium Potion'"
        ).fetchone()[0]
        conn.close()
        assert "mana" in effects.lower()

    def test_unique_index_on_name(self, db):
        conn = sqlite3.connect(db)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO awakening_herbalism_potion_effects (name, type, power, effects) "
                "VALUES ('Superb Lyrium Potion', 'Mana', 250.0, NULL)"
            )
        conn.close()


# ─── Supply table edge cases ──────────────────────────────────────────────────

class TestSupplyTable:
    def test_empty_supply_creates_table(self, db):
        """An empty supply list still creates the table with correct columns."""
        conn = sqlite3.connect(db)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(awakening_herbalism_unlimited_supply)")}
        conn.close()
        assert "ingredient" in cols
        assert "vendor" in cols
        assert "location" in cols
        assert "note" in cols

    def test_supply_with_data(self, tmp_path):
        """Uses custom supply data — needs its own DB."""
        supply = [{"ingredient": "Elfroot", "vendor": "Yuriah", "location": "Vigil's Keep", "note": None}]
        db = run_loader(tmp_path, supply=supply)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT vendor, location FROM awakening_herbalism_unlimited_supply WHERE ingredient='Elfroot'"
        ).fetchone()
        conn.close()
        assert row == ("Yuriah", "Vigil's Keep")


# ─── Upsert behaviour ─────────────────────────────────────────────────────────

class TestUpsert:
    def test_no_recipe_duplicates_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        loader.upsert_by_key(conn, cur, pd.DataFrame(RECIPES), loader.RECIPES_TABLE, "name")
        n = conn.execute("SELECT COUNT(*) FROM awakening_herbalism_recipes").fetchone()[0]
        conn.close()
        assert n == 3

    def test_effect_updated_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        updated = [
            {"name": "Lesser Stamina Draught", "type": "Stamina", "power": 99.0,
             "effects": "Updated text"},
        ]
        loader.upsert_by_key(conn, cur, pd.DataFrame(updated), loader.EFFECTS_TABLE, "name")
        power = conn.execute(
            "SELECT power FROM awakening_herbalism_potion_effects WHERE name='Lesser Stamina Draught'"
        ).fetchone()[0]
        conn.close()
        assert power == 99.0


# ─── Query patterns ───────────────────────────────────────────────────────────

class TestQueryPatterns:
    def test_reverse_lookup_flask(self, db):
        """All three recipes use Flask."""
        conn = sqlite3.connect(db)
        recipes = {
            r[0] for r in conn.execute(
                "SELECT recipe FROM awakening_herbalism_ingredient_recipes WHERE ingredient='Flask'"
            ).fetchall()
        }
        conn.close()
        assert "Lesser Stamina Draught Recipe" in recipes
        assert "Master Health Poultice Recipe" in recipes
        assert "Superb Lyrium Potion Recipe"   in recipes

    def test_filter_by_type(self, db):
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT name FROM awakening_herbalism_potion_effects WHERE type='Stamina'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "Lesser Stamina Draught"

    def test_all_tiers_are_4(self, db):
        conn = sqlite3.connect(db)
        non_4 = conn.execute(
            "SELECT COUNT(*) FROM awakening_herbalism_tiers WHERE tier != 4"
        ).fetchone()[0]
        conn.close()
        assert non_4 == 0
