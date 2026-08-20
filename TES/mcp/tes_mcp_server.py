"""TES GameTools MCP server — Morrowind, Oblivion, and Skyrim."""
import math
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
def skyrim_alchemy_list_ingredients() -> list[dict]:
    """Return all Skyrim alchemy ingredients with name, weight, value, and full effect list.
    Use for exhaustive searches — for example, finding every pair of ingredients
    whose all four effects overlap (perfect overlap), or any combinatorial analysis
    that requires the complete ingredient set at once."""
    ingredients = _query(
        "SELECT name, weight, value FROM skyrim_alchemy_ingredients ORDER BY name"
    )
    effects_rows = _query(
        "SELECT name, effect FROM skyrim_alchemy_effects ORDER BY name, rowid"
    )
    effects_map: dict[str, list[str]] = {}
    for r in effects_rows:
        effects_map.setdefault(r["name"], []).append(r["effect"])
    for ing in ingredients:
        ing["effects"] = effects_map.get(ing["name"], [])
    return ingredients


@mcp.tool()
def skyrim_alchemy_perfect_overlaps(min_shared: int = 4) -> list[dict]:
    """Find all Skyrim ingredient pairs whose effect sets share at least min_shared effects.
    Default min_shared=4 finds perfect overlaps (all four effects identical in any order).
    Use min_shared=3 to find near-perfect overlaps.
    Returns list of {ingredient_1, ingredient_2, shared_effects, shared_count}, sorted by
    shared_count descending then alphabetically — the computation runs in the tool,
    so the model never needs to enumerate pairs manually."""
    effects_rows = _query(
        "SELECT name, effect FROM skyrim_alchemy_effects ORDER BY name"
    )
    effects_map: dict[str, set[str]] = {}
    for r in effects_rows:
        effects_map.setdefault(r["name"], set()).add(r["effect"])
    names = sorted(effects_map)
    result = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared = effects_map[names[i]] & effects_map[names[j]]
            if len(shared) >= min_shared:
                result.append({
                    "ingredient_1": names[i],
                    "ingredient_2": names[j],
                    "shared_effects": sorted(shared),
                    "shared_count": len(shared),
                })
    result.sort(key=lambda r: (-r["shared_count"], r["ingredient_1"], r["ingredient_2"]))
    return result


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
def oblivion_alchemy_list_ingredients() -> list[dict]:
    """Return all Oblivion alchemy ingredients with name, weight, value, and full effect list.
    Use for exhaustive searches — for example, finding every pair of ingredients
    whose all four effects overlap (perfect overlap), or any combinatorial analysis
    that requires the complete ingredient set at once. Note that in Oblivion only
    effects visible at the character's current Alchemy skill level are usable in crafting."""
    ingredients = _query(
        "SELECT name, weight, value FROM oblivion_alchemy_ingredients ORDER BY name"
    )
    effects_rows = _query(
        "SELECT name, effect FROM oblivion_alchemy_effects "
        "WHERE effect IS NOT NULL ORDER BY name, rowid"
    )
    effects_map: dict[str, list[str]] = {}
    for r in effects_rows:
        effects_map.setdefault(r["name"], []).append(r["effect"])
    for ing in ingredients:
        ing["effects"] = effects_map.get(ing["name"], [])
    return ingredients


@mcp.tool()
def oblivion_alchemy_perfect_overlaps(min_shared: int = 4) -> list[dict]:
    """Find all Oblivion ingredient pairs whose effect sets share at least min_shared effects.
    Default min_shared=4 finds perfect overlaps (all four effects identical in any order).
    Use min_shared=3 to find near-perfect overlaps.
    Note: in Oblivion only effects visible at the character's current Alchemy skill level
    are usable in crafting — the DB stores all effects; the caller should keep this in mind.
    Returns list of {ingredient_1, ingredient_2, shared_effects, shared_count}, sorted by
    shared_count descending — the computation runs in the tool, so the model never needs to
    enumerate pairs manually."""
    effects_rows = _query(
        "SELECT name, effect FROM oblivion_alchemy_effects "
        "WHERE effect IS NOT NULL ORDER BY name"
    )
    effects_map: dict[str, set[str]] = {}
    for r in effects_rows:
        effects_map.setdefault(r["name"], set()).add(r["effect"])
    names = sorted(effects_map)
    result = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared = effects_map[names[i]] & effects_map[names[j]]
            if len(shared) >= min_shared:
                result.append({
                    "ingredient_1": names[i],
                    "ingredient_2": names[j],
                    "shared_effects": sorted(shared),
                    "shared_count": len(shared),
                })
    result.sort(key=lambda r: (-r["shared_count"], r["ingredient_1"], r["ingredient_2"]))
    return result


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
def morrowind_alchemy_list_ingredients() -> list[dict]:
    """Return all Morrowind alchemy ingredients with name, weight, value, and full effect list
    (including hidden effects). Use for exhaustive searches — for example, finding every pair
    of ingredients whose all four effects overlap (perfect overlap), or any combinatorial
    analysis that requires the complete ingredient set at once. Unlike Oblivion, hidden effects
    always count toward crafting in Morrowind regardless of Alchemy skill level."""
    ingredients = _query(
        "SELECT name, weight, value FROM morrowind_alchemy_ingredients ORDER BY name"
    )
    effects_rows = _query(
        "SELECT name, effect FROM morrowind_alchemy_effects "
        "WHERE effect IS NOT NULL ORDER BY name, rowid"
    )
    effects_map: dict[str, list[str]] = {}
    for r in effects_rows:
        effects_map.setdefault(r["name"], []).append(r["effect"])
    for ing in ingredients:
        ing["effects"] = effects_map.get(ing["name"], [])
    return ingredients


