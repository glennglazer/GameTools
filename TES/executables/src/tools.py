"""Standalone tool implementations for TES GameTools.

Mirrors all tools in TES/mcp/tes_mcp_server.py using sqlite3 directly
(no SQLAlchemy dependency).  Set DB_PATH before calling any tool.
"""
import math
import sqlite3
from pathlib import Path
from typing import Any

# Set by main.py / server.py at startup
DB_PATH: Path | None = None


# ─── DB helpers ─────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    if DB_PATH is None:
        raise RuntimeError("DB_PATH not set — call set_db_path() before using tools")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _query(sql: str, params: dict | None = None) -> list[dict]:
    with _conn() as conn:
        cur = conn.execute(sql, params or {})
        return [dict(r) for r in cur.fetchall()]


def _query_list(sql: str, key: str, values: list, extra_params: dict | None = None) -> list[dict]:
    """Execute SQL with one IN clause; :key in the SQL is replaced with
    expanded positional parameters.  extra_params are additional named params."""
    params = dict(extra_params or {})
    placeholders = ', '.join(f':__v{i}' for i in range(len(values)))
    expanded = sql.replace(f':{key}', f'({placeholders})')
    for i, v in enumerate(values):
        params[f'__v{i}'] = v
    return _query(expanded, params)


# ─── utility ────────────────────────────────────────────────────────────────

def list_tables() -> list[str]:
    rows = _query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r['name'] for r in rows]


# ─── Skyrim alchemy ─────────────────────────────────────────────────────────

def skyrim_alchemy_ingredient(name: str) -> dict | None:
    rows = _query(
        "SELECT name, weight, value FROM skyrim_alchemy_ingredients "
        "WHERE LOWER(name) = LOWER(:name)",
        {"name": name},
    )
    if not rows:
        return None
    ing = rows[0]
    effects = _query(
        "SELECT effect FROM skyrim_alchemy_effects "
        "WHERE LOWER(name) = LOWER(:name) ORDER BY rowid",
        {"name": ing["name"]},
    )
    ing["effects"] = [r["effect"] for r in effects]
    return ing


def skyrim_alchemy_search(query: str) -> list[dict]:
    return _query(
        "SELECT name, weight, value FROM skyrim_alchemy_ingredients "
        "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{query}%"},
    )


def skyrim_alchemy_find_by_effect(effect: str) -> list[dict]:
    return _query(
        "SELECT DISTINCT name, base_magnitude, base_cost FROM skyrim_alchemy_effects "
        "WHERE LOWER(effect) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{effect}%"},
    )


def skyrim_alchemy_combos(ingredients: list[str]) -> list[dict]:
    if len(ingredients) < 2:
        return []
    # Build IN clauses for both e1.name and e2.name with the same list
    n = len(ingredients)
    ph1 = ', '.join(f':__v{i}' for i in range(n))
    ph2 = ', '.join(f':__v{i}' for i in range(n))  # same values
    params = {f'__v{i}': v for i, v in enumerate(ingredients)}
    sql = (
        "SELECT e1.name AS ingredient_1, e2.name AS ingredient_2, e1.effect AS shared_effect "
        "FROM skyrim_alchemy_effects e1 "
        "JOIN skyrim_alchemy_effects e2 ON e1.effect = e2.effect AND e1.name < e2.name "
        f"WHERE e1.name IN ({ph1}) AND e2.name IN ({ph2}) "
        "ORDER BY e1.name, e2.name, e1.effect"
    )
    return _query(sql, params)


def skyrim_alchemy_list_effects() -> list[str]:
    rows = _query("SELECT DISTINCT effect FROM skyrim_alchemy_effects ORDER BY effect")
    return [r["effect"] for r in rows]


def skyrim_alchemy_perks() -> list[dict]:
    return _query(
        "SELECT name, skill_level, prerequisite, description "
        "FROM skyrim_alchemy_perks ORDER BY skill_level, name"
    )


# ─── Oblivion alchemy ───────────────────────────────────────────────────────

