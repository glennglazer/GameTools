"""TES GameTools MCP server — Morrowind, Oblivion, and Skyrim."""
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.pool import NullPool

_SCRIPT_DIR = Path(__file__).parent
_DB = (_SCRIPT_DIR.parent / 'database' / 'gametools.sqlite3').resolve()

# Read-only engine: the creator opens the file via SQLite URI mode=ro so no
# tool can accidentally mutate the database.
_engine = create_engine(
    "sqlite+pysqlite://",
    creator=lambda: sqlite3.connect(f"file:{_DB}?mode=ro", uri=True),
    poolclass=NullPool,
)

mcp = FastMCP("TES GameTools")


# ─── general rules ──────────────────────────────────────────────────────────

@mcp.resource("gametools://tes/rules")
def tes_general_rules() -> str:
    """Cross-game query conventions: explicit absence rule, NULL data, mechanic vs data gaps."""
    return (_SCRIPT_DIR / 'tes_general.md').read_text()


def _query(sql: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only SQL query and return rows as plain dicts."""
    with _engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


# ─── utility ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_tables() -> list[str]:
    """List all tables in the TES GameTools database."""
    rows = _query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r['name'] for r in rows]


# ─── Skyrim alchemy ─────────────────────────────────────────────────────────

@mcp.resource("gametools://skyrim/alchemy/rules")
def skyrim_alchemy_rules() -> str:
    """Skyrim alchemy mechanics, perk effects, and effect classification."""
    return (_SCRIPT_DIR / 'skyrim_alchemy.md').read_text()


@mcp.tool()
def skyrim_alchemy_ingredient(name: str) -> dict | None:
    """Return weight, value, and all four effects for a named Skyrim alchemy ingredient (case-insensitive exact match)."""
    rows = _query(
        "SELECT name, weight, value FROM skyrim_alchemy_ingredients WHERE LOWER(name) = LOWER(:name)",
        {"name": name},
    )
    if not rows:
        return None
    ing = rows[0]
    effects = _query(
        "SELECT effect FROM skyrim_alchemy_effects WHERE LOWER(name) = LOWER(:name) ORDER BY rowid",
        {"name": ing["name"]},
    )
    ing["effects"] = [r["effect"] for r in effects]
    return ing


@mcp.tool()
def skyrim_alchemy_search(query: str) -> list[dict]:
    """Search Skyrim alchemy ingredients by partial name (case-insensitive). Returns name, weight, and value."""
    return _query(
        "SELECT name, weight, value FROM skyrim_alchemy_ingredients "
        "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{query}%"},
    )


@mcp.tool()
def skyrim_alchemy_find_by_effect(effect: str) -> list[dict]:
    """Return all Skyrim ingredients that carry a given effect (partial match, case-insensitive), with the effect's base_magnitude and base_cost. Both are properties of the effect and are the same for every ingredient that carries it. base_cost is needed to compute potion value."""
    return _query(
        "SELECT DISTINCT name, base_magnitude, base_cost FROM skyrim_alchemy_effects "
        "WHERE LOWER(effect) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{effect}%"},
    )


@mcp.tool()
def skyrim_alchemy_combos(ingredients: list[str]) -> list[dict]:
    """Given a list of Skyrim ingredient names, return all pairs that share at least one effect and can therefore be combined into a potion."""
    if len(ingredients) < 2:
        return []
    sql = text(
        "SELECT e1.name AS ingredient_1, e2.name AS ingredient_2, e1.effect AS shared_effect "
        "FROM skyrim_alchemy_effects e1 "
        "JOIN skyrim_alchemy_effects e2 ON e1.effect = e2.effect AND e1.name < e2.name "
        "WHERE e1.name IN :ings AND e2.name IN :ings "
        "ORDER BY e1.name, e2.name, e1.effect"
    ).bindparams(bindparam("ings", expanding=True))
    with _engine.connect() as conn:
        result = conn.execute(sql, {"ings": ingredients})
        return [dict(row._mapping) for row in result]


@mcp.tool()
def skyrim_alchemy_list_effects() -> list[str]:
    """Return all 60 distinct Skyrim alchemy effects in alphabetical order."""
    rows = _query("SELECT DISTINCT effect FROM skyrim_alchemy_effects ORDER BY effect")
    return [r["effect"] for r in rows]