@mcp.tool()
def morrowind_alchemy_perfect_overlaps(min_shared: int = 4) -> list[dict]:
    """Find all Morrowind ingredient pairs whose effect sets share at least min_shared effects.
    Default min_shared=4 finds perfect overlaps (all four effects identical in any order).
    Use min_shared=3 to find near-perfect overlaps. Includes hidden effects — in Morrowind,
    hidden effects always count toward crafting regardless of Alchemy skill level.
    Returns list of {ingredient_1, ingredient_2, shared_effects, shared_count}, sorted by
    shared_count descending — the computation runs in the tool, so the model never needs to
    enumerate pairs manually."""
    effects_rows = _query(
        "SELECT name, effect FROM morrowind_alchemy_effects "
        "WHERE effect IS NOT NULL ORDER BY name"
    )
    effects_map: dict[str, set[str]] = {}
    for r in effects_rows:
        effects_map.setdefault(r["name"], set()).add(r["effect"])
    names = sorted(effects_map)
    result = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared = effects_map[names[i]] & effects_map[names[j]]
            if len(shared) >= min_shared:
                result.append({
                    "ingredient_1": names[i],
                    "ingredient_2": names[j],
                    "shared_effects": sorted(shared),
                    "shared_count": len(shared),
                })
    result.sort(key=lambda r: (-r["shared_count"], r["ingredient_1"], r["ingredient_2"]))
    return result


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

@mcp.resource("gametools://morrowind/enchanting/rules")
def morrowind_enchanting_rules() -> str:
    """Morrowind enchanting: self-enchant formulae, CE rules, compounding, recharge, alchemy-enchant loop."""
    return (_SCRIPT_DIR / 'morrowind_enchanting.md').read_text()


@mcp.tool()
def morrowind_enchant_magic_effects(
    name: str | None = None,
    school: str | None = None,
) -> list[dict]:
    """Return Morrowind magic effects with name, base_cost, school, and description.
    base_cost feeds the enchantment point formula: C = avg_magnitude × 0.05 × base_cost × duration.
    Optional partial name filter and/or school filter
    (Alteration/Conjuration/Destruction/Illusion/Mysticism/Restoration)."""
    valid_schools = ('Alteration', 'Conjuration', 'Destruction', 'Illusion', 'Mysticism', 'Restoration')
    where: list[str] = []
    params: dict = {}

    if school:
        matched = next((s for s in valid_schools if s.lower() == school.lower()), None)
        if not matched:
            return [{"error": f"Unknown school '{school}'. Choose from: {', '.join(valid_schools)}"}]
        school_id = valid_schools.index(matched)
        where.append("School = :school_id")
        params["school_id"] = school_id

    if name:
        where.append("LOWER(Name) LIKE LOWER('%' || :name || '%')")
        params["name"] = name

    w = ("WHERE " + " AND ".join(where)) if where else ""
    rows = _query(
        f"SELECT Name AS name, [Base Cost] AS base_cost, School AS school_id, Description AS description "
        f"FROM morrowind_enchant_magic_effects {w} "
        f"ORDER BY School, Name",
        params,
    )
    school_names = ('Alteration', 'Conjuration', 'Destruction', 'Illusion', 'Mysticism', 'Restoration')
    for r in rows:
        sid = r.pop("school_id", None)
        try:
            r["school"] = school_names[int(sid)]
        except (TypeError, ValueError, IndexError):
            r["school"] = str(sid)
    return rows