def oblivion_alchemy_ingredient(name: str) -> dict | None:
    rows = _query(
        "SELECT name, weight, value FROM oblivion_alchemy_ingredients "
        "WHERE LOWER(name) = LOWER(:name)",
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


def oblivion_alchemy_search(query: str) -> list[dict]:
    return _query(
        "SELECT name, weight, value FROM oblivion_alchemy_ingredients "
        "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{query}%"},
    )


def oblivion_alchemy_find_by_effect(effect: str) -> list[str]:
    rows = _query(
        "SELECT DISTINCT name FROM oblivion_alchemy_effects "
        "WHERE effect IS NOT NULL AND LOWER(effect) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{effect}%"},
    )
    return [r["name"] for r in rows]


def oblivion_alchemy_combos(ingredients: list[str]) -> list[dict]:
    if len(ingredients) < 2:
        return []
    n = len(ingredients)
    ph = ', '.join(f':__v{i}' for i in range(n))
    params = {f'__v{i}': v for i, v in enumerate(ingredients)}
    sql = (
        "SELECT e1.name AS ingredient_1, e2.name AS ingredient_2, e1.effect AS shared_effect "
        "FROM oblivion_alchemy_effects e1 "
        "JOIN oblivion_alchemy_effects e2 ON e1.effect = e2.effect AND e1.name < e2.name "
        f"WHERE e1.effect IS NOT NULL AND e1.name IN ({ph}) AND e2.name IN ({ph}) "
        "ORDER BY e1.name, e2.name, e1.effect"
    )
    return _query(sql, params)


def oblivion_alchemy_list_effects() -> list[str]:
    rows = _query(
        "SELECT DISTINCT effect FROM oblivion_alchemy_effects "
        "WHERE effect IS NOT NULL ORDER BY effect"
    )
    return [r["effect"] for r in rows]


def oblivion_alchemy_apparatus(apparatus_type: str | None = None) -> list[dict]:
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

def morrowind_alchemy_ingredient(name: str) -> dict | None:
    rows = _query(
        "SELECT name, weight, value FROM morrowind_alchemy_ingredients "
        "WHERE LOWER(name) = LOWER(:name)",
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


def morrowind_alchemy_search(query: str) -> list[dict]:
    return _query(
        "SELECT name, weight, value FROM morrowind_alchemy_ingredients "
        "WHERE LOWER(name) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{query}%"},
    )


def morrowind_alchemy_find_by_effect(effect: str) -> list[str]:
    rows = _query(
        "SELECT DISTINCT name FROM morrowind_alchemy_effects "
        "WHERE effect IS NOT NULL AND LOWER(effect) LIKE LOWER(:pattern) ORDER BY name",
        {"pattern": f"%{effect}%"},
    )
    return [r["name"] for r in rows]


def morrowind_alchemy_combos(ingredients: list[str]) -> list[dict]:
    if len(ingredients) < 2:
        return []
    n = len(ingredients)
    ph = ', '.join(f':__v{i}' for i in range(n))
    params = {f'__v{i}': v for i, v in enumerate(ingredients)}
    sql = (
        "SELECT e1.name AS ingredient_1, e2.name AS ingredient_2, e1.effect AS shared_effect "
        "FROM morrowind_alchemy_effects e1 "
        "JOIN morrowind_alchemy_effects e2 ON e1.effect = e2.effect AND e1.name < e2.name "
        f"WHERE e1.effect IS NOT NULL AND e1.name IN ({ph}) AND e2.name IN ({ph}) "
        "ORDER BY e1.name, e2.name, e1.effect"
    )
    return _query(sql, params)


def morrowind_alchemy_list_effects() -> list[str]:
    rows = _query(
        "SELECT DISTINCT effect FROM morrowind_alchemy_effects "
        "WHERE effect IS NOT NULL ORDER BY effect"
    )
    return [r["effect"] for r in rows]


def morrowind_alchemy_apparatus(apparatus_type: str | None = None) -> list[dict]:
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

_MW_SCHOOLS = ('Alteration', 'Conjuration', 'Destruction', 'Illusion', 'Mysticism', 'Restoration')