@mcp.tool()
def skyrim_alchemy_perks() -> list[dict]:
    """Return the full Skyrim alchemy perk tree with skill level requirements, prerequisites, and descriptions."""
    return _query("SELECT name, skill_level, prerequisite, description FROM skyrim_alchemy_perks ORDER BY skill_level, name")


# ─── Oblivion alchemy ───────────────────────────────────────────────────────

@mcp.resource("gametools://oblivion/alchemy/rules")
def oblivion_alchemy_rules() -> str:
    """Oblivion alchemy mechanics, mastery levels, apparatus interactions, and strength formulas."""
    return (_SCRIPT_DIR / 'oblivion_alchemy.md').read_text()


@mcp.tool()
def oblivion_alchemy_ingredient(name: str) -> dict | None:
    """Return weight, value, and all effects for a named Oblivion alchemy ingredient (case-insensitive exact match). Only effects visible at your Alchemy skill level count toward crafting."""
    rows = _query(
        "SELECT name, weight, value FROM oblivion_alchemy_ingredients WHERE LOWER(name) = LOWER(:name)",
        {"name": name},
    )
    if not rows:
        return None
    ing = rows[0]
    effects = _query(
        "SELECT effect FROM oblivion_alchemy_effects "
        "WHERE LOWER(name) = LOWER(:name) AND effect IS NOT NULL ORDER BY rowid",
        {"name": ing["name"]},
    )
    ing["effects"] = [r["effect"] for r in effects]
    return ing


@mcp.tool()
def oblivion_alchemy_search(query: str) -> list[dict]:
    """Search Oblivion alchemy ingredients by partial name (case-insensitive). Returns name, weight, and value."""
    return _query(
        "SELECT name, weight, value FROM oblivion_alchemy_ingredients "
        "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{query}%"},
    )


@mcp.tool()
def oblivion_alchemy_find_by_effect(effect: str) -> list[str]:
    """Return all Oblivion ingredient names that carry a given effect (partial match, case-insensitive)."""
    rows = _query(
        "SELECT DISTINCT name FROM oblivion_alchemy_effects "
        "WHERE effect IS NOT NULL AND LOWER(effect) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{effect}%"},
    )
    return [r["name"] for r in rows]


@mcp.tool()
def oblivion_alchemy_combos(ingredients: list[str]) -> list[dict]:
    """Given a list of Oblivion ingredient names, return all pairs that share at least one effect. Only effects visible at the character's Alchemy skill level are used in crafting — consult the rules resource for the mastery level table."""
    if len(ingredients) < 2:
        return []
    sql = text(
        "SELECT e1.name AS ingredient_1, e2.name AS ingredient_2, e1.effect AS shared_effect "
        "FROM oblivion_alchemy_effects e1 "
        "JOIN oblivion_alchemy_effects e2 ON e1.effect = e2.effect AND e1.name < e2.name "
        "WHERE e1.effect IS NOT NULL AND e1.name IN :ings AND e2.name IN :ings "
        "ORDER BY e1.name, e2.name, e1.effect"
    ).bindparams(bindparam("ings", expanding=True))
    with _engine.connect() as conn:
        result = conn.execute(sql, {"ings": ingredients})
        return [dict(row._mapping) for row in result]


@mcp.tool()
def oblivion_alchemy_list_effects() -> list[str]:
    """Return all distinct Oblivion alchemy effects in alphabetical order."""
    rows = _query(
        "SELECT DISTINCT effect FROM oblivion_alchemy_effects WHERE effect IS NOT NULL ORDER BY effect"
    )
    return [r["effect"] for r in rows]


@mcp.tool()
def oblivion_alchemy_apparatus(apparatus_type: str | None = None) -> list[dict]:
    """Return Oblivion alchemy apparatus with grade and strength. Optionally filter by type keyword: 'Mortar', 'Retort', 'Alembic', or 'Calcinator'."""
    if apparatus_type:
        return _query(
            "SELECT name, grade, weight, cost, strength FROM oblivion_alchemy_apparatus "
            "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY name, strength",
            {"pattern": f"%{apparatus_type}%"},
        )
    return _query(
        "SELECT name, grade, weight, cost, strength FROM oblivion_alchemy_apparatus "
        "ORDER BY name, strength"
    )


