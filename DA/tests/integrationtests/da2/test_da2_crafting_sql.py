"""
Integration tests for create_or_update_da2_crafting.py

Loads 4-table DA2 crafting fixture data into a temp SQLite DB and verifies
schema, constraints, and idempotency (full-replace pattern).
"""

import json
import sqlite3
from pathlib import Path

import pytest
from conftest import load_module

mod = load_module(
    "DA/DA2/crafting/crafting_sql/create_or_update_da2_crafting.py",
    "create_or_update_da2_crafting",
)
run_loader = mod.run_loader

# ── fixture data ──────────────────────────────────────────────────────────────

LOCATIONS = [
    {"name": "Elfroot Potion",     "act": '{"acts":[1]}',     "location": "given by Lady Elegant in Lowtown"},
    {"name": "Restoration Potion", "act": '{"acts":[1,2,3]}', "location": "bought from Formari Herbalist shop in The Gallows"},
    {"name": "Rock Armor Potion",  "act": '{"acts":[2]}',     "location": "found in Lowtown at night"},
    {"name": "Rune of Protection", "act": '{"acts":[1]}',     "location": "gift from Worthy in Hightown"},
    {"name": "Rune of Fortune",    "act": '{"acts":[1,2,3]}', "location": "bought at the Black Emporium"},
    {"name": "Debilitating Poison","act": '{"acts":[1]}',     "location": "given in Darktown from Tomwise"},
]

RESOURCES = [
    {"name": "Elfroot",       "location": "The Bone Pit",      "quest": None,                  "description": "On the far south east end of the map.", "act": 1},
    {"name": "Deathroot",     "location": "Darktown",          "quest": None,                  "description": "On the south end of the map.", "act": 1},
    {"name": "Silverite",     "location": "Sundermount Caverns","quest": None,                 "description": "Next to the door in the fire pit room.", "act": 1},
    {"name": "Deep Mushroom",  "location": "Bone Pit Mines",   "quest": "The Bone Pit",        "description": "Up the first set of stairs.", "act": 1},
    {"name": "Glitterdust",   "location": "Holding Caves",     "quest": "A Bitter Pill",       "description": "Near where the four paths meet.", "act": 2},
    {"name": "Elfroot",       "location": "Sundermount",       "quest": None,                  "description": "In the stone ruin on the low path.", "act": 2},
    {"name": "Dragon's Blood","location": "The Bone Pit",      "quest": "Mine Massacre",       "description": "Collected from the High Dragon's corpse.", "act": 3},
    {"name": "Felandaris",    "location": "Pride's End",        "quest": "A New Path",          "description": "To the right of Audacity's idol.", "act": 3},
]

RECIPES = [
    # name, Elfroot, Spindleweed, Lyrium, Silverite, Orichalcum, Dragon's Blood, Gold, Silver, Bronze
    {"name": "Elfroot Potion",     "Ambrosia": 0, "Deathroot": 0, "Deep Mushroom": 0, "Dragon's Blood": 0,
     "Elfroot": 1, "Embrium": 0, "Felandaris": 0, "Glitterdust": 0,
     "Lyrium": 0, "Orichalcum": 0, "Silverite": 0, "Spindleweed": 0,
     "Gold": 0, "Silver": 37, "Bronze": 50},
    {"name": "Restoration Potion", "Ambrosia": 0, "Deathroot": 0, "Deep Mushroom": 0, "Dragon's Blood": 0,
     "Elfroot": 3, "Embrium": 0, "Felandaris": 0, "Glitterdust": 0,
     "Lyrium": 0, "Orichalcum": 0, "Silverite": 0, "Spindleweed": 2,
     "Gold": 0, "Silver": 49, "Bronze": 0},
    {"name": "Rune of Protection", "Ambrosia": 0, "Deathroot": 0, "Deep Mushroom": 0, "Dragon's Blood": 0,
     "Elfroot": 0, "Embrium": 0, "Felandaris": 0, "Glitterdust": 0,
     "Lyrium": 2, "Orichalcum": 0, "Silverite": 2, "Spindleweed": 0,
     "Gold": 0, "Silver": 30, "Bronze": 0},
    {"name": "Rune of Devastation","Ambrosia": 0, "Deathroot": 0, "Deep Mushroom": 0, "Dragon's Blood": 1,
     "Elfroot": 0, "Embrium": 0, "Felandaris": 0, "Glitterdust": 0,
     "Lyrium": 3, "Orichalcum": 4, "Silverite": 4, "Spindleweed": 0,
     "Gold": 0, "Silver": 75, "Bronze": 0},
]