def morrowind_enchant_magic_effects(
    name: str | None = None,
    school: str | None = None,
) -> list[dict]:
    where: list[str] = []
    params: dict = {}

    if school:
        matched = next((s for s in _MW_SCHOOLS if s.lower() == school.lower()), None)
        if not matched:
            return [{"error": f"Unknown school '{school}'. Choose from: {', '.join(_MW_SCHOOLS)}"}]
        school_id = _MW_SCHOOLS.index(matched)
        where.append("School = :school_id")
        params["school_id"] = school_id

    if name:
        where.append("LOWER(Name) LIKE LOWER('%' || :name || '%')")
        params["name"] = name

    w = ("WHERE " + " AND ".join(where)) if where else ""
    rows = _query(
        f"SELECT Name AS name, [Base Cost] AS base_cost, School AS school_id, "
        f"Description AS description "
        f"FROM morrowind_enchant_magic_effects {w} ORDER BY School, Name",
        params,
    )
    for r in rows:
        sid = r.pop("school_id", None)
        try:
            r["school"] = _MW_SCHOOLS[int(sid)]
        except (TypeError, ValueError, IndexError):
            r["school"] = str(sid)
    return rows


def morrowind_enchant_souls(name: str | None = None) -> list[dict]:
    if name:
        return _query(
            "SELECT name, soul_size FROM morrowind_enchant_souls "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY soul_size, name",
            {"name": name},
        )
    return _query("SELECT name, soul_size FROM morrowind_enchant_souls ORDER BY soul_size, name")


def morrowind_enchant_soul_gems() -> list[dict]:
    return _query(
        "SELECT Name AS name, Weight AS weight, Value AS value, Capacity AS capacity "
        "FROM morrowind_enchant_soul_gems ORDER BY Capacity"
    )


def morrowind_enchant_item(
    name: str | None = None,
    item_type: str | None = None,
    min_enchant_pts: float | None = None,
) -> list[dict]:
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

    sql = (
        f"SELECT Name AS name, 'weapon' AS category, Type AS item_type, "
        f"CAST(Enchantment AS REAL)/10 AS enchant_pts "
        f"FROM morrowind_enchant_weapons w {_wc(where_w)} "
        f"UNION ALL "
        f"SELECT Name, 'armor', Type, CAST(Enchantment AS REAL)/10 "
        f"FROM morrowind_enchant_armor a {_wc(where_a)} "
        f"UNION ALL "
        f"SELECT Name, 'clothing', Type, CAST(Enchantment AS REAL)/10 "
        f"FROM morrowind_enchant_clothing c {_wc(where_c)} "
        f"ORDER BY enchant_pts DESC, name"
    )
    return _query(sql, params)


# ─── Oblivion enchanting ────────────────────────────────────────────────────

_OB_SCHOOLS = ('Alteration', 'Conjuration', 'Destruction', 'Illusion', 'Mysticism', 'Restoration')
_SIGIL_LEVELS = ('descendent', 'subjacent', 'latent', 'ascendent', 'transcendent')


def oblivion_enchant_effects(
    school: str | None = None,
    name: str | None = None,
) -> list[dict]:
    where: list[str] = []
    params: dict = {}

    if school:
        matched = next((s for s in _OB_SCHOOLS if s.lower() == school.lower()), None)
        if not matched:
            return [{"error": f"Unknown school '{school}'. Choose from: {', '.join(_OB_SCHOOLS)}"}]
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


def oblivion_enchant_souls(name: str | None = None) -> list[dict]:
    if name:
        return _query(
            "SELECT name, soul_size FROM oblivion_enchant_souls "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY soul_size, name",
            {"name": name},
        )
    return _query("SELECT name, soul_size FROM oblivion_enchant_souls ORDER BY soul_size, name")


def oblivion_sigil_stone(
    weapon_effect: str | None = None,
    armor_effect: str | None = None,
    level: str | None = None,
) -> list[dict]:
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

def skyrim_enchant_perks() -> list[dict]:
    return _query(
        "SELECT name, skill_level, prerequisite, description "
        "FROM skyrim_enchant_perks ORDER BY skill_level, name"
    )


