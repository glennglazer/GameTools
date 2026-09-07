#!/usr/bin/python3
"""
DA data pipeline driver.

Runs the full update pipeline for all implemented Dragon Age game/system combinations:
  - Origins herbalism (scrape → JSON → SQL)
  - Origins poisons & grenades (scrape → JSON → SQL)

Halts immediately on any subprocess failure.
"""

import logging
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


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    log.info('=== DA pipeline starting ===')

    # Origins
    update_origins_herbalism()
    update_origins_poisons_grenades()

    log.info('=== DA pipeline complete ===')


if __name__ == '__main__':
    main()
