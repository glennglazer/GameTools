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


# ─── Skyrim homestead ───────────────────────────────────────────────────────


if __name__ == '__main__':
    mcp.run()