def skyrim_enchant_weapon_effects(name: str | None = None) -> list[dict]:
    if name:
        return _query(
            "SELECT name, school, base_cost FROM skyrim_enchant_weapons "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY name",
            {"name": name},
        )
    return _query("SELECT name, school, base_cost FROM skyrim_enchant_weapons ORDER BY name")


def skyrim_enchant_apparel_effects(
    slot: str | None = None,
    name: str | None = None,
) -> list[dict]:
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


def skyrim_enchant_soul_gems() -> list[dict]:
    return _query(
        "SELECT name, weight, value, capacity, trappable_souls "
        "FROM skyrim_enchant_soulgems ORDER BY capacity, name"
    )


def skyrim_enchant_souls(name: str | None = None) -> list[dict]:
    if name:
        return _query(
            "SELECT name, soul_size FROM skyrim_enchant_souls "
            "WHERE LOWER(name) LIKE LOWER('%' || :name || '%') ORDER BY soul_size, name",
            {"name": name},
        )
    return _query("SELECT name, soul_size FROM skyrim_enchant_souls ORDER BY soul_size, name")


def skyrim_enchant_disenchant(effect: str) -> list[dict]:
    params = {"effect": f"%{effect}%"}
    apparel = _query(
        "SELECT effect, item, note, 'apparel' AS type "
        "FROM skyrim_enchant_disenchant_apparel "
        "WHERE LOWER(effect) LIKE LOWER(:effect) ORDER BY effect, item",
        params,
    )
    weapons = _query(
        "SELECT effect, item, note, 'weapon' AS type "
        "FROM skyrim_enchant_disenchant_weapons "
        "WHERE LOWER(effect) LIKE LOWER(:effect) ORDER BY effect, item",
        params,
    )
    return apparel + weapons


# ─── Skyrim smithing ────────────────────────────────────────────────────────

_ARMOR_FIXED  = frozenset({'piece', 'material_perk', 'armor_rating', 'weight', 'value', 'id'})
_WEAPON_FIXED = frozenset({'piece', 'material_perk', 'damage',       'weight', 'value', 'id'})


def _col_display(col: str) -> str:
    return col.replace('_', ' ').title()


def _materialize(row: dict, fixed_cols: frozenset) -> dict:
    base = {k: v for k, v in row.items() if k in fixed_cols}
    base['materials'] = {
        _col_display(k): v
        for k, v in row.items()
        if k not in fixed_cols and v
    }
    return base


def skyrim_smithing_perks() -> list[dict]:
    return _query(
        "SELECT name, skill_level, prerequisite, description "
        "FROM skyrim_smithing_perks ORDER BY skill_level, name"
    )


def skyrim_smithing_armor(
    name: str | None = None,
    perk: str | None = None,
) -> list[dict]:
    where: list[str] = []
    params: dict = {}
    if name:
        where.append("LOWER(piece) LIKE LOWER(:name)")
        params['name'] = f'%{name}%'
    if perk:
        where.append("LOWER(material_perk) LIKE LOWER(:perk)")
        params['perk'] = f'%{perk}%'
    w = ('WHERE ' + ' AND '.join(where)) if where else ''
    rows = _query(f"SELECT * FROM skyrim_smithing_armor {w} ORDER BY material_perk, piece", params)
    return [_materialize(r, _ARMOR_FIXED) for r in rows]


def skyrim_smithing_weapons(
    name: str | None = None,
    perk: str | None = None,
) -> list[dict]:
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
        f"SELECT * FROM skyrim_smithing_weapons {w} ORDER BY material_perk, piece", params
    )
    ammo = _query(
        f"SELECT * FROM skyrim_smithing_ammo {w} ORDER BY material_perk, piece", params
    )
    return [_materialize(r, _WEAPON_FIXED) for r in weapons + ammo]


def skyrim_smithing_improvement() -> list[dict]:
    rows = _query(
        "SELECT quality, skill_without_perk, skill_with_perk, armor_effect, weapon_effect "
        "FROM skyrim_smithing_improvement ORDER BY skill_without_perk"
    )
    for i, r in enumerate(rows, 1):
        r['quality_number'] = i
    return rows