# ─── Morrowind alchemy ──────────────────────────────────────────────────────

@mcp.resource("gametools://morrowind/alchemy/rules")
def morrowind_alchemy_rules() -> str:
    """Morrowind alchemy mechanics, success chance, apparatus interactions, and strength formulas."""
    return (_SCRIPT_DIR / 'morrowind_alchemy.md').read_text()


@mcp.tool()
def morrowind_alchemy_ingredient(name: str) -> dict | None:
    """Return weight, value, and all effects for a named Morrowind alchemy ingredient (case-insensitive exact match). In Morrowind, hidden effects count toward crafting even if not yet visible at the character's Alchemy skill level."""
    rows = _query(
        "SELECT name, weight, value FROM morrowind_alchemy_ingredients WHERE LOWER(name) = LOWER(:name)",
        {"name": name},
    )
    if not rows:
        return None
    ing = rows[0]
    effects = _query(
        "SELECT effect FROM morrowind_alchemy_effects "
        "WHERE LOWER(name) = LOWER(:name) AND effect IS NOT NULL ORDER BY rowid",
        {"name": ing["name"]},
    )
    ing["effects"] = [r["effect"] for r in effects]
    return ing


@mcp.tool()
def morrowind_alchemy_search(query: str) -> list[dict]:
    """Search Morrowind alchemy ingredients by partial name (case-insensitive). Returns name, weight, and value."""
    return _query(
        "SELECT name, weight, value FROM morrowind_alchemy_ingredients "
        "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{query}%"},
    )


@mcp.tool()
def morrowind_alchemy_find_by_effect(effect: str) -> list[str]:
    """Return all Morrowind ingredient names that carry a given effect (partial match, case-insensitive). Includes effects that may be hidden at lower Alchemy skill levels — hidden effects can still be used in crafting."""
    rows = _query(
        "SELECT DISTINCT name FROM morrowind_alchemy_effects "
        "WHERE effect IS NOT NULL AND LOWER(effect) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{effect}%"},
    )
    return [r["name"] for r in rows]


@mcp.tool()
def morrowind_alchemy_combos(ingredients: list[str]) -> list[dict]:
    """Given a list of Morrowind ingredient names, return all pairs that share at least one effect. Unlike Oblivion, hidden effects count — this tool returns all possible combinations regardless of Alchemy skill visibility."""
    if len(ingredients) < 2:
        return []
    sql = text(
        "SELECT e1.name AS ingredient_1, e2.name AS ingredient_2, e1.effect AS shared_effect "
        "FROM morrowind_alchemy_effects e1 "
        "JOIN morrowind_alchemy_effects e2 ON e1.effect = e2.effect AND e1.name < e2.name "
        "WHERE e1.effect IS NOT NULL AND e1.name IN :ings AND e2.name IN :ings "
        "ORDER BY e1.name, e2.name, e1.effect"
    ).bindparams(bindparam("ings", expanding=True))
    with _engine.connect() as conn:
        result = conn.execute(sql, {"ings": ingredients})
        return [dict(row._mapping) for row in result]


@mcp.tool()
def morrowind_alchemy_list_effects() -> list[str]:
    """Return all distinct Morrowind alchemy effects in alphabetical order."""
    rows = _query(
        "SELECT DISTINCT effect FROM morrowind_alchemy_effects WHERE effect IS NOT NULL ORDER BY effect"
    )
    return [r["effect"] for r in rows]


@mcp.tool()
def morrowind_alchemy_apparatus(apparatus_type: str | None = None) -> list[dict]:
    """Return Morrowind alchemy apparatus with quality values. Optionally filter by type keyword: 'Mortar', 'Retort', 'Alembic', 'Calcinator', or 'Skooma'."""
    if apparatus_type:
        return _query(
            "SELECT name, weight, value, quality FROM morrowind_alchemy_apparatus "
            "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY quality, name",
            {"pattern": f"%{apparatus_type}%"},
        )
    return _query(
        "SELECT name, weight, value, quality FROM morrowind_alchemy_apparatus "
        "ORDER BY name, quality"
    )


# ─── Morrowind enchanting ───────────────────────────────────────────────────


# ─── Oblivion enchanting ────────────────────────────────────────────────────