@mcp.tool()
def morrowind_enchant_souls(name: str | None = None) -> list[dict]:
    """Return Morrowind+Tribunal+Bloodmoon creature soul sizes (soul_size = actual soul strength).
    Souls ≥ 400 qualify for Constant Effect enchantments.
    Grizzly Bear appears twice (Bloodmoon): soul_size 50 and 100 — always clarify which.
    Optional partial name filter."""
    if name:
        return _query(
            "SELECT name, soul_size FROM morrowind_enchant_souls "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY soul_size, name",
            {"name": name},
        )
    return _query("SELECT name, soul_size FROM morrowind_enchant_souls ORDER BY soul_size, name")


@mcp.tool()
def morrowind_enchant_soul_gems() -> list[dict]:
    """Return Morrowind soul gem types with weight, value, and capacity.
    Capacity is the maximum soul size the gem can hold. Grand Soul Gems (capacity 600) and
    Azura's Star (capacity 15000 in DB — effectively unlimited; holds any soul) are required for
    Constant Effect enchantments. Azura's Star is reusable; other gems are destroyed on use."""
    return _query(
        "SELECT Name AS name, Weight AS weight, Value AS value, Capacity AS capacity "
        "FROM morrowind_enchant_soul_gems ORDER BY Capacity"
    )


@mcp.tool()
def morrowind_enchant_item(
    name: str | None = None,
    item_type: str | None = None,
    min_enchant_pts: float | None = None,
) -> list[dict]:
    """Search enchantable Morrowind items (weapons, armor, clothing) by name, type, or minimum
    enchantment capacity. Returns item name, category (weapon/armor/clothing), item type (e.g.
    LongBladeOneHand, Shield, Ring), and enchant_pts (the enchantment point capacity).

    item_type supports partial match (e.g. 'Shield', 'Ring', 'LongBlade', 'Helmet').
    min_enchant_pts filters to items with at least that many enchantment points.
    Results ordered by enchant_pts descending."""
    where_w, where_a, where_c = [], [], []
    params: dict = {}

    if name:
        pattern = f"%{name}%"
        where_w.append("LOWER(w.Name) LIKE LOWER(:name)")
        where_a.append("LOWER(a.Name) LIKE LOWER(:name)")
        where_c.append("LOWER(c.Name) LIKE LOWER(:name)")
        params["name"] = pattern

    if item_type:
        tp = f"%{item_type}%"
        where_w.append("LOWER(w.Type) LIKE LOWER(:itype)")
        where_a.append("LOWER(a.Type) LIKE LOWER(:itype)")
        where_c.append("LOWER(c.Type) LIKE LOWER(:itype)")
        params["itype"] = tp

    if min_enchant_pts is not None:
        raw = min_enchant_pts * 10
        where_w.append("CAST(w.Enchantment AS REAL) >= :minraw")
        where_a.append("CAST(a.Enchantment AS REAL) >= :minraw")
        where_c.append("CAST(c.Enchantment AS REAL) >= :minraw")
        params["minraw"] = raw

    def _wc(clauses: list[str]) -> str:
        return ("WHERE " + " AND ".join(clauses)) if clauses else ""

    sql = f"""
        SELECT Name AS name, 'weapon' AS category, Type AS item_type,
               CAST(Enchantment AS REAL)/10 AS enchant_pts
        FROM morrowind_enchant_weapons w {_wc(where_w)}
        UNION ALL
        SELECT Name, 'armor', Type, CAST(Enchantment AS REAL)/10
        FROM morrowind_enchant_armor a {_wc(where_a)}
        UNION ALL
        SELECT Name, 'clothing', Type, CAST(Enchantment AS REAL)/10
        FROM morrowind_enchant_clothing c {_wc(where_c)}
        ORDER BY enchant_pts DESC, name
    """
    return _query(sql, params)


# ─── Oblivion enchanting ────────────────────────────────────────────────────

@mcp.resource("gametools://oblivion/enchanting/rules")
def oblivion_enchanting_rules() -> str:
    """Oblivion enchanting mechanics: sigil stones, altar formulae, charges, soul gems, cursed items."""
    return (_SCRIPT_DIR / 'oblivion_enchanting.md').read_text()


@mcp.tool()
def oblivion_enchant_effects(
    school: str | None = None,
    name: str | None = None,
) -> list[dict]:
    """Return Oblivion enchantment effects with name, effect_id, base_cost, barter_factor,
    school, and description. Optional filters: school
    (Alteration/Conjuration/Destruction/Illusion/Mysticism/Restoration) and/or partial effect
    name (e.g. 'Paralyze', 'Fortify Strength', 'Night'). Searches the human-readable name column.
    base_cost feeds the weapon charge formula and apparel CEEF; barter_factor feeds the gold cost."""
    valid_schools = ('Alteration', 'Conjuration', 'Destruction', 'Illusion', 'Mysticism', 'Restoration')
    where: list[str] = []
    params: dict = {}

    if school:
        matched = next((s for s in valid_schools if s.lower() == school.lower()), None)
        if not matched:
            return [{"error": f"Unknown school '{school}'. Choose from: {', '.join(valid_schools)}"}]
        where.append("school = :school")
        params["school"] = matched

    if name:
        where.append("LOWER(name) LIKE LOWER('%' || :name || '%')")
        params["name"] = name

    w = ("WHERE " + " AND ".join(where)) if where else ""
    return _query(
        f"SELECT name, effect_id, base_cost, barter_factor, school, description "
        f"FROM oblivion_enchant_effects {w} ORDER BY school, name",
        params,
    )