def skyrim_tempering_materials(smithing_category: str | None = None) -> list[dict]:
    if smithing_category:
        return _query(
            "SELECT smithing_category, crafting_material FROM skyrim_tempering_materials "
            "WHERE LOWER(smithing_category) LIKE LOWER(:cat) ORDER BY smithing_category",
            {"cat": f'%{smithing_category}%'},
        )
    return _query(
        "SELECT smithing_category, crafting_material "
        "FROM skyrim_tempering_materials ORDER BY smithing_category"
    )


def skyrim_smelting(
    source: str | None = None,
    ingot: str | None = None,
) -> list[dict]:
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


def skyrim_homestead_locations() -> list[str]:
    rows = _query("SELECT DISTINCT location FROM skyrim_homestead_build ORDER BY location")
    return [r['location'] for r in rows]


def skyrim_homestead_build(location: str | None = None) -> list[dict]:
    if location:
        prefix = location.replace(' ', '_')
        rows = _query(
            "SELECT * FROM skyrim_homestead_build "
            "WHERE location LIKE :loc ORDER BY location, section",
            {"loc": f"{prefix}%"},
        )
    else:
        rows = _query("SELECT * FROM skyrim_homestead_build ORDER BY location, section")
    result = []
    for row in rows:
        mats = {k: row[k] for k in _BUILD_MAT_COLS if row.get(k)}
        result.append({'section': row['section'], 'location': row['location'], 'materials': mats})
    return result


def skyrim_homestead_crafted_components() -> list[dict]:
    return _query(
        "SELECT name, batch_size, iron_ingot, corundum_ingot "
        "FROM skyrim_homestead_crafted_components ORDER BY name"
    )


def skyrim_homestead_steward_cost(room: str | None = None) -> list[dict]:
    if room:
        return _query(
            "SELECT room, gold_cost FROM skyrim_homestead_steward_cost "
            "WHERE LOWER(room) LIKE LOWER(:room) ORDER BY room",
            {"room": f"%{room}%"},
        )
    return _query("SELECT room, gold_cost FROM skyrim_homestead_steward_cost ORDER BY room")


def skyrim_homestead_manifest(
    locations: str | None = None,
    level: int = 1,
) -> dict:
    if level not in (1, 2, 3):
        return {"error": "level must be 1, 2, or 3"}

    location_list = [loc.strip() for loc in (locations or '').split(',') if loc.strip()]

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
            "note": "No rows matched. Verify location prefix with skyrim_homestead_locations().",
        }

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

    comp_rows = _query(
        "SELECT name, batch_size, iron_ingot, corundum_ingot "
        "FROM skyrim_homestead_crafted_components"
    )
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

    # Level 3: convert ingots to ores
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


# ─── Tool registry ──────────────────────────────────────────────────────────

# Maps tool name → (function, input_schema)
# input_schema follows Anthropic tool-use format.

