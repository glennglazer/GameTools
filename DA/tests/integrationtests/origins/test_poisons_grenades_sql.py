"""Integration tests for DA/Origins/poisons_grenades/poisons_grenades_sql/create_or_update_origins_poisons_grenades.py"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

loader = load_module(
    "DA/Origins/poisons_grenades/poisons_grenades_sql/create_or_update_origins_poisons_grenades.py",
    "create_or_update_origins_poisons_grenades",
)

# ─── Fixture data ─────────────────────────────────────────────────────────────

RECIPES = [
    {
        "name": "Deathroot Extract Recipe",
        "type": "poison",
        "result": "Deathroot Extract",
        "description": "A recipe for a poisonous weapon coating.",
        "item_id": "gen_im_cft_psn_102",
        "tier": 1,
        "ingredient1": "Deathroot",
        "quantity1": 1,
        "ingredient2": "Flask",
        "quantity2": 1,
        "ingredient3": None,
        "quantity3": None,
        "ingredient4": None,
        "quantity4": None,
    },
    {
        "name": "Fire Bomb Recipe",
        "type": "grenade",
        "result": "Fire Bomb",
        "description": "Recipe for fire bombs.",
        "item_id": "gen_im_cft_psn_206",
        "tier": 2,
        "ingredient1": "Fire Crystal",
        "quantity1": 1,
        "ingredient2": "Flask",
        "quantity2": 1,
        "ingredient3": "Corrupter Agent",
        "quantity3": 1,
        "ingredient4": None,
        "quantity4": None,
    },
    {
        "name": "Magebane Poison Recipe",
        "type": "poison",
        "result": "Magebane",
        "description": "Drains mana from target.",
        "item_id": "gen_im_cft_psn_310",
        "tier": 3,
        "ingredient1": "Lyrium Dust",
        "quantity1": 3,
        "ingredient2": "Flask",
        "quantity2": 1,
        "ingredient3": "Corrupter Agent",
        "quantity3": 2,
        "ingredient4": "Concentrator Agent",
        "quantity4": 1,
    },
]

ING_RECS = [
    {"ingredient": "Concentrator Agent", "recipe": "Magebane Poison Recipe", "quantity": 1},
    {"ingredient": "Corrupter Agent", "recipe": "Fire Bomb Recipe", "quantity": 1},
    {"ingredient": "Corrupter Agent", "recipe": "Magebane Poison Recipe", "quantity": 2},
    {"ingredient": "Deathroot", "recipe": "Deathroot Extract Recipe", "quantity": 1},
    {"ingredient": "Fire Crystal", "recipe": "Fire Bomb Recipe", "quantity": 1},
    {"ingredient": "Flask", "recipe": "Deathroot Extract Recipe", "quantity": 1},
    {"ingredient": "Flask", "recipe": "Fire Bomb Recipe", "quantity": 1},
    {"ingredient": "Flask", "recipe": "Magebane Poison Recipe", "quantity": 1},
    {"ingredient": "Lyrium Dust", "recipe": "Magebane Poison Recipe", "quantity": 3},
]

TIERS = [
    {"recipe": "Deathroot Extract Recipe", "tier": 1},
    {"recipe": "Fire Bomb Recipe", "tier": 2},
    {"recipe": "Magebane Poison Recipe", "tier": 3},
]

SUPPLY = [
    {"ingredient": "Flask", "vendor": "Bartender", "location": "Gnawed Noble Tavern", "note": None},
    {"ingredient": "Flask", "vendor": "Bodahn Feddic", "location": "Party Camp", "note": None},
    {"ingredient": "Lyrium Dust", "vendor": "Quartermaster", "location": "Circle Tower", "note": None},
    {"ingredient": "Corrupter Agent", "vendor": "Alimar", "location": "Dust Town",
     "note": "If not forced to accept bribe of 10 silvers for information"},
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def write_json(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return str(p)


def run_loader(tmp_path, recipes=None, ing_recs=None, tiers=None, supply=None):
    import pandas as pd
    import sqlite3 as _sqlite3

    recipes = recipes or RECIPES
    ing_recs = ing_recs or ING_RECS
    tiers = tiers or TIERS
    supply = supply or SUPPLY

    db_path = str(tmp_path / "test.sqlite3")
    conn = _sqlite3.connect(db_path)
    cur = conn.cursor()

    loader.upsert_by_key(conn, cur, pd.DataFrame(recipes), loader.RECIPES_TABLE, "name")
    loader.upsert_ingredient_recipes(conn, cur, pd.DataFrame(ing_recs))
    loader.upsert_by_key(conn, cur, pd.DataFrame(tiers), loader.TIERS_TABLE, "recipe")
    loader.full_replace(conn, cur, pd.DataFrame(supply), loader.SUPPLY_TABLE)

    conn.close()
    return db_path


# ─── Initial load ─────────────────────────────────────────────────────────────

class TestInitialLoad:
    def test_tables_created(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "origins_poisons_grenades_recipes" in tables
        assert "origins_poisons_grenades_ingredient_recipes" in tables
        assert "origins_poisons_grenades_tiers" in tables
        assert "origins_poisons_grenades_unlimited_supply" in tables

    def test_recipe_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_poisons_grenades_recipes").fetchone()[0]
        conn.close()
        assert n == 3

    def test_type_column_poison(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        t = conn.execute(
            "SELECT type FROM origins_poisons_grenades_recipes WHERE name='Deathroot Extract Recipe'"
        ).fetchone()[0]
        conn.close()
        assert t == "poison"

    def test_type_column_grenade(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        t = conn.execute(
            "SELECT type FROM origins_poisons_grenades_recipes WHERE name='Fire Bomb Recipe'"
        ).fetchone()[0]
        conn.close()
        assert t == "grenade"

    def test_filter_by_type_grenade(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT name FROM origins_poisons_grenades_recipes WHERE type='grenade'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "Fire Bomb Recipe"

    def test_filter_by_type_poison(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT name FROM origins_poisons_grenades_recipes WHERE type='poison'"
        ).fetchall()
        conn.close()
        assert len(rows) == 2

    def test_nullable_ingredient4(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT ingredient3, ingredient4 FROM origins_poisons_grenades_recipes WHERE name='Deathroot Extract Recipe'"
        ).fetchone()
        conn.close()
        assert row == (None, None)

    def test_four_ingredient_recipe(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT ingredient1, ingredient2, ingredient3, ingredient4 "
            "FROM origins_poisons_grenades_recipes WHERE name='Magebane Poison Recipe'"
        ).fetchone()
        conn.close()
        assert row == ("Lyrium Dust", "Flask", "Corrupter Agent", "Concentrator Agent")

    def test_ingredient_recipes_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_poisons_grenades_ingredient_recipes").fetchone()[0]
        conn.close()
        assert n == 9

    def test_tiers_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_poisons_grenades_tiers").fetchone()[0]
        conn.close()
        assert n == 3

    def test_supply_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_poisons_grenades_unlimited_supply").fetchone()[0]
        conn.close()
        assert n == 4

    def test_supply_note_stored(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        note = conn.execute(
            "SELECT note FROM origins_poisons_grenades_unlimited_supply WHERE vendor='Alimar'"
        ).fetchone()[0]
        conn.close()
        assert note is not None
        assert "bribe" in note


# ─── Upsert behaviour ─────────────────────────────────────────────────────────

class TestUpsert:
    def test_no_duplicates_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        loader.upsert_by_key(conn, cur, pd.DataFrame(RECIPES), loader.RECIPES_TABLE, "name")
        n = conn.execute("SELECT COUNT(*) FROM origins_poisons_grenades_recipes").fetchone()[0]
        conn.close()
        assert n == 3

    def test_type_updated_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        modified = [{**RECIPES[0], "type": "grenade"}]  # flip a poison to grenade
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        loader.upsert_by_key(conn, cur, pd.DataFrame(modified), loader.RECIPES_TABLE, "name")
        t = conn.execute(
            "SELECT type FROM origins_poisons_grenades_recipes WHERE name='Deathroot Extract Recipe'"
        ).fetchone()[0]
        conn.close()
        assert t == "grenade"

    def test_supply_full_replace(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        loader.full_replace(conn, cur, pd.DataFrame([SUPPLY[0]]), loader.SUPPLY_TABLE)
        n = conn.execute("SELECT COUNT(*) FROM origins_poisons_grenades_unlimited_supply").fetchone()[0]
        conn.close()
        assert n == 1


# ─── Query patterns ───────────────────────────────────────────────────────────

class TestQueryPatterns:
    def test_reverse_lookup_flask(self, tmp_path):
        """Which recipes use Flask?"""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        recipes = {
            r[0] for r in conn.execute(
                "SELECT recipe FROM origins_poisons_grenades_ingredient_recipes WHERE ingredient='Flask'"
            ).fetchall()
        }
        conn.close()
        assert "Deathroot Extract Recipe" in recipes
        assert "Fire Bomb Recipe" in recipes
        assert "Magebane Poison Recipe" in recipes

    def test_grenade_tier_all_two(self, tmp_path):
        """Confirm all grenades in this fixture are tier 2."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT r.name, t.tier FROM origins_poisons_grenades_recipes r "
            "JOIN origins_poisons_grenades_tiers t ON r.name = t.recipe "
            "WHERE r.type = 'grenade'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][1] == 2

    def test_ingredient_count_matches_wide_table(self, tmp_path):
        """Wide table non-null ingredient count agrees with ingredient_recipes join count."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        for recipe_name in [r["name"] for r in RECIPES]:
            row = conn.execute(
                "SELECT ingredient1, ingredient2, ingredient3, ingredient4 "
                "FROM origins_poisons_grenades_recipes WHERE name = ?",
                (recipe_name,)
            ).fetchone()
            wide_count = sum(1 for v in row if v is not None)
            join_count = conn.execute(
                "SELECT COUNT(*) FROM origins_poisons_grenades_ingredient_recipes WHERE recipe = ?",
                (recipe_name,)
            ).fetchone()[0]
            assert wide_count == join_count, f"Mismatch for {recipe_name}"
        conn.close()