@mcp.tool()
def oblivion_enchant_souls(name: str | None = None) -> list[dict]:
    """Return Oblivion creature soul sizes (soul_size = Power value used in enchanting formulas:
    150/300/800/1200/1600). Black souls (humanoids, Dremora) are at 1600.
    Optional partial name filter."""
    if name:
        return _query(
            "SELECT name, soul_size FROM oblivion_enchant_souls "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY soul_size, name",
            {"name": name},
        )
    return _query("SELECT name, soul_size FROM oblivion_enchant_souls ORDER BY soul_size, name")


_SIGIL_LEVELS = ('descendent', 'subjacent', 'latent', 'ascendent', 'transcendent')

@mcp.tool()
def oblivion_sigil_stone(
    weapon_effect: str | None = None,
    armor_effect: str | None = None,
    level: str | None = None,
) -> list[dict]:
    """Return Oblivion sigil stones with weapon effect, armor effect, and all magnitude/charge
    columns. Optional filters: partial weapon_effect name, partial armor_effect name, and/or
    level (descendent/subjacent/latent/ascendent/transcendent).
    Magnitude columns are NULL for all levels except the stone's own level.
    Weapon columns: {level}_magnitude, {level}_charges.
    Armor columns: {level}_armor_magnitude."""
    if level and level.lower() not in _SIGIL_LEVELS:
        return [{"error": f"Unknown level '{level}'. Choose from: {', '.join(_SIGIL_LEVELS)}"}]

    where: list[str] = []
    params: dict = {}

    if weapon_effect:
        where.append("LOWER(s.weapon_effect) LIKE LOWER('%' || :wfx || '%')")
        params["wfx"] = weapon_effect
    if armor_effect:
        where.append("LOWER(s.armor_effect) LIKE LOWER('%' || :afx || '%')")
        params["afx"] = armor_effect
    if level:
        col = f"wm.{level.lower()}_magnitude"
        where.append(f"{col} IS NOT NULL")

    w = ("WHERE " + " AND ".join(where)) if where else ""
    return _query(
        f"SELECT s.form_id, s.weapon_effect, s.armor_effect, "
        f"wm.descendent_magnitude, wm.descendent_charges, "
        f"wm.subjacent_magnitude, wm.subjacent_charges, "
        f"wm.latent_magnitude, wm.latent_charges, "
        f"wm.ascendent_magnitude, wm.ascendent_charges, "
        f"wm.transcendent_magnitude, wm.transcendent_charges, "
        f"am.descendent_magnitude AS descendent_armor_magnitude, "
        f"am.subjacent_magnitude AS subjacent_armor_magnitude, "
        f"am.latent_magnitude AS latent_armor_magnitude, "
        f"am.ascendent_magnitude AS ascendent_armor_magnitude, "
        f"am.transcendent_magnitude AS transcendent_armor_magnitude "
        f"FROM oblivion_sigil_stone s "
        f"JOIN oblivion_sigil_stone_weapon_magnitudes wm ON s.form_id = wm.form_id "
        f"JOIN oblivion_sigil_stone_armor_magnitudes am ON s.form_id = am.form_id "
        f"{w} ORDER BY s.weapon_effect, s.armor_effect, s.form_id",
        params,
    )


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

@mcp.resource("gametools://skyrim/smithing/rules")
def skyrim_smithing_rules() -> str:
    """Skyrim smithing mechanics: perk tree, quality levels, effective skill, armor cap, smelting rules."""
    return (_SCRIPT_DIR / 'skyrim_smithing.md').read_text()


_ARMOR_FIXED  = frozenset({'piece', 'material_perk', 'armor_rating', 'weight', 'value', 'id'})
_WEAPON_FIXED = frozenset({'piece', 'material_perk', 'damage',       'weight', 'value', 'id'})


def _col_display(col: str) -> str:
    return col.replace('_', ' ').title()