TOOL_MAP: dict[str, tuple[Any, dict]] = {
    "list_tables": (list_tables, {
        "type": "object", "properties": {}, "required": []
    }),
    # ── Skyrim alchemy
    "skyrim_alchemy_ingredient": (skyrim_alchemy_ingredient, {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Exact ingredient name (case-insensitive)"}},
        "required": ["name"],
    }),
    "skyrim_alchemy_search": (skyrim_alchemy_search, {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Partial name to search"}},
        "required": ["query"],
    }),
    "skyrim_alchemy_find_by_effect": (skyrim_alchemy_find_by_effect, {
        "type": "object",
        "properties": {"effect": {"type": "string", "description": "Partial effect name"}},
        "required": ["effect"],
    }),
    "skyrim_alchemy_combos": (skyrim_alchemy_combos, {
        "type": "object",
        "properties": {"ingredients": {"type": "array", "items": {"type": "string"}, "description": "List of ingredient names"}},
        "required": ["ingredients"],
    }),
    "skyrim_alchemy_list_effects": (skyrim_alchemy_list_effects, {
        "type": "object", "properties": {}, "required": []
    }),
    "skyrim_alchemy_perks": (skyrim_alchemy_perks, {
        "type": "object", "properties": {}, "required": []
    }),
    # ── Oblivion alchemy
    "oblivion_alchemy_ingredient": (oblivion_alchemy_ingredient, {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }),
    "oblivion_alchemy_search": (oblivion_alchemy_search, {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }),
    "oblivion_alchemy_find_by_effect": (oblivion_alchemy_find_by_effect, {
        "type": "object",
        "properties": {"effect": {"type": "string"}},
        "required": ["effect"],
    }),
    "oblivion_alchemy_combos": (oblivion_alchemy_combos, {
        "type": "object",
        "properties": {"ingredients": {"type": "array", "items": {"type": "string"}}},
        "required": ["ingredients"],
    }),
    "oblivion_alchemy_list_effects": (oblivion_alchemy_list_effects, {
        "type": "object", "properties": {}, "required": []
    }),
    "oblivion_alchemy_apparatus": (oblivion_alchemy_apparatus, {
        "type": "object",
        "properties": {"apparatus_type": {"type": "string", "description": "Partial type keyword: Mortar, Retort, Alembic, or Calcinator"}},
        "required": [],
    }),
    # ── Morrowind alchemy
    "morrowind_alchemy_ingredient": (morrowind_alchemy_ingredient, {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }),
    "morrowind_alchemy_search": (morrowind_alchemy_search, {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }),
    "morrowind_alchemy_find_by_effect": (morrowind_alchemy_find_by_effect, {
        "type": "object",
        "properties": {"effect": {"type": "string"}},
        "required": ["effect"],
    }),
    "morrowind_alchemy_combos": (morrowind_alchemy_combos, {
        "type": "object",
        "properties": {"ingredients": {"type": "array", "items": {"type": "string"}}},
        "required": ["ingredients"],
    }),
    "morrowind_alchemy_list_effects": (morrowind_alchemy_list_effects, {
        "type": "object", "properties": {}, "required": []
    }),
    "morrowind_alchemy_apparatus": (morrowind_alchemy_apparatus, {
        "type": "object",
        "properties": {"apparatus_type": {"type": "string"}},
        "required": [],
    }),
    # ── Morrowind enchanting
    "morrowind_enchant_magic_effects": (morrowind_enchant_magic_effects, {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Partial effect name"},
            "school": {"type": "string", "description": "Alteration/Conjuration/Destruction/Illusion/Mysticism/Restoration"},
        },
        "required": [],
    }),
    "morrowind_enchant_souls": (morrowind_enchant_souls, {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Partial creature name"}},
        "required": [],
    }),
    "morrowind_enchant_soul_gems": (morrowind_enchant_soul_gems, {
        "type": "object", "properties": {}, "required": []
    }),
    "morrowind_enchant_item": (morrowind_enchant_item, {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "item_type": {"type": "string", "description": "Partial type: Shield, Ring, LongBlade, Helmet, etc."},
            "min_enchant_pts": {"type": "number", "description": "Minimum enchantment point capacity"},
        },
        "required": [],
    }),
    # ── Oblivion enchanting
    "oblivion_enchant_effects": (oblivion_enchant_effects, {
        "type": "object",
        "properties": {
            "school": {"type": "string"},
            "name": {"type": "string"},
        },
        "required": [],
    }),
    "oblivion_enchant_souls": (oblivion_enchant_souls, {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": [],
    }),
    "oblivion_sigil_stone": (oblivion_sigil_stone, {
        "type": "object",
        "properties": {
            "weapon_effect": {"type": "string"},
            "armor_effect": {"type": "string"},
            "level": {"type": "string", "description": "descendent/subjacent/latent/ascendent/transcendent"},
        },
        "required": [],
    }),
    # ── Skyrim enchanting
    "skyrim_enchant_perks": (skyrim_enchant_perks, {
        "type": "object", "properties": {}, "required": []
    }),
    "skyrim_enchant_weapon_effects": (skyrim_enchant_weapon_effects, {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": [],
    }),
    "skyrim_enchant_apparel_effects": (skyrim_enchant_apparel_effects, {
        "type": "object",
        "properties": {
            "slot": {"type": "string", "description": "head/chest/hands/feet/shield/amulet/ring"},
            "name": {"type": "string"},
        },
        "required": [],
    }),
    "skyrim_enchant_soul_gems": (skyrim_enchant_soul_gems, {
        "type": "object", "properties": {}, "required": []
    }),
    "skyrim_enchant_souls": (skyrim_enchant_souls, {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": [],
    }),
    "skyrim_enchant_disenchant": (skyrim_enchant_disenchant, {
        "type": "object",
        "properties": {"effect": {"type": "string", "description": "Partial enchantment effect name"}},
        "required": ["effect"],
    }),
    # ── Skyrim smithing
    "skyrim_smithing_perks": (skyrim_smithing_perks, {
        "type": "object", "properties": {}, "required": []
    }),
    "skyrim_smithing_armor": (skyrim_smithing_armor, {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "perk": {"type": "string", "description": "Material perk partial match: Elven, Steel, Daedric, etc."},
        },
        "required": [],
    }),
    "skyrim_smithing_weapons": (skyrim_smithing_weapons, {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "perk": {"type": "string"},
        },
        "required": [],
    }),
    "skyrim_smithing_improvement": (skyrim_smithing_improvement, {
        "type": "object", "properties": {}, "required": []
    }),
    "skyrim_tempering_materials": (skyrim_tempering_materials, {
        "type": "object",
        "properties": {"smithing_category": {"type": "string"}},
        "required": [],
    }),
    "skyrim_smelting": (skyrim_smelting, {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Partial source material name"},
            "ingot": {"type": "string", "description": "Partial ingot name"},
        },
        "required": [],
    }),
    # ── Skyrim homestead
    "skyrim_homestead_locations": (skyrim_homestead_locations, {
        "type": "object", "properties": {}, "required": []
    }),
    "skyrim_homestead_build": (skyrim_homestead_build, {
        "type": "object",
        "properties": {"location": {"type": "string", "description": "Location prefix (e.g. 'Main Hall', 'West_Wing')"}},
        "required": [],
    }),
    "skyrim_homestead_crafted_components": (skyrim_homestead_crafted_components, {
        "type": "object", "properties": {}, "required": []
    }),
    "skyrim_homestead_steward_cost": (skyrim_homestead_steward_cost, {
        "type": "object",
        "properties": {"room": {"type": "string", "description": "Partial room name"}},
        "required": [],
    }),
    "skyrim_homestead_manifest": (skyrim_homestead_manifest, {
        "type": "object",
        "properties": {
            "locations": {
                "type": "string",
                "description": "Comma-separated location prefixes, or omit for full manor",
            },
            "level": {
                "type": "integer",
                "description": "1=component, 2=ingot (crafted components expanded), 3=ore/base",
                "enum": [1, 2, 3],
            },
        },
        "required": [],
    }),
}