EFFECTS = [
    {"name": "Elfroot Potion",     "effects": "Health regeneration: 80%; Injuries: -1"},
    {"name": "Restoration Potion", "effects": "Heals full health over time"},
    {"name": "Rune of Protection", "effects": "+10% armor"},
    {"name": "Rune of Devastation","effects": "+50% damage on crits"},
]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """Load all four tables into a fresh temp DB and return the path."""
    db_path = tmp_path_factory.mktemp("db") / "test.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.close()

    tmp = tmp_path_factory.mktemp("json")

    def write_json(data, fname):
        p = tmp / fname
        p.write_text(json.dumps(data))
        return p

    run_loader(
        write_json(LOCATIONS, "locations.json"),
        write_json(RESOURCES, "resources.json"),
        write_json(RECIPES,   "recipes.json"),
        write_json(EFFECTS,   "effects.json"),
        db_path,
    )
    return str(db_path)


# ── TestInitialLoad ───────────────────────────────────────────────────────────

class TestInitialLoad:
    def test_locations_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM da2_crafting_recipe_locations").fetchone()[0]
        conn.close()
        assert count == len(LOCATIONS)

    def test_resources_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM da2_crafting_resources").fetchone()[0]
        conn.close()
        assert count == len(RESOURCES)

    def test_recipes_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM da2_crafting_recipes").fetchone()[0]
        conn.close()
        assert count == len(RECIPES)

    def test_effects_row_count(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM da2_crafting_item_effects").fetchone()[0]
        conn.close()
        assert count == len(EFFECTS)

    def test_all_four_tables_exist(self, db):
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "da2_crafting_recipe_locations" in tables
        assert "da2_crafting_resources" in tables
        assert "da2_crafting_recipes" in tables
        assert "da2_crafting_item_effects" in tables


# ── TestLocationsTable ────────────────────────────────────────────────────────

class TestLocationsTable:
    def test_act_json_stored(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT act FROM da2_crafting_recipe_locations WHERE name='Elfroot Potion'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert json.loads(row[0]) == {"acts": [1]}

    def test_act_range_json(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT act FROM da2_crafting_recipe_locations WHERE name='Restoration Potion'"
        ).fetchone()
        conn.close()
        assert json.loads(row[0]) == {"acts": [1, 2, 3]}

    def test_location_text(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT location FROM da2_crafting_recipe_locations WHERE name='Rune of Fortune'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert "Black Emporium" in row[0]

    def test_unique_name_constraint(self, db):
        conn = sqlite3.connect(db)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO da2_crafting_recipe_locations (name, act, location) "
                "VALUES ('Elfroot Potion', '{\"acts\":[1]}', 'duplicate')"
            )
        conn.close()


# ── TestResourcesTable ────────────────────────────────────────────────────────

class TestResourcesTable:
    def test_null_quest(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT quest FROM da2_crafting_resources "
            "WHERE name='Elfroot' AND location='The Bone Pit' AND act=1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] is None

    def test_quest_value(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT quest FROM da2_crafting_resources "
            "WHERE name='Deep Mushroom'"
        ).fetchone()
        conn.close()
        assert row[0] == "The Bone Pit"

    def test_elfroot_two_acts(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM da2_crafting_resources WHERE name='Elfroot'"
        ).fetchone()[0]
        conn.close()
        assert count == 2

    def test_act_3_rows(self, db):
        conn = sqlite3.connect(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM da2_crafting_resources WHERE act=3"
        ).fetchone()[0]
        conn.close()
        assert count == 2

    def test_pk_unique_constraint(self, db):
        """(name, location, description, act) composite PK must be unique."""
        conn = sqlite3.connect(db)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO da2_crafting_resources (name, location, quest, description, act) "
                "VALUES ('Elfroot', 'The Bone Pit', NULL, 'On the far south east end of the map.', 1)"
            )
        conn.close()


# ── TestRecipesTable ──────────────────────────────────────────────────────────

class TestRecipesTable:
    def test_ingredient_columns_present(self, db):
        conn = sqlite3.connect(db)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(da2_crafting_recipes)").fetchall()}
        conn.close()
        expected_ingredients = {
            "Ambrosia", "Deathroot", "Deep Mushroom", "Dragon's Blood",
            "Elfroot", "Embrium", "Felandaris", "Glitterdust",
            "Lyrium", "Orichalcum", "Silverite", "Spindleweed",
        }
        assert expected_ingredients.issubset(cols)

    def test_elfroot_potion_ingredients(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT Elfroot, Spindleweed, Lyrium "
            "FROM da2_crafting_recipes WHERE name='Elfroot Potion'"
        ).fetchone()
        conn.close()
        assert row == (1, 0, 0)

    def test_devastation_four_ingredients(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT Lyrium, Silverite, Orichalcum, \"Dragon's Blood\" "
            "FROM da2_crafting_recipes WHERE name='Rune of Devastation'"
        ).fetchone()
        conn.close()
        assert row == (3, 4, 4, 1)

    def test_currency_columns(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT Gold, Silver, Bronze FROM da2_crafting_recipes "
            "WHERE name='Elfroot Potion'"
        ).fetchone()
        conn.close()
        assert row == (0, 37, 50)

    def test_high_cost_gold(self, db):
        """Rune of Devastation: 75 silver, 0 bronze."""
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT Gold, Silver, Bronze FROM da2_crafting_recipes "
            "WHERE name='Rune of Devastation'"
        ).fetchone()
        conn.close()
        assert row == (0, 75, 0)

    def test_unique_name_constraint(self, db):
        conn = sqlite3.connect(db)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO da2_crafting_recipes (name, Elfroot) VALUES ('Elfroot Potion', 99)"
            )
        conn.close()


