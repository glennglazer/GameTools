"""Integration tests for DA/Origins/herbalism/herbalism_sql/create_or_update_origins_herbalism.py

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
    "DA/Origins/herbalism/herbalism_sql/create_or_update_origins_herbalism.py",
    "create_or_update_origins_herbalism",
)

# ─── Sample fixture data ───────────────────────────────────────────────────────

RECIPES = [
    {
        "name": "Health Poultice",
        "result": "Health Poultice",
        "description": "A basic healing salve.",
        "item_id": "gen_im_alc_hlp_minor",
        "tier": 1,
        "ingredient1": "Elfroot",
        "quantity1": 2,
        "ingredient2": "Flask",
        "quantity2": 1,
        "ingredient3": None,
        "quantity3": None,
        "ingredient4": None,
        "quantity4": None,
    },
    {
        "name": "Elixir of Grounding",
        "result": "Elixir of Grounding",
        "description": "Grants resistance to electricity.",
        "item_id": "gen_im_alc_elx_grounding",
        "tier": 3,
        "ingredient1": "Elfroot",
        "quantity1": 1,
        "ingredient2": "Lifestone",
        "quantity2": 1,
        "ingredient3": "Deep Mushroom",
        "quantity3": 2,
        "ingredient4": None,
        "quantity4": None,
    },
]

ING_RECS = [
    {"ingredient": "Deep Mushroom", "recipe": "Elixir of Grounding", "quantity": 2},
    {"ingredient": "Elfroot", "recipe": "Elixir of Grounding", "quantity": 1},
    {"ingredient": "Elfroot", "recipe": "Health Poultice", "quantity": 2},
    {"ingredient": "Flask", "recipe": "Health Poultice", "quantity": 1},
    {"ingredient": "Lifestone", "recipe": "Elixir of Grounding", "quantity": 1},
]

TIERS = [
    {"recipe": "Health Poultice", "tier": 1},
    {"recipe": "Elixir of Grounding", "tier": 3},
]

SUPPLY = [
    {"ingredient": "Elfroot", "vendor": "Jetta", "location": "Denerim Market District", "note": None},
    {"ingredient": "Elfroot", "vendor": "Cesar", "location": "Denerim Market District", "note": None},
    {"ingredient": "Deep Mushroom", "vendor": "Ruck", "location": "Ruck's Cave", "note": None},
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def write_json(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return str(p)


EFFECTS = [
    {
        "name": "Lesser Health Poultice",
        "type": "Health",
        "power": 50,
        "effects": "Instantly restores (50 + SP) health",
    },
    {
        "name": "Lesser Lyrium Potion",
        "type": "Mana",
        "power": 50,
        "effects": "Instantly restores (50 + 0.5 * SP) mana",
    },
    {
        "name": "Lesser Injury Kit",
        "type": "Injury",
        "power": 10,
        "effects": "Instantly regains 10 health and is cured of a single injury",
    },
    {
        "name": "Lesser Ice Salve",
        "type": "Cold Resistance",
        "power": 30,
        "effects": "+30% cold resistance for 180 seconds",
    },
    {
        "name": "Incense of Awareness",
        "type": None,
        "power": None,
        "effects": "+10 Defense for 120 seconds, -10 Mental Resistance for 120 seconds",
    },
]


def run_loader(tmp_path, recipes=None, ing_recs=None, tiers=None, supply=None, effects=None):
    recipes = recipes or RECIPES
    ing_recs = ing_recs or ING_RECS
    tiers = tiers or TIERS
    supply = supply or SUPPLY
    effects = effects or EFFECTS

    r_path = write_json(tmp_path, "recipes.json", recipes)
    ir_path = write_json(tmp_path, "ing_recs.json", ing_recs)
    t_path = write_json(tmp_path, "tiers.json", tiers)
    s_path = write_json(tmp_path, "supply.json", supply)
    e_path = write_json(tmp_path, "effects.json", effects)
    db_path = str(tmp_path / "test.sqlite3")

    # Call the main upsert functions directly (bypassing argparse)
    import pandas as pd
    import sqlite3 as _sqlite3

    conn = _sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")
    cur = conn.cursor()

    df_r = pd.DataFrame(recipes)
    df_ir = pd.DataFrame(ing_recs)
    df_t = pd.DataFrame(tiers)
    df_s = pd.DataFrame(supply)
    df_e = pd.DataFrame(effects)

    loader.upsert_by_key(conn, cur, df_r, loader.RECIPES_TABLE, "name")
    loader.upsert_ingredient_recipes(conn, cur, df_ir)
    loader.upsert_by_key(conn, cur, df_t, loader.TIERS_TABLE, "recipe")
    loader.full_replace(conn, cur, df_s, loader.SUPPLY_TABLE)
    loader.upsert_by_key(conn, cur, df_e, loader.EFFECTS_TABLE, "name")

    conn.close()
    return db_path


# ─── Module-scoped shared DB (all read-only tests share one load) ─────────────

@pytest.fixture(scope="module")
def db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("shared")
    return run_loader(tmp)


# ─── Tests: initial load ──────────────────────────────────────────────────────

class TestInitialLoad:
    def test_recipes_table_created(self, db):
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "origins_herbalism_recipes" in tables

    def test_recipes_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM origins_herbalism_recipes").fetchone()[0]
        conn.close()
        assert count == 2

    def test_ingredient_recipes_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM origins_herbalism_ingredient_recipes").fetchone()[0]
        conn.close()
        assert count == 5

    def test_tiers_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM origins_herbalism_tiers").fetchone()[0]
        conn.close()
        assert count == 2

    def test_supply_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM origins_herbalism_unlimited_supply").fetchone()[0]
        conn.close()
        assert count == 3

    def test_nullable_ingredient_columns(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT ingredient3, quantity3, ingredient4, quantity4 "
            "FROM origins_herbalism_recipes WHERE name='Health Poultice'"
        ).fetchone()
        conn.close()
        assert row == (None, None, None, None)

    def test_tier_value(self, db):
        conn = sqlite3.connect(db)
        tier = conn.execute(
            "SELECT tier FROM origins_herbalism_tiers WHERE recipe='Elixir of Grounding'"
        ).fetchone()[0]
        conn.close()
        assert tier == 3

    def test_supply_vendor_nullable(self, tmp_path):
        """Test that null vendor is handled correctly in supply table (uses custom supply)."""
        supply_with_null = SUPPLY + [
            {"ingredient": "Lifestone", "vendor": None, "location": "Lifestone's Cave", "note": None}
        ]
        db = run_loader(tmp_path, supply=supply_with_null)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT vendor FROM origins_herbalism_unlimited_supply WHERE ingredient='Lifestone'"
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_ingredient_recipe_query(self, db):
        """Verify the reverse-lookup query: what recipes use Elfroot?"""
        conn = sqlite3.connect(db)
        recipes = {
            r[0] for r in conn.execute(
                "SELECT recipe FROM origins_herbalism_ingredient_recipes WHERE ingredient='Elfroot'"
            ).fetchall()
        }
        conn.close()
        assert "Health Poultice" in recipes
        assert "Elixir of Grounding" in recipes


# ─── Tests: upsert (second load overwrites, no duplicates) ───────────────────

class TestUpsert:
    def test_recipes_no_duplicate_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        # Run again with same data
        import pandas as pd
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_r = pd.DataFrame(RECIPES)
        loader.upsert_by_key(conn, cur, df_r, loader.RECIPES_TABLE, "name")
        count = conn.execute("SELECT COUNT(*) FROM origins_herbalism_recipes").fetchone()[0]
        conn.close()
        assert count == 2

    def test_ingredient_recipes_no_duplicate_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_ir = pd.DataFrame(ING_RECS)
        loader.upsert_ingredient_recipes(conn, cur, df_ir)
        count = conn.execute("SELECT COUNT(*) FROM origins_herbalism_ingredient_recipes").fetchone()[0]
        conn.close()
        assert count == 5

    def test_supply_full_replace(self, tmp_path):
        db = run_loader(tmp_path)
        # Second load with fewer rows — full replace should clear the old ones
        import pandas as pd
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_s = pd.DataFrame([SUPPLY[0]])  # Only one row
        loader.full_replace(conn, cur, df_s, loader.SUPPLY_TABLE)
        count = conn.execute("SELECT COUNT(*) FROM origins_herbalism_unlimited_supply").fetchone()[0]
        conn.close()
        assert count == 1

    def test_recipe_updated_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        # Modify a recipe and reload
        import pandas as pd
        updated = [{**RECIPES[0], "tier": 2}]
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        df_r = pd.DataFrame(updated)
        loader.upsert_by_key(conn, cur, df_r, loader.RECIPES_TABLE, "name")
        tier = conn.execute(
            "SELECT tier FROM origins_herbalism_recipes WHERE name='Health Poultice'"
        ).fetchone()[0]
        conn.close()
        assert tier == 2


# ─── Tests: join correctness ─────────────────────────────────────────────────

class TestJoinQueries:
    def test_recipe_ingredients_join(self, db):
        """Wide table and join table agree on ingredient count for a recipe."""
        conn = sqlite3.connect(db)

        # From wide table: count non-null ingredient columns
        row = conn.execute(
            "SELECT ingredient1, ingredient2, ingredient3, ingredient4 "
            "FROM origins_herbalism_recipes WHERE name='Elixir of Grounding'"
        ).fetchone()
        wide_count = sum(1 for v in row if v is not None)

        # From join table
        join_count = conn.execute(
            "SELECT COUNT(*) FROM origins_herbalism_ingredient_recipes "
            "WHERE recipe='Elixir of Grounding'"
        ).fetchone()[0]

        conn.close()
        assert wide_count == join_count == 3

    def test_tier_join_with_recipes(self, db):
        """Tier table joins cleanly to recipes table."""
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT r.name, t.tier FROM origins_herbalism_recipes r "
            "JOIN origins_herbalism_tiers t ON r.name = t.recipe"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        names = {r[0] for r in rows}
        assert "Health Poultice" in names
        assert "Elixir of Grounding" in names


# ─── Tests: potion effects table ─────────────────────────────────────────────

class TestPotionEffects:
    def test_effects_table_created(self, db):
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "origins_herbalism_potion_effects" in tables

    def test_effects_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM origins_herbalism_potion_effects"
        ).fetchone()[0]
        conn.close()
        assert count == 5

    def test_health_type_and_power(self, db):
        """Health potions now have power computed at SP=0."""
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type, power FROM origins_herbalism_potion_effects "
            "WHERE name='Lesser Health Poultice'"
        ).fetchone()
        conn.close()
        assert row[0] == "Health"
        assert row[1] == 50  # (50 + SP) at SP=0

    def test_injury_power_stored(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type, power FROM origins_herbalism_potion_effects "
            "WHERE name='Lesser Injury Kit'"
        ).fetchone()
        conn.close()
        assert row[0] == "Injury"
        assert row[1] == 10

    def test_resistance_power_stored(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type, power FROM origins_herbalism_potion_effects "
            "WHERE name='Lesser Ice Salve'"
        ).fetchone()
        conn.close()
        assert row[0] == "Cold Resistance"
        assert row[1] == 30

    def test_buff_null_type_and_power(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT type, power FROM origins_herbalism_potion_effects "
            "WHERE name='Incense of Awareness'"
        ).fetchone()
        conn.close()
        assert row[0] is None
        assert row[1] is None

    def test_effects_text_stored(self, db):
        conn = sqlite3.connect(db)
        effects = conn.execute(
            "SELECT effects FROM origins_herbalism_potion_effects "
            "WHERE name='Lesser Health Poultice'"
        ).fetchone()[0]
        conn.close()
        assert "50 + SP" in effects

    def test_no_duplicate_on_reload(self, db):
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        df_e = pd.DataFrame(EFFECTS)
        loader.upsert_by_key(conn, cur, df_e, loader.EFFECTS_TABLE, "name")
        count = conn.execute(
            "SELECT COUNT(*) FROM origins_herbalism_potion_effects"
        ).fetchone()[0]
        conn.close()
        assert count == 5

    def test_filter_by_type(self, db):
        """Querying by type works (resistance, buff, etc.)."""
        conn = sqlite3.connect(db)
        buffs = conn.execute(
            "SELECT name FROM origins_herbalism_potion_effects WHERE type IS NULL"
        ).fetchall()
        conn.close()
        assert len(buffs) == 1
        assert buffs[0][0] == "Incense of Awareness"