# Flat list of tool definitions for Anthropic API
TOOLS: list[dict] = []
_TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_tables": "List all tables in the TES GameTools database.",
    "skyrim_alchemy_ingredient": "Return weight, value, and effects for a named Skyrim alchemy ingredient.",
    "skyrim_alchemy_search": "Search Skyrim alchemy ingredients by partial name.",
    "skyrim_alchemy_find_by_effect": "Return all Skyrim ingredients carrying a given effect.",
    "skyrim_alchemy_combos": "Given Skyrim ingredient names, return all pairs that share an effect.",
    "skyrim_alchemy_list_effects": "Return all 60 distinct Skyrim alchemy effects.",
    "skyrim_alchemy_perks": "Return the Skyrim alchemy perk tree.",
    "oblivion_alchemy_ingredient": "Return weight, value, and effects for a named Oblivion alchemy ingredient.",
    "oblivion_alchemy_search": "Search Oblivion alchemy ingredients by partial name.",
    "oblivion_alchemy_find_by_effect": "Return all Oblivion ingredients carrying a given effect.",
    "oblivion_alchemy_combos": "Given Oblivion ingredient names, return all pairs that share an effect.",
    "oblivion_alchemy_list_effects": "Return all distinct Oblivion alchemy effects.",
    "oblivion_alchemy_apparatus": "Return Oblivion alchemy apparatus with grade and strength.",
    "morrowind_alchemy_ingredient": "Return weight, value, and effects for a named Morrowind alchemy ingredient (hidden effects included).",
    "morrowind_alchemy_search": "Search Morrowind alchemy ingredients by partial name.",
    "morrowind_alchemy_find_by_effect": "Return all Morrowind ingredients carrying a given effect (hidden included).",
    "morrowind_alchemy_combos": "Given Morrowind ingredient names, return all pairs that share an effect.",
    "morrowind_alchemy_list_effects": "Return all distinct Morrowind alchemy effects.",
    "morrowind_alchemy_apparatus": "Return Morrowind alchemy apparatus with quality values.",
    "morrowind_enchant_magic_effects": "Return Morrowind magic effects with base_cost and school. Optional name/school filter.",
    "morrowind_enchant_souls": "Return Morrowind creature soul sizes. Optional partial name filter.",
    "morrowind_enchant_soul_gems": "Return Morrowind soul gem types with weight, value, and capacity.",
    "morrowind_enchant_item": "Search enchantable Morrowind items by name, type, or minimum enchantment capacity.",
    "oblivion_enchant_effects": "Return Oblivion enchantment effects with base_cost and barter_factor.",
    "oblivion_enchant_souls": "Return Oblivion creature soul sizes (150/300/800/1200/1600).",
    "oblivion_sigil_stone": "Return Oblivion sigil stones with weapon/armor effects and magnitudes.",
    "skyrim_enchant_perks": "Return the Skyrim enchanting perk tree.",
    "skyrim_enchant_weapon_effects": "Return Skyrim weapon enchantment effects with school and base_cost.",
    "skyrim_enchant_apparel_effects": "Return Skyrim apparel enchantments with equip-slot flags and base_cost.",
    "skyrim_enchant_soul_gems": "Return Skyrim soul gem types with capacity and trappable souls.",
    "skyrim_enchant_souls": "Return Skyrim creature soul sizes. Souls of 3000 are black souls.",
    "skyrim_enchant_disenchant": "Return items to disenchant to learn a given enchantment effect.",
    "skyrim_smithing_perks": "Return the Skyrim smithing perk tree.",
    "skyrim_smithing_armor": "Return Skyrim craftable armor pieces with material requirements.",
    "skyrim_smithing_weapons": "Return Skyrim craftable weapons and ammunition with material requirements.",
    "skyrim_smithing_improvement": "Return Skyrim quality levels with effective-skill thresholds.",
    "skyrim_tempering_materials": "Return the tempering material for each smithing category.",
    "skyrim_smelting": "Return Skyrim smelting recipes (ore or Dwemer scrap to ingot).",
    "skyrim_homestead_locations": "List all distinct location values in the Skyrim homestead build table.",
    "skyrim_homestead_build": "Return Skyrim homestead build rows with non-zero material quantities.",
    "skyrim_homestead_crafted_components": "Return Skyrim homestead forge recipes (nails, hinge, iron fittings, lock).",
    "skyrim_homestead_steward_cost": "Return gold cost to have the steward furnish each homestead room.",
    "skyrim_homestead_manifest": "Compute a Skyrim Hearthfire build manifest at component, ingot, or ore level.",
}

for _name, (_fn, _schema) in TOOL_MAP.items():
    TOOLS.append({
        "name": _name,
        "description": _TOOL_DESCRIPTIONS.get(_name, _name.replace("_", " ")),
        "input_schema": _schema,
    })


def call_tool(name: str, arguments: dict) -> Any:
    """Dispatch a tool call by name with the given arguments."""
    entry = TOOL_MAP.get(name)
    if not entry:
        return {"error": f"Unknown tool: {name}"}
    fn, _ = entry
    try:
        return fn(**arguments)
    except Exception as exc:
        return {"error": str(exc)}
