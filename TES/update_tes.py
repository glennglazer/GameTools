#!/usr/bin/python3
"""
TES data pipeline driver.

Runs the full update pipeline for all implemented TES game/system combinations:
  - Morrowind alchemy, Oblivion alchemy, Skyrim alchemy (scrape → JSON → SQL)
  - Morrowind enchanting (CSV → JSON → SQL; no web scrape, CSVs are manually maintained)

Skipped without error:
  - Oblivion enchanting: not yet automated
  - Skyrim enchanting: not applicable (simplified system)

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
log = logging.getLogger('update_tes')


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


def has_diff_files(json_dir: Path) -> bool:
    """Return True if upsert/delete diff files are waiting to be applied."""
    return (
        any(json_dir.glob('*.upsert.json')) or
        any(json_dir.glob('*.delete.json'))
    )


def update_alchemy(game: str) -> None:
    """Scrape → JSON → SQL for one game's alchemy system."""
    g = game.lower()
    game_dir  = _SCRIPT_DIR / game
    parse_dir = game_dir / 'alchemy' / 'ingredients_parse'
    json_dir  = game_dir / 'alchemy' / 'ingredients_json'
    sql_dir   = game_dir / 'alchemy' / 'ingredients_sql'

    run_step(
        f'{game} alchemy scrape',
        [parse_dir / f'{g}_scrape_wiki.py', '--out-dir', parse_dir],
    )
    run_step(
        f'{game} alchemy JSON',
        [json_dir / f'{g}_parse_wiki_to_json.py'],
    )

    if not has_diff_files(json_dir):
        log.info('[%s alchemy] no changes — database update skipped', game)
        return

    run_step(
        f'{game} alchemy ingredients SQL',
        [sql_dir / f'create_or_update_{g}_alchemy_ingredients.py'],
    )
    run_step(
        f'{game} alchemy effects SQL',
        [sql_dir / f'create_or_update_{g}_alchemy_effects.py'],
    )


def update_morrowind_enchanting() -> None:
    """CSV → JSON → SQL for Morrowind enchanting (no web scrape step)."""
    game_dir = _SCRIPT_DIR / 'Morrowind'
    json_dir = game_dir / 'enchanting' / 'enchant_json'
    sql_dir  = game_dir / 'enchanting' / 'enchant_sql'

    run_step(
        'Morrowind enchanting JSON',
        [json_dir / 'morrowind_parse_enchant_csv_to_json.py'],
    )

    if not has_diff_files(json_dir):
        log.info('[Morrowind enchanting] no changes — database update skipped')
        return

    run_step(
        'Morrowind enchanting SQL',
        [sql_dir / 'create_or_update_morrowind_enchant_tables.py'],
    )


if __name__ == '__main__':
    log.info('=== TES data pipeline starting ===')

    for game in ['Morrowind', 'Oblivion', 'Skyrim']:
        log.info('--- %s alchemy ---', game)
        update_alchemy(game)

    log.info('--- Morrowind enchanting ---')
    update_morrowind_enchanting()

    log.info('--- Oblivion enchanting: skipped (not yet automated) ---')
    log.info('--- Skyrim enchanting: skipped (not applicable) ---')

    log.info('=== TES data pipeline complete ===')