# ── TestEffectsTable ──────────────────────────────────────────────────────────

class TestEffectsTable:
    def test_effects_stored(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT effects FROM da2_crafting_item_effects WHERE name='Elfroot Potion'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert "Health regeneration: 80%" in row[0]

    def test_effects_semicolon_separator(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT effects FROM da2_crafting_item_effects WHERE name='Elfroot Potion'"
        ).fetchone()
        conn.close()
        assert ";" in row[0]

    def test_unique_name_constraint(self, db):
        conn = sqlite3.connect(db)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO da2_crafting_item_effects (name, effects) "
                "VALUES ('Elfroot Potion', 'duplicate')"
            )
        conn.close()


# ── TestUniqueIndexes ─────────────────────────────────────────────────────────

class TestUniqueIndexes:
    def test_locations_index_exists(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_da2_crl_name'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_resources_pk_index_exists(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_da2_cr_pk'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_recipes_index_exists(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_da2_crec_name'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_effects_index_exists(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_da2_cie_name'"
        ).fetchone()
        conn.close()
        assert row is not None


# ── TestFullReplace ───────────────────────────────────────────────────────────

class TestFullReplace:
    def test_idempotent_on_rerun(self, tmp_path_factory):
        """Running the loader twice must not double the row count."""
        db_path = tmp_path_factory.mktemp("db2") / "test2.sqlite3"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.close()

        tmp = tmp_path_factory.mktemp("json2")

        def write_json(data, fname):
            p = tmp / fname
            p.write_text(json.dumps(data))
            return p

        lp = write_json(LOCATIONS, "locations.json")
        rp = write_json(RESOURCES, "resources.json")
        cp = write_json(RECIPES,   "recipes.json")
        ep = write_json(EFFECTS,   "effects.json")

        # Run twice
        run_loader(lp, rp, cp, ep, db_path)
        run_loader(lp, rp, cp, ep, db_path)

        conn = sqlite3.connect(str(db_path))
        loc_count = conn.execute("SELECT COUNT(*) FROM da2_crafting_recipe_locations").fetchone()[0]
        res_count = conn.execute("SELECT COUNT(*) FROM da2_crafting_resources").fetchone()[0]
        rec_count = conn.execute("SELECT COUNT(*) FROM da2_crafting_recipes").fetchone()[0]
        eff_count = conn.execute("SELECT COUNT(*) FROM da2_crafting_item_effects").fetchone()[0]
        conn.close()

        assert loc_count == len(LOCATIONS)
        assert res_count == len(RESOURCES)
        assert rec_count == len(RECIPES)
        assert eff_count == len(EFFECTS)