def _materialize(row: dict, fixed_cols: frozenset) -> dict:
    """Separate fixed columns from sparse material columns.
    Returns the fixed fields plus a 'materials' dict of {display_name: quantity}
    containing only non-zero entries."""
    base = {k: v for k, v in row.items() if k in fixed_cols}
    base['materials'] = {
        _col_display(k): v
        for k, v in row.items()
        if k not in fixed_cols and v
    }
    return base


@mcp.tool()
def skyrim_smithing_perks() -> list[dict]:
    """Return the full Skyrim smithing perk tree with skill level requirements, prerequisites,
    and descriptions."""
    return _query(
        "SELECT name, skill_level, prerequisite, description "
        "FROM skyrim_smithing_perks ORDER BY skill_level, name"
    )


@mcp.tool()
def skyrim_smithing_armor(
    name: str | None = None,
    perk: str | None = None,
) -> list[dict]:
    """Return Skyrim craftable armor pieces with required materials.
    Optional partial name filter (e.g. 'Helmet', 'Daedric Armor').
    Optional perk filter — partial match on the material_perk column
    (e.g. 'Elven', 'Steel', 'Daedric').
    Materials are returned as a dict of {Material: quantity}; zero entries are omitted.
    Includes base-game and Creation Club armor (193 total pieces)."""
    where: list[str] = []
    params: dict = {}
    if name:
        where.append("LOWER(piece) LIKE LOWER(:name)")
        params['name'] = f'%{name}%'
    if perk:
        where.append("LOWER(material_perk) LIKE LOWER(:perk)")
        params['perk'] = f'%{perk}%'
    w = ('WHERE ' + ' AND '.join(where)) if where else ''
    rows = _query(
        f"SELECT * FROM skyrim_smithing_armor {w} ORDER BY material_perk, piece",
        params,
    )
    return [_materialize(r, _ARMOR_FIXED) for r in rows]


@mcp.tool()
def skyrim_smithing_weapons(
    name: str | None = None,
    perk: str | None = None,
) -> list[dict]:
    """Return Skyrim craftable weapons and ammunition with required materials.
    Optional partial name filter (e.g. 'Sword', 'Bow', 'Arrow', 'Crossbow').
    Optional perk filter — partial match on the material_perk column
    (e.g. 'Glass', 'Dwarven', 'Steel').
    Materials are returned as a dict of {Material: quantity}; zero entries are omitted.
    Includes base-game weapons, Dawnguard crossbows, and Creation Club weapons and ammo
    (135 weapons + 12 CC ammo pieces)."""
    where: list[str] = []
    params: dict = {}
    if name:
        where.append("LOWER(piece) LIKE LOWER(:name)")
        params['name'] = f'%{name}%'
    if perk:
        where.append("LOWER(material_perk) LIKE LOWER(:perk)")
        params['perk'] = f'%{perk}%'
    w = ('WHERE ' + ' AND '.join(where)) if where else ''
    weapons = _query(
        f"SELECT * FROM skyrim_smithing_weapons {w} ORDER BY material_perk, piece",
        params,
    )
    ammo = _query(
        f"SELECT * FROM skyrim_smithing_ammo {w} ORDER BY material_perk, piece",
        params,
    )
    return [_materialize(r, _WEAPON_FIXED) for r in weapons + ammo]


@mcp.tool()
def skyrim_smithing_improvement() -> list[dict]:
    """Return Skyrim item improvement quality levels with effective-skill thresholds and stat effects.
    skill_without_perk / skill_with_perk are the effective_skill values (base + Fortify Smithing)
    needed to reach each quality.
    'With perk' means having the specific material perk (e.g. Ebony Smithing for ebony items).
    quality_number is the level index (Fine=1 … Legendary=6); above 6 the game still displays
    'Legendary' — always report the actual quality_number as Legendary (N) when N >= 6."""
    rows = _query(
        "SELECT quality, skill_without_perk, skill_with_perk, armor_effect, weapon_effect "
        "FROM skyrim_smithing_improvement ORDER BY skill_without_perk"
    )
    for i, r in enumerate(rows, 1):
        r['quality_number'] = i
    return rows


@mcp.tool()
def skyrim_tempering_materials(smithing_category: str | None = None) -> list[dict]:
    """Return the tempering material for each smithing category — the ingot or material consumed
    when improving an item of that type. Optional partial smithing_category filter
    (e.g. 'Ebony', 'Daedric', 'Steel', 'Amber')."""
    if smithing_category:
        return _query(
            "SELECT smithing_category, crafting_material "
            "FROM skyrim_tempering_materials "
            "WHERE LOWER(smithing_category) LIKE LOWER(:cat) "
            "ORDER BY smithing_category",
            {"cat": f'%{smithing_category}%'},
        )
    return _query(
        "SELECT smithing_category, crafting_material "
        "FROM skyrim_tempering_materials ORDER BY smithing_category"
    )


