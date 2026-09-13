"""
Integration tests for create_or_update_awakening_runecrafting.py

Tests that all 6 tables are created with correct row counts, JSON columns are
valid, nullable level column works for hybrid runes, and the full-replace
upsert is idempotent.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from conftest import REPO_ROOT, load_module

mod = load_module(
    "DA/Awakening/runecrafting/runecrafting_sql/create_or_update_awakening_runecrafting.py",
    "create_or_update_awakening_runecrafting",
)
run_loader = mod.run_loader

# ── fixture data ─────────────────────────────────────────────────────────────

SKILL = [
    {"level": "Runecrafting",          "character_level": 20, "rune_levels": '{"rune_levels": ["Journeyman", "Expert"]}'},
    {"level": "Improved Runecrafting", "character_level": 22, "rune_levels": '{"rune_levels": ["Master"]}'},
    {"level": "Expert Runecrafting",   "character_level": 24, "rune_levels": '{"rune_levels": ["Grandmaster", "Masterpiece"]}'},
    {"level": "Master Runecrafting",   "character_level": 26, "rune_levels": '{"rune_levels": ["Paragon"]}'},
]

TRACING = [
    {
        "tracing": "Flame", "type": "Weapon",
        "journeyman": '{"sources": ["Initial"]}',
        "expert":     '{"sources": ["Cera"]}',
        "master":     '{"sources": ["Cera"]}',
        "grandmaster":'{"sources": ["Cera"]}',
        "masterpiece":'{"sources": ["Kal\'Hirol - Trade Quarter"]}',
        "paragon":    '{"sources": ["Kal\'Hirol - Trade Quarter"]}',
    },
    {
        "tracing": "Dweomer", "type": "Weapon",
        "journeyman": '{"sources": ["Cera", "Octham"]}',
        "expert":     '{"sources": ["Octham"]}',
        "master":     '{"sources": ["Octham"]}',
        "grandmaster":'{"sources": ["Yuriah (+1 upgrade)"]}',
        "masterpiece":'{"sources": ["Yuriah (+2 upgrades)"]}',
        "paragon":    '{"sources": ["Yuriah (+3 upgrades)"]}',
    },
]

HYBRID = [
    {"tracing": "Intensifying", "type": "Weapon", "location": "Bartender at The Crown and Lion."},
    {"tracing": "Evasion",      "type": "Armor",  "location": "Cera"},
]

ARMOR_RUNES = [
    {"name": "Barrier",    "level": "Novice",  "effect": '{"effects": ["+1 armor"]}',  "description": "The Tevinter symbol for protection."},
    {"name": "Barrier",    "level": "Paragon",  "effect": '{"effects": ["+7 Armor"]}',  "description": "The Tevinter symbol for protection."},
    {"name": "Evasion",    "level": None,        "effect": '{"effects": ["+5% chance to dodge"]}', "description": "This shape is the closest to zero."},
]

WEAPON_RUNES = [
    {"name": "Flame",        "level": "Novice",     "effect": '{"effects": ["+1 Fire Damage"]}',  "description": "Ancient Tevinter symbol for fire."},
    {"name": "Flame",        "level": "Paragon",    "effect": '{"effects": ["+7 Fire Damage"]}',  "description": "Ancient Tevinter symbol for fire."},
    {"name": "Intensifying", "level": None,          "effect": '{"effects": ["5% ranged critical chance", "5% melee critical chance"]}', "description": "Something like bigger."},
]

COSTS = [
    {"name": "Novice Flame Rune",   "gold": 0, "silver": 60, "bronze": 0},
    {"name": "Novice Barrier Rune", "gold": 0, "silver": 65, "bronze": 0},
    {"name": "Blank Runestone",     "gold": 0, "silver": 0,  "bronze": 50},
    {"name": "Etching Agent",       "gold": 0, "silver": 8,  "bronze": 0},
]


# ── module-scoped shared db ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("db") / "test.sqlite3")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.close()

    tmp = tmp_path_factory.mktemp("json")

    def write(data, fname):
        p = tmp / fname
        p.write_text(json.dumps(data))
        return str(p)

    run_loader(
        Path(write(SKILL,        "skill.json")),
        Path(write(TRACING,      "tracing.json")),
        Path(write(HYBRID,       "hybrid.json")),
        Path(write(ARMOR_RUNES,  "armor.json")),
        Path(write(WEAPON_RUNES, "weapon.json")),
        Path(write(COSTS,        "costs.json")),
        Path(db_path),
    )
    return db_path


# ── TestInitialLoad ───────────────────────────────────────────────────────────

class TestInitialLoad:
    def test_skill_row_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM awakening_runecrafting_skill").fetchone()[0]
        conn.close()
        assert n == 4

    def test_tracing_row_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM awakening_runecrafting_tracing_acquisition"
        ).fetchone()[0]
        conn.close()
        assert n == 2

    def test_hybrid_tracing_row_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM awakening_runecrafting_hybrid_tracing_acquisition"
        ).fetchone()[0]
        conn.close()
        assert n == 2

    def test_armor_runes_row_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM awakening_runecrafting_armor_runes"
        ).fetchone()[0]
        conn.close()
        assert n == 3

    def test_weapon_runes_row_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM awakening_runecrafting_weapon_runes"
        ).fetchone()[0]
        conn.close()
        assert n == 3

    def test_costs_row_count(self, db):
        conn = sqlite3.connect(db)
        n = conn.execute(
            "SELECT COUNT(*) FROM awakening_runecrafting_costs"
        ).fetchone()[0]
        conn.close()
        assert n == 4

    def test_all_six_tables_exist(self, db):
        conn = sqlite3.connect(db)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        expected = {
            "awakening_runecrafting_skill",
            "awakening_runecrafting_tracing_acquisition",
            "awakening_runecrafting_hybrid_tracing_acquisition",
            "awakening_runecrafting_armor_runes",
            "awakening_runecrafting_weapon_runes",
            "awakening_runecrafting_costs",
        }
        assert expected.issubset(tables)


# ── TestJsonColumns ───────────────────────────────────────────────────────────

class TestJsonColumns:
    def test_skill_rune_levels_json(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT rune_levels FROM awakening_runecrafting_skill "
            "WHERE level = 'Runecrafting'"
        ).fetchone()
        conn.close()
        parsed = json.loads(row[0])
        assert parsed["rune_levels"] == ["Journeyman", "Expert"]

    def test_tracing_sources_json(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT journeyman FROM awakening_runecrafting_tracing_acquisition "
            "WHERE tracing = 'Flame'"
        ).fetchone()
        conn.close()
        assert json.loads(row[0])["sources"] == ["Initial"]

    def test_tracing_yuriah_upgrade_json(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT paragon FROM awakening_runecrafting_tracing_acquisition "
            "WHERE tracing = 'Dweomer'"
        ).fetchone()
        conn.close()
        assert json.loads(row[0])["sources"] == ["Yuriah (+3 upgrades)"]

    def test_armor_effect_json(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT effect FROM awakening_runecrafting_armor_runes "
            "WHERE name = 'Barrier' AND level = 'Novice'"
        ).fetchone()
        conn.close()
        parsed = json.loads(row[0])
        assert parsed["effects"] == ["+1 armor"]

    def test_weapon_multi_effect_json(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT effect FROM awakening_runecrafting_weapon_runes "
            "WHERE name = 'Intensifying'"
        ).fetchone()
        conn.close()
        parsed = json.loads(row[0])
        assert len(parsed["effects"]) == 2


# ── TestNullableLevel ─────────────────────────────────────────────────────────

class TestNullableLevel:
    def test_hybrid_armor_level_null(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT level FROM awakening_runecrafting_armor_runes "
            "WHERE name = 'Evasion'"
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_hybrid_weapon_level_null(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT level FROM awakening_runecrafting_weapon_runes "
            "WHERE name = 'Intensifying'"
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_non_hybrid_level_set(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT level FROM awakening_runecrafting_armor_runes "
            "WHERE name = 'Barrier' AND level = 'Novice'"
        ).fetchone()
        conn.close()
        assert row[0] == "Novice"


# ── TestCostsTable ────────────────────────────────────────────────────────────

class TestCostsTable:
    def test_blank_runestone_bronze(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT gold, silver, bronze FROM awakening_runecrafting_costs "
            "WHERE name = 'Blank Runestone'"
        ).fetchone()
        conn.close()
        assert row == (0, 0, 50)

    def test_etching_agent_silver(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT gold, silver, bronze FROM awakening_runecrafting_costs "
            "WHERE name = 'Etching Agent'"
        ).fetchone()
        conn.close()
        assert row == (0, 8, 0)

    def test_novice_flame_cost(self, db):
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT gold, silver, bronze FROM awakening_runecrafting_costs "
            "WHERE name = 'Novice Flame Rune'"
        ).fetchone()
        conn.close()
        assert row == (0, 60, 0)


# ── TestUpsert ────────────────────────────────────────────────────────────────

class TestUpsert:
    def test_full_replace_idempotent(self, tmp_path):
        """Re-running the loader replaces data, no duplicates."""
        db_path = str(tmp_path / "upsert.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.close()

        def write(data, name):
            p = tmp_path / name
            p.write_text(json.dumps(data))
            return Path(p)

        paths = dict(
            skill=write(SKILL,       "s.json"),
            tracing=write(TRACING,   "t.json"),
            hybrid=write(HYBRID,     "h.json"),
            armor=write(ARMOR_RUNES, "a.json"),
            weapon=write(WEAPON_RUNES,"w.json"),
            costs=write(COSTS,       "c.json"),
        )

        # Run twice — second run must produce same counts
        for _ in range(2):
            run_loader(
                paths["skill"], paths["tracing"], paths["hybrid"],
                paths["armor"], paths["weapon"], paths["costs"],
                Path(db_path),
            )

        conn = sqlite3.connect(db_path)
        n_skill  = conn.execute("SELECT COUNT(*) FROM awakening_runecrafting_skill").fetchone()[0]
        n_tracing = conn.execute(
            "SELECT COUNT(*) FROM awakening_runecrafting_tracing_acquisition"
        ).fetchone()[0]
        conn.close()
        assert n_skill   == 4
        assert n_tracing == 2
