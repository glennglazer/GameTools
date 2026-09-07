"""Integration tests for DA/Origins/trap_making/trap_making_sql/create_or_update_origins_trap_making.py"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

loader = load_module(
    "DA/Origins/trap_making/trap_making_sql/create_or_update_origins_trap_making.py",
    "create_or_update_origins_trap_making",
)

# ─── Fixture data ─────────────────────────────────────────────────────────────

RECIPES = [
    {
        "name": "Small Caltrop Trap Plans",
        "result": "Small Caltrop Trap",
        "description": "Schematics to build a trap that releases small iron caltrops.",
        "item_id": "gen_im_cft_trp_102",
        "tier": 1,
        "ingredient1": "Metal Shard",
        "quantity1": 1,
        "ingredient2": None, "quantity2": None,
        "ingredient3": None, "quantity3": None,
        "ingredient4": None, "quantity4": None,
    },
    {
        "name": "Fire Trap Plans",
        "result": "Fire Trap",
        "description": "Directions for building a fire trap.",
        "item_id": "gen_im_cft_trp_208",
        "tier": 3,
        "ingredient1": "Fire Crystal",
        "quantity1": 1,
        "ingredient2": "Corrupter Agent",
        "quantity2": 1,
        "ingredient3": "Trap Trigger",
        "quantity3": 1,
        "ingredient4": None, "quantity4": None,
    },
    {
        "name": "Acidic Grease Trap Plans",
        "result": "Acidic Grease Trap",
        "description": "Directions for creating an acidic grease trap.",
        "item_id": "gen_im_cft_trp_307",
        "tier": 4,
        "ingredient1": "Lifestone",
        "quantity1": 3,
        "ingredient2": "Corrupter Agent",
        "quantity2": 2,
        "ingredient3": "Concentrator Agent",
        "quantity3": 2,
        "ingredient4": "Trap Trigger",
        "quantity4": 1,
    },
]

ING_RECS = [
    {"ingredient": "Concentrator Agent", "recipe": "Acidic Grease Trap Plans", "quantity": 2},
    {"ingredient": "Corrupter Agent", "recipe": "Acidic Grease Trap Plans", "quantity": 2},
    {"ingredient": "Corrupter Agent", "recipe": "Fire Trap Plans", "quantity": 1},
    {"ingredient": "Fire Crystal", "recipe": "Fire Trap Plans", "quantity": 1},
    {"ingredient": "Lifestone", "recipe": "Acidic Grease Trap Plans", "quantity": 3},
    {"ingredient": "Metal Shard", "recipe": "Small Caltrop Trap Plans", "quantity": 1},
    {"ingredient": "Trap Trigger", "recipe": "Acidic Grease Trap Plans", "quantity": 1},
    {"ingredient": "Trap Trigger", "recipe": "Fire Trap Plans", "quantity": 1},
]

TIERS = [
    {"recipe": "Small Caltrop Trap Plans", "tier": 1},
    {"recipe": "Fire Trap Plans", "tier": 3},
    {"recipe": "Acidic Grease Trap Plans", "tier": 4},
]

SUPPLY = [
    {"ingredient": "Concentrator Agent", "vendor": "Bartender", "location": "Gnawed Noble Tavern", "note": None},
    {"ingredient": "Concentrator Agent", "vendor": "Bodahn Feddic", "location": None, "note": None},
    {"ingredient": "Corrupter Agent", "vendor": "Bodahn Feddic", "location": None, "note": None},
    {"ingredient": "Corrupter Agent", "vendor": "Alimar", "location": "Dust Town", "note": "cheaper"},
    {"ingredient": "Trap Trigger", "vendor": "Alimar", "location": "Dust Town", "note": None},
    {"ingredient": "Trap Trigger", "vendor": "Barlin", "location": "Lothering", "note": "cheaper"},
    {"ingredient": "Lifestone", "vendor": "Ruck", "location": None, "note": None},
]

EFFECTS = [
    {
        "name": "Small Caltrop Trap",
        "damage_type": "physical",
        "power": 8,
        "effect": "-40% movement speed to creatures in the area",
    },
    {
        "name": "Fire Trap",
        "damage_type": "fire",
        "power": 100,
        "effect": None,
    },
    {
        "name": "Acidic Grease Trap",
        "damage_type": "nature",
        "power": -4,
        "effect": "-50% movement speed to creatures who enter the area",
    },
    {
        "name": "Spring Trap",
        "damage_type": None,
        "power": None,
        "effect": "Trap knocks down the target",
    },
    {
        "name": "Poisoned Caltrop Trap",
        "damage_type": "physical",
        "power": 8,
        "effect": "-40% movement speed to creatures in the area",
    },
    {
        "name": "Poisoned Caltrop Trap",
        "damage_type": "nature",
        "power": 8,
        "effect": "-40% movement speed to creatures in the area",
    },
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def run_loader(tmp_path, recipes=None, ing_recs=None, tiers=None, supply=None, effects=None):
    import pandas as pd
    import sqlite3 as _sqlite3

    recipes = recipes or RECIPES
    ing_recs = ing_recs or ING_RECS
    tiers = tiers or TIERS
    supply = supply if supply is not None else SUPPLY
    effects = effects if effects is not None else EFFECTS

    db_path = str(tmp_path / "test.sqlite3")
    conn = _sqlite3.connect(db_path)
    cur = conn.cursor()

    loader.upsert_by_key(conn, cur, pd.DataFrame(recipes), loader.RECIPES_TABLE, "name")
    loader.upsert_ingredient_recipes(conn, cur, pd.DataFrame(ing_recs))
    loader.upsert_by_key(conn, cur, pd.DataFrame(tiers), loader.TIERS_TABLE, "recipe")
    loader.full_replace(conn, cur, pd.DataFrame(supply), loader.SUPPLY_TABLE)
    loader.upsert_trap_effects(conn, cur, pd.DataFrame(effects))

    conn.close()
    return db_path


# ─── Initial load ─────────────────────────────────────────────────────────────

class TestInitialLoad:
    def test_all_tables_created(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "origins_trap_making_recipes" in tables
        assert "origins_trap_making_ingredient_recipes" in tables
        assert "origins_trap_making_tiers" in tables
        assert "origins_trap_making_unlimited_supply" in tables
        assert "origins_trap_making_effects" in tables

    def test_recipe_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_recipes").fetchone()[0]
        conn.close()
        assert n == 3

    def test_result_column_stored(self, tmp_path):
        """result (trap name) is distinct from name (plan name)."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        result = conn.execute(
            "SELECT result FROM origins_trap_making_recipes WHERE name='Fire Trap Plans'"
        ).fetchone()[0]
        conn.close()
        assert result == "Fire Trap"

    def test_nullable_ingredient4(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT ingredient2, ingredient4 FROM origins_trap_making_recipes "
            "WHERE name='Small Caltrop Trap Plans'"
        ).fetchone()
        conn.close()
        assert row == (None, None)

    def test_four_ingredient_recipe(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT ingredient1, ingredient2, ingredient3, ingredient4 "
            "FROM origins_trap_making_recipes WHERE name='Acidic Grease Trap Plans'"
        ).fetchone()
        conn.close()
        assert row == ("Lifestone", "Corrupter Agent", "Concentrator Agent", "Trap Trigger")

    def test_ingredient_recipes_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_ingredient_recipes").fetchone()[0]
        conn.close()
        assert n == 8

    def test_tiers_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_tiers").fetchone()[0]
        conn.close()
        assert n == 3

    def test_supply_count(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_unlimited_supply").fetchone()[0]
        conn.close()
        assert n == 7

    def test_effects_count(self, tmp_path):
        # 5 trap names; Poisoned Caltrop Trap has 2 rows (physical + nature) → 6 total
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_effects").fetchone()[0]
        conn.close()
        assert n == 6


# ─── Effects table ────────────────────────────────────────────────────────────

class TestEffectsTable:
    def test_physical_damage_stored(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT damage_type, power FROM origins_trap_making_effects WHERE name='Small Caltrop Trap'"
        ).fetchone()
        conn.close()
        assert row == ("physical", 8)

    def test_fire_damage_null_effect(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT damage_type, power, effect FROM origins_trap_making_effects WHERE name='Fire Trap'"
        ).fetchone()
        conn.close()
        assert row[0] == "fire"
        assert row[1] == 100
        assert row[2] is None

    def test_negative_power_stored(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        power = conn.execute(
            "SELECT power FROM origins_trap_making_effects WHERE name='Acidic Grease Trap'"
        ).fetchone()[0]
        conn.close()
        assert power == -4

    def test_dual_damage_type_stored(self, tmp_path):
        # Poisoned Caltrop Trap is stored as two rows — one per damage type
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT damage_type, power FROM origins_trap_making_effects "
            "WHERE name='Poisoned Caltrop Trap' ORDER BY damage_type"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        types = {r[0] for r in rows}
        assert "physical" in types
        assert "nature" in types
        for _, power in rows:
            assert power == 8

    def test_null_damage_with_effect(self, tmp_path):
        """Spring Trap: no damage, but has effect."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT damage_type, power, effect FROM origins_trap_making_effects WHERE name='Spring Trap'"
        ).fetchone()
        conn.close()
        assert row[0] is None
        assert row[1] is None
        assert row[2] is not None

    def test_effect_text_stored(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        effect = conn.execute(
            "SELECT effect FROM origins_trap_making_effects WHERE name='Small Caltrop Trap'"
        ).fetchone()[0]
        conn.close()
        assert "movement speed" in effect

    def test_unique_index_on_composite_key(self, tmp_path):
        """Duplicate (name, power, damage_type) should raise IntegrityError."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO origins_trap_making_effects (name, damage_type, power, effect) "
                "VALUES ('Fire Trap', 'fire', 100, NULL)"
            )
        conn.close()


# ─── Supply table ─────────────────────────────────────────────────────────────

class TestSupplyTable:
    def test_null_location_stored(self, tmp_path):
        """Bodahn Feddic has no location in the source."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT location FROM origins_trap_making_unlimited_supply "
            "WHERE vendor='Bodahn Feddic' AND ingredient='Concentrator Agent'"
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_cheaper_note_stored(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        note = conn.execute(
            "SELECT note FROM origins_trap_making_unlimited_supply "
            "WHERE ingredient='Corrupter Agent' AND vendor='Alimar'"
        ).fetchone()[0]
        conn.close()
        assert note == "cheaper"

    def test_ruck_null_location(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT vendor, location FROM origins_trap_making_unlimited_supply "
            "WHERE ingredient='Lifestone'"
        ).fetchone()
        conn.close()
        assert row == ("Ruck", None)


# ─── Upsert behaviour ─────────────────────────────────────────────────────────

class TestUpsert:
    def test_no_recipe_duplicates_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        loader.upsert_by_key(conn, cur, pd.DataFrame(RECIPES), loader.RECIPES_TABLE, "name")
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_recipes").fetchone()[0]
        conn.close()
        assert n == 3

    def test_no_effects_duplicates_on_reload(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        loader.upsert_trap_effects(conn, cur, pd.DataFrame(EFFECTS))
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_effects").fetchone()[0]
        conn.close()
        assert n == 6

    def test_supply_full_replace(self, tmp_path):
        db = run_loader(tmp_path)
        import pandas as pd, sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        cur = conn.cursor()
        loader.full_replace(conn, cur, pd.DataFrame([SUPPLY[0]]), loader.SUPPLY_TABLE)
        n = conn.execute("SELECT COUNT(*) FROM origins_trap_making_unlimited_supply").fetchone()[0]
        conn.close()
        assert n == 1


# ─── Query patterns ───────────────────────────────────────────────────────────

class TestQueryPatterns:
    def test_reverse_lookup_trap_trigger(self, tmp_path):
        """Which recipes use Trap Trigger?"""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        recipes = {
            r[0] for r in conn.execute(
                "SELECT recipe FROM origins_trap_making_ingredient_recipes WHERE ingredient='Trap Trigger'"
            ).fetchall()
        }
        conn.close()
        assert "Fire Trap Plans" in recipes
        assert "Acidic Grease Trap Plans" in recipes

    def test_tier4_recipes(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT r.name FROM origins_trap_making_recipes r "
            "JOIN origins_trap_making_tiers t ON r.name = t.recipe "
            "WHERE t.tier = 4"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "Acidic Grease Trap Plans"

    def test_damage_type_filter(self, tmp_path):
        """Filter effects by damage_type."""
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT name FROM origins_trap_making_effects WHERE damage_type='fire'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "Fire Trap"

    def test_ingredient_count_matches_wide_table(self, tmp_path):
        db = run_loader(tmp_path)
        conn = sqlite3.connect(db)
        for recipe_name in [r["name"] for r in RECIPES]:
            row = conn.execute(
                "SELECT ingredient1, ingredient2, ingredient3, ingredient4 "
                "FROM origins_trap_making_recipes WHERE name = ?",
                (recipe_name,)
            ).fetchone()
            wide_count = sum(1 for v in row if v is not None)
            join_count = conn.execute(
                "SELECT COUNT(*) FROM origins_trap_making_ingredient_recipes WHERE recipe = ?",
                (recipe_name,)
            ).fetchone()[0]
            assert wide_count == join_count, f"Mismatch for {recipe_name}"
        conn.close()
