#!/usr/bin/python3
"""
DA data pipeline driver.

Runs the full update pipeline for all implemented Dragon Age game/system combinations:
  - Origins herbalism (scrape → JSON → SQL), chained into Awakening herbalism
  - Origins poisons & grenades (scrape → JSON → SQL)
  - Origins trap-making (scrape → JSON → SQL)
  - Awakening herbalism (bootstrap DAO:A DB → sync Origins data → scrape → JSON → SQL)

Halts immediately on any subprocess failure.
"""

import logging
import shutil
import sys
import subprocess
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('update_da')

_DB = _SCRIPT_DIR / 'database' / 'gametools.sqlite3'


def run_step(label: str, cmd: list) -> None:
    """Run one pipeline step; relay its output; halt the process on failure."""
    log.info('[%s] starting', label)
    result = subprocess.run(
        [sys.executable] + [str(c) for c in cmd],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        log.info('  %s', line)
    for line in result.stderr.splitlines():
        log.info('  %s', line)
    if result.returncode != 0:
        log.error('[%s] failed with exit code %d — aborting', label, result.returncode)
        sys.exit(1)
    log.info('[%s] done', label)


# ─── Origins ──────────────────────────────────────────────────────────────────

def update_origins_herbalism() -> None:
    """Scrape → JSON → SQL for DAO Herbalism."""
    herbalism_dir = _SCRIPT_DIR / 'Origins' / 'herbalism'
    parse_dir = herbalism_dir / 'herbalism_parse'
    json_dir  = herbalism_dir / 'herbalism_json'
    sql_dir   = herbalism_dir / 'herbalism_sql'

    raw_json      = parse_dir / 'herbalism_raw.json'
    recipes_json  = json_dir  / 'origins_herbalism_recipes.json'
    ing_rec_json  = json_dir  / 'origins_herbalism_ingredient_recipes.json'
    tiers_json    = json_dir  / 'origins_herbalism_tiers.json'
    supply_json   = json_dir  / 'origins_herbalism_unlimited_supply.json'
    effects_json  = json_dir  / 'origins_herbalism_potion_effects.json'

    # 1. Scrape
    run_step(
        'Origins herbalism scrape',
        [parse_dir / 'origins_scrape_herbalism.py', raw_json],
    )

    # 2. Parse JSON
    run_step(
        'Origins herbalism JSON parse',
        [
            json_dir / 'origins_parse_herbalism.py',
            raw_json, recipes_json, ing_rec_json, tiers_json, supply_json, effects_json,
        ],
    )

    # 3. SQL load
    run_step(
        'Origins herbalism SQL load',
        [
            sql_dir / 'create_or_update_origins_herbalism.py',
            recipes_json, ing_rec_json, tiers_json, supply_json, effects_json, _DB,
        ],
    )


def update_origins_poisons_grenades() -> None:
    """Scrape → JSON → SQL for DAO Poisons & Grenades."""
    pg_dir    = _SCRIPT_DIR / 'Origins' / 'poisons_grenades'
    parse_dir = pg_dir / 'poisons_grenades_parse'
    json_dir  = pg_dir / 'poisons_grenades_json'
    sql_dir   = pg_dir / 'poisons_grenades_sql'

    raw_json      = parse_dir / 'poisons_grenades_raw.json'
    recipes_json  = json_dir  / 'origins_poisons_grenades_recipes.json'
    ing_rec_json  = json_dir  / 'origins_poisons_grenades_ingredient_recipes.json'
    tiers_json    = json_dir  / 'origins_poisons_grenades_tiers.json'
    supply_json   = json_dir  / 'origins_poisons_grenades_unlimited_supply.json'
    effects_json  = json_dir  / 'origins_poisons_grenades_effects.json'

    # 1. Scrape
    run_step(
        'Origins poisons/grenades scrape',
        [parse_dir / 'origins_scrape_poisons_grenades.py', raw_json],
    )

    # 2. Parse JSON
    run_step(
        'Origins poisons/grenades JSON parse',
        [
            json_dir / 'origins_parse_poisons_grenades.py',
            raw_json, recipes_json, ing_rec_json, tiers_json, supply_json, effects_json,
        ],
    )

    # 3. SQL load
    run_step(
        'Origins poisons/grenades SQL load',
        [
            sql_dir / 'create_or_update_origins_poisons_grenades.py',
            recipes_json, ing_rec_json, tiers_json, supply_json, effects_json, _DB,
        ],
    )


def update_origins_trap_making() -> None:
    """Scrape → JSON → SQL for DAO Trap-Making."""
    tm_dir    = _SCRIPT_DIR / 'Origins' / 'trap_making'
    parse_dir = tm_dir / 'trap_making_parse'
    json_dir  = tm_dir / 'trap_making_json'
    sql_dir   = tm_dir / 'trap_making_sql'

    raw_json      = parse_dir / 'trap_making_raw.json'
    recipes_json  = json_dir  / 'origins_trap_making_recipes.json'
    ing_rec_json  = json_dir  / 'origins_trap_making_ingredient_recipes.json'
    tiers_json    = json_dir  / 'origins_trap_making_tiers.json'
    supply_json   = json_dir  / 'origins_trap_making_unlimited_supply.json'
    effects_json  = json_dir  / 'origins_trap_making_effects.json'

    # 1. Scrape
    run_step(
        'Origins trap-making scrape',
        [parse_dir / 'origins_scrape_trap_making.py', raw_json],
    )

    # 2. Parse JSON
    run_step(
        'Origins trap-making JSON parse',
        [
            json_dir / 'origins_parse_trap_making.py',
            raw_json, recipes_json, ing_rec_json, tiers_json, supply_json, effects_json,
        ],
    )

    # 3. SQL load
    run_step(
        'Origins trap-making SQL load',
        [
            sql_dir / 'create_or_update_origins_trap_making.py',
            recipes_json, ing_rec_json, tiers_json, supply_json, effects_json, _DB,
        ],
    )


# ─── Awakening ────────────────────────────────────────────────────────────────

def update_awakening_herbalism() -> None:
    """Chain: bootstrap DAO:A DB → sync Origins herbalism → run Awakening herbalism pipeline.

    Step 0: If the DAO:A database does not yet exist, copy the DAO DB to DA/Awakening/database/.
    Step 1: Run the full DAO herbalism pipeline (scrape → JSON → SQL against the DAO DB).
    Step 2: Re-run the DAO herbalism SQL loader against the DAO:A DB so any Origins changes
            are reflected there (the loader is idempotent via the upsert pattern).
    Step 3: Scrape, parse, and load Awakening-exclusive herbalism data into the DAO:A DB.
    """
    dao_db  = _SCRIPT_DIR / 'database' / 'gametools.sqlite3'
    daa_dir = _SCRIPT_DIR / 'Awakening'
    daa_db  = daa_dir / 'database' / 'gametools.sqlite3'

    # Step 0 ── bootstrap DAO:A DB
    if not daa_db.exists():
        daa_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(dao_db), str(daa_db))
        log.info('Bootstrapped DAO:A DB from %s → %s', dao_db, daa_db)

    # Step 1 ── run the full DAO herbalism pipeline (updates DAO DB)
    update_origins_herbalism()

    # Step 2 ── sync Origins herbalism into the DAO:A DB
    origins_herb_dir = _SCRIPT_DIR / 'Origins' / 'herbalism'
    origins_herb_sql = origins_herb_dir / 'herbalism_sql' / 'create_or_update_origins_herbalism.py'
    origins_herb_json = origins_herb_dir / 'herbalism_json'
    run_step('Origins herbalism SQL → DAO:A DB', [
        origins_herb_sql,
        origins_herb_json / 'origins_herbalism_recipes.json',
        origins_herb_json / 'origins_herbalism_ingredient_recipes.json',
        origins_herb_json / 'origins_herbalism_tiers.json',
        origins_herb_json / 'origins_herbalism_unlimited_supply.json',
        origins_herb_json / 'origins_herbalism_potion_effects.json',
        daa_db,
    ])

    # Step 3 ── Awakening-exclusive herbalism pipeline
    aw_herb_dir = daa_dir / 'herbalism'
    parse_dir   = aw_herb_dir / 'herbalism_parse'
    json_dir    = aw_herb_dir / 'herbalism_json'
    sql_dir     = aw_herb_dir / 'herbalism_sql'

    raw_json      = parse_dir / 'herbalism_raw.json'
    recipes_json  = json_dir  / 'awakening_herbalism_recipes.json'
    ing_rec_json  = json_dir  / 'awakening_herbalism_ingredient_recipes.json'
    tiers_json    = json_dir  / 'awakening_herbalism_tiers.json'
    supply_json   = json_dir  / 'awakening_herbalism_unlimited_supply.json'
    effects_json  = json_dir  / 'awakening_herbalism_potion_effects.json'

    run_step('Awakening herbalism scrape', [
        parse_dir / 'awakening_scrape_herbalism.py', raw_json,
    ])
    run_step('Awakening herbalism JSON parse', [
        json_dir / 'awakening_parse_herbalism.py',
        raw_json, recipes_json, ing_rec_json, tiers_json, supply_json, effects_json,
    ])
    run_step('Awakening herbalism SQL load', [
        sql_dir / 'create_or_update_awakening_herbalism.py',
        recipes_json, ing_rec_json, tiers_json, supply_json, effects_json, daa_db,
    ])


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    log.info('=== DA pipeline starting ===')

    # Origins-only systems (no Awakening equivalent yet)
    update_origins_poisons_grenades()
    update_origins_trap_making()

    # Awakening herbalism (chains DAO herbalism internally as step 1)
    update_awakening_herbalism()

    log.info('=== DA pipeline complete ===')


if __name__ == '__main__':
    main()