@mcp.tool()
def skyrim_smelting(
    source: str | None = None,
    ingot: str | None = None,
) -> list[dict]:
    """Return Skyrim smelting recipes (ore or Dwemer scrap → ingot).
    Optional partial Source_Name filter (e.g. 'Iron Ore', 'Dwemer').
    Optional partial Ingot_Name filter (e.g. 'Dwarven', 'Steel').
    The Stalhrim row has NULL Ingot_Name — Stalhrim cannot be smelted; see Note.
    Steel Ingot has two rows (Iron Ore and Corundum Ore are both required — the Note on each row
    cross-references the other); it is the only recipe that requires two different ore types."""
    where: list[str] = []
    params: dict = {}
    if source:
        where.append("LOWER(Source_Name) LIKE LOWER(:src)")
        params['src'] = f'%{source}%'
    if ingot:
        where.append("LOWER(Ingot_Name) LIKE LOWER(:ing)")
        params['ing'] = f'%{ingot}%'
    w = ('WHERE ' + ' AND '.join(where)) if where else ''
    return _query(
        f"SELECT Source_Name, Source_Weight, Source_Value, Source_To_Ingot, "
        f"Ingot_Name, Ingots_Produced, Ingot_Weight, Ingot_Value, Note "
        f"FROM skyrim_smelting {w} ORDER BY Ingot_Name, Source_Name",
        params,
    )


# ─── Skyrim homestead ───────────────────────────────────────────────────────

@mcp.resource("gametools://skyrim/homestead/rules")
def skyrim_homestead_rules() -> str:
    """Skyrim Hearthfire homestead construction: materials hierarchy, crafted components,
    manifest levels, wing restriction, steward costs, Entry Hall ordering rule."""
    return (_SCRIPT_DIR / 'skyrim_homestead.md').read_text()


# Material columns in skyrim_homestead_build (excludes section, location, batch_size)
_BUILD_MAT_COLS = [
    'sawn_log', 'quarried_stone', 'nails', 'clay', 'iron_fittings', 'lock', 'hinge',
    'iron_ingot', 'steel_ingot', 'glass', 'quicksilver_ingot', 'refined_moonstone',
    'filled_grand_soul_gem', 'gold_ingot', 'leather_strips', 'straw', 'goat_horns',
    'vampire_dust', 'deer_hide', 'large_antlers', 'small_antlers', 'goat_hide',
    'horker_tusk', 'mudcrab_chitin', 'slaughterfish_scales', 'wolf_pelt',
    'sabre_cat_pelt', 'sabre_cat_tooth', 'sabre_cat_snow_pelt', 'bear_pelt',
    'amulet_of_akatosh', 'amulet_of_arkay', 'amulet_of_dibella', 'amulet_of_julianos',
    'amulet_of_kynareth', 'amulet_of_mara', 'amulet_of_stendarr', 'amulet_of_talos',
    'amulet_of_zenithar', 'flawless_amethyst', 'flawless_sapphire',
    'corundum_ingot', 'orichalcum_ingot', 'silver_ingot', 'ebony_ingot',
    'refined_malachite', 'dragon_bone', 'dragon_scales',
]

# Ingot column → {ore_name: multiplier} for Level 3 conversion
_INGOT_TO_ORE: dict[str, dict[str, int]] = {
    'iron_ingot':        {'Iron Ore':          1},
    'corundum_ingot':    {'Corundum Ore':       2},
    'steel_ingot':       {'Iron Ore':           1, 'Corundum Ore': 1},
    'quicksilver_ingot': {'Quicksilver Ore':    2},
    'refined_moonstone': {'Moonstone Ore':      2},
    'gold_ingot':        {'Gold Ore':           2},
    'orichalcum_ingot':  {'Orichalcum Ore':     2},
    'silver_ingot':      {'Silver Ore':         2},
    'ebony_ingot':       {'Ebony Ore':          2},
    'refined_malachite': {'Malachite Ore':      2},
}


@mcp.tool()
def skyrim_homestead_locations() -> list[str]:
    """List all distinct location values in the Skyrim homestead build table.
    Use these as prefix arguments in skyrim_homestead_build() and
    skyrim_homestead_manifest(). Top-level locations include Small House, Main Hall,
    West_Wing, North_Wing, East_Wing, Cellar, Exterior, and Entryway."""
    rows = _query("SELECT DISTINCT location FROM skyrim_homestead_build ORDER BY location")
    return [r['location'] for r in rows]