# ─── Skyrim enchanting ──────────────────────────────────────────────────────

@mcp.resource("gametools://skyrim/enchanting/rules")
def skyrim_enchanting_rules() -> str:
    """Skyrim enchanting mechanics: formulae (patched/unpatched), charges, soul gems, perks."""
    return (_SCRIPT_DIR / 'skyrim_enchanting.md').read_text()


@mcp.tool()
def skyrim_enchant_perks() -> list[dict]:
    """Return all Skyrim enchanting perks with skill level, prerequisite, and description."""
    return _query(
        "SELECT name, skill_level, prerequisite, description "
        "FROM skyrim_enchant_perks ORDER BY skill_level, name"
    )


@mcp.tool()
def skyrim_enchant_weapon_effects(name: str | None = None) -> list[dict]:
    """Return Skyrim weapon enchantment effects with school and base_cost.
    Optional partial name filter. base_cost is used in the charges-per-use formula."""
    if name:
        return _query(
            "SELECT name, school, base_cost FROM skyrim_enchant_weapons "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY name",
            {"name": name},
        )
    return _query(
        "SELECT name, school, base_cost FROM skyrim_enchant_weapons ORDER BY name"
    )


@mcp.tool()
def skyrim_enchant_apparel_effects(
    slot: str | None = None,
    name: str | None = None,
) -> list[dict]:
    """Return Skyrim apparel enchantments with equip-slot flags and base_cost.
    Optional slot filter: head, chest, hands, feet, shield, amulet, or ring.
    Optional partial name filter. base_cost is used in the enchanting-for-profit calculation."""
    valid_slots = ('head', 'chest', 'hands', 'feet', 'shield', 'amulet', 'ring')
    where_clauses = []
    params: dict = {}

    if slot:
        slot = slot.lower()
        if slot not in valid_slots:
            return [{"error": f"Invalid slot '{slot}'. Choose from: {', '.join(valid_slots)}"}]
        where_clauses.append(f"{slot} = 1")

    if name:
        where_clauses.append("LOWER(enchantment) LIKE LOWER('%' || :name || '%')")
        params["name"] = name

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    return _query(
        f"SELECT enchantment, head, chest, hands, feet, shield, amulet, ring, base_cost "
        f"FROM skyrim_enchant_apparel {where} ORDER BY enchantment",
        params,
    )


@mcp.tool()
def skyrim_enchant_soul_gems() -> list[dict]:
    """Return Skyrim soul gem types with capacity, value, weight, and trappable soul description."""
    return _query(
        "SELECT name, weight, value, capacity, trappable_souls "
        "FROM skyrim_enchant_soulgems ORDER BY capacity, name"
    )


@mcp.tool()
def skyrim_enchant_souls(name: str | None = None) -> list[dict]:
    """Return Skyrim creature soul sizes (soul_size in charge points). Optional partial name filter.
    Souls of 3000 are black souls (humanoids) and require a black soul gem."""
    if name:
        return _query(
            "SELECT name, soul_size FROM skyrim_enchant_souls "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY soul_size, name",
            {"name": name},
        )
    return _query(
        "SELECT name, soul_size FROM skyrim_enchant_souls ORDER BY soul_size, name"
    )


@mcp.tool()
def skyrim_enchant_disenchant(effect: str) -> list[dict]:
    """Return items to disenchant to learn a given enchantment effect (partial name match).
    Searches both apparel and weapon disenchant tables. Returns effect, item, note, and type
    ('apparel' or 'weapon')."""
    params = {"effect": effect}
    apparel = _query(
        "SELECT effect, item, note, 'apparel' AS type "
        "FROM skyrim_enchant_disenchant_apparel "
        "WHERE LOWER(effect) LIKE LOWER('%' || :effect || '%') ORDER BY effect, item",
        params,
    )
    weapons = _query(
        "SELECT effect, item, note, 'weapon' AS type "
        "FROM skyrim_enchant_disenchant_weapons "
        "WHERE LOWER(effect) LIKE LOWER('%' || :effect || '%') ORDER BY effect, item",
        params,
    )
    return apparel + weapons


# ─── Skyrim smithing ────────────────────────────────────────────────────────


# ─── Skyrim homestead ───────────────────────────────────────────────────────


if __name__ == '__main__':
    mcp.run()