@mcp.tool()
def skyrim_homestead_build(location: str | None = None) -> list[dict]:
    """Return Skyrim homestead build rows with non-zero material quantities.
    Optional location: prefix match — 'Main Hall' (or 'Main_Hall') returns the
    'Main Hall' shell row AND all 'Main_Hall_*' furnishing sub-locations.
    Spaces are normalised to underscores before matching so that SQLite's _
    wildcard captures both space and underscore variants in the data.
    'West_Wing' returns the wing shell and all 'West_Wing_*' furnishing rows.
    Omit for all 410 rows.
    Each result row has section, location, and a materials dict of {column: quantity}
    containing only non-zero entries."""
    if location:
        # Normalise spaces to underscores so the SQLite _ wildcard in the LIKE
        # pattern matches both 'Main Hall' (space) and 'Main_Hall_*' (underscore).
        prefix = location.replace(' ', '_')
        rows = _query(
            "SELECT * FROM skyrim_homestead_build "
            "WHERE location LIKE :loc ORDER BY location, section",
            {"loc": f"{prefix}%"},
        )
    else:
        rows = _query(
            "SELECT * FROM skyrim_homestead_build ORDER BY location, section"
        )
    result = []
    for row in rows:
        mats = {k: row[k] for k in _BUILD_MAT_COLS if row.get(k)}
        result.append({'section': row['section'], 'location': row['location'], 'materials': mats})
    return result


@mcp.tool()
def skyrim_homestead_crafted_components() -> list[dict]:
    """Return Skyrim homestead forge recipes for nails, hinge, iron fittings, and lock.
    Each record: name (matches build table column), batch_size (units per forge action),
    iron_ingot and corundum_ingot (ingots consumed per forge action).
    Use ceil(needed / batch_size) to compute forge actions and ingot cost."""
    return _query(
        "SELECT name, batch_size, iron_ingot, corundum_ingot "
        "FROM skyrim_homestead_crafted_components ORDER BY name"
    )


@mcp.tool()
def skyrim_homestead_steward_cost(room: str | None = None) -> list[dict]:
    """Return gold cost to have the steward furnish each homestead room.
    'room' values match location prefixes in skyrim_homestead_build (e.g.
    'Main Hall', \"West_Wing_Enchanter's_Tower\", 'Cellar'). Note: the steward
    cannot furnish the Cellar — all cellar items must be built manually.
    Optional partial room name filter."""
    if room:
        return _query(
            "SELECT room, gold_cost FROM skyrim_homestead_steward_cost "
            "WHERE LOWER(room) LIKE LOWER(:room) ORDER BY room",
            {"room": f"%{room}%"},
        )
    return _query("SELECT room, gold_cost FROM skyrim_homestead_steward_cost ORDER BY room")


@mcp.tool()
def skyrim_homestead_manifest(
    locations: str | None = None,
    level: int = 1,
) -> dict:
    """Compute a Skyrim Hearthfire build manifest at one of three abstraction levels.

    locations: comma-separated location prefixes to include (e.g.
    'Small House,Main Hall,Cellar' or 'West_Wing,West_Wing_Enchanter\\'s_Tower').
    Each prefix matches that exact location AND all sub-locations (prefix match).
    Omit or pass None to compute a full-manor manifest covering all 410 rows.

    level:
      1 = Component — raw quantities from the build table; crafted components
          (nails / hinge / iron_fittings / lock) are listed as-is.
      2 = Ingot — crafted components resolved to iron / corundum ingots via ceiling
          division over forge batch sizes; batch_info shows waste produced.
      3 = Ore/base — ingots converted to raw ores; leather_strips folded into
          leather (ceil(strips / 4)); non-smelted materials carry forward unchanged.

    Returns level, description, locations_queried, row_count, materials (non-zero
    only), plus batch_info at level 2 and ore_notes at level 3."""
    if level not in (1, 2, 3):
        return {"error": "level must be 1, 2, or 3"}

    # Build WHERE clause for location prefix matching
    location_list = [loc.strip() for loc in (locations or '').split(',') if loc.strip()]

    # Small House is a required prerequisite for the Main Hall. Auto-include it
    # when any Main Hall location is requested but Small House is not.
    auto_included: list[str] = []
    if location_list:
        has_main_hall = any(
            loc.lower().startswith('main hall') or loc.lower().startswith('main_hall')
            for loc in location_list
        )
        has_small_house = any(loc.lower().startswith('small house') for loc in location_list)
        if has_main_hall and not has_small_house:
            location_list = ['Small House'] + location_list
            auto_included.append('Small House (prerequisite for Main Hall)')

    if location_list:
        conds = ' OR '.join(f"location LIKE :loc{i}" for i in range(len(location_list)))
        # Normalise spaces to underscores so the SQLite _ wildcard matches both
        # 'Main Hall' (space in data) and 'Main_Hall_*' (underscore in data).
        q_params: dict = {f'loc{i}': f'{p.replace(" ", "_")}%' for i, p in enumerate(location_list)}
        where = f"WHERE ({conds})"
    else:
        q_params = {}
        where = ""

    col_list = ', '.join(_BUILD_MAT_COLS)
    rows = _query(
        f"SELECT section, location, {col_list} FROM skyrim_homestead_build "
        f"{where} ORDER BY location, section",
        q_params,
    )

    if not rows:
        return {
            "level": level,
            "locations_queried": location_list or ["(all)"],
            "row_count": 0,
            "materials": {},
            "note": "No rows matched — verify location prefix spelling with skyrim_homestead_locations().",
        }

    # Aggregate Level 1 totals
    totals: dict[str, int] = {}
    for row in rows:
        for col in _BUILD_MAT_COLS:
            v = row.get(col) or 0
            if v:
                totals[col] = totals.get(col, 0) + v

    _LEVEL_DESC = {
        1: "Component level — raw build quantities; crafted components listed as-is",
        2: "Ingot level — crafted components expanded to ingots via forge batch recipes",
        3: "Ore/base level — ingots converted to raw ores; leather strips folded into leather",
    }

    result: dict = {
        "level": level,
        "description": _LEVEL_DESC[level],
        "locations_queried": location_list or ["(all)"],
        "row_count": len(rows),
    }
    if auto_included:
        result["auto_included"] = auto_included

    if level == 1:
        result["materials"] = {k: v for k, v in totals.items() if v}
        return result

    # ── Level 2: expand crafted components to ingots ──────────────────────────
    comp_rows = _query(
        "SELECT name, batch_size, iron_ingot, corundum_ingot "
        "FROM skyrim_homestead_crafted_components"
    )
    # Normalize names to match build table column names (e.g. 'iron fittings' → 'iron_fittings')
    recipes = {r['name'].replace(' ', '_'): r for r in comp_rows}
    craftable = ('nails', 'hinge', 'iron_fittings', 'lock')

    batch_info: dict[str, dict] = {}
    extra_iron = 0
    extra_corundum = 0

    for comp in craftable:
        needed = totals.pop(comp, 0)
        if not needed:
            continue
        rec = recipes.get(comp)
        if not rec:
            continue
        bs = rec['batch_size']
        batches = math.ceil(needed / bs)
        produced = batches * bs
        waste = produced - needed
        iron_used = batches * rec['iron_ingot']
        corundum_used = batches * rec['corundum_ingot']
        extra_iron += iron_used
        extra_corundum += corundum_used
        batch_info[comp] = {
            'needed': needed,
            'batches': batches,
            'produced': produced,
            'waste': waste,
            'iron_ingot_consumed': iron_used,
            'corundum_ingot_consumed': corundum_used,
        }

    if extra_iron:
        totals['iron_ingot'] = totals.get('iron_ingot', 0) + extra_iron
    if extra_corundum:
        totals['corundum_ingot'] = totals.get('corundum_ingot', 0) + extra_corundum

    result["materials"] = {k: v for k, v in totals.items() if v}
    if batch_info:
        result["batch_info"] = batch_info
        result["note"] = (
            "Ceiling division applied: forge actions rounded up to whole batches. "
            "'waste' shows excess components produced beyond what is needed."
        )

    if level == 2:
        return result

    # ── Level 3: convert ingots to ores, fold leather strips ─────────────────
    # Capture steel count before removing it (for ore_notes)
    steel_count = totals.get('steel_ingot', 0)

    ore_notes: list[str] = []
    for col, ore_map in _INGOT_TO_ORE.items():
        qty = totals.pop(col, 0)
        if not qty:
            continue
        for ore_name, mult in ore_map.items():
            totals[ore_name] = totals.get(ore_name, 0) + qty * mult

    if steel_count:
        ore_notes.append(
            f"Steel Ingot: each of the {steel_count} steel ingots contributes "
            f"1 Iron Ore and 1 Corundum Ore — both ore totals above include this."
        )

    # Fold leather strips into leather
    strips = totals.pop('leather_strips', 0)
    if strips:
        leather = math.ceil(strips / 4)
        waste_strips = leather * 4 - strips
        totals['leather'] = totals.get('leather', 0) + leather
        ore_notes.append(
            f"Leather strips: {strips} strips → {leather} leather "
            f"(4 strips per leather at the tanning rack"
            + (f"; {waste_strips} extra strip(s) produced" if waste_strips else "")
            + ")"
        )

    result["materials"] = {k: v for k, v in totals.items() if v}
    if ore_notes:
        result["ore_notes"] = ore_notes

    return result


if __name__ == '__main__':
    mcp.run()
