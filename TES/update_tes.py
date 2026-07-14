#!/usr/bin/python3
"""
TES data pipeline driver.

Runs the full update pipeline for all implemented TES game/system combinations:
  - Morrowind alchemy, Oblivion alchemy, Skyrim alchemy (scrape → JSON → SQL)
  - Morrowind enchanting (CSV → JSON → SQL; no web scrape, CSVs are manually maintained)
  - Oblivion enchanting (CSV → SQL directly; static 2006 game data, no JSON intermediate)
  - Skyrim enchanting (scrape → JSON → SQL for perks, soul gems, creature souls,
                       enchantment effects, apparel enchantments)

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


def update_oblivion_enchanting() -> None:
    """CSV → SQL for Oblivion enchanting (static data; no JSON intermediate step)."""
    game_dir = _SCRIPT_DIR / 'Oblivion'
    sql_dir  = game_dir / 'enchanting' / 'enchant_sql'

    run_step(
        'Oblivion enchanting SQL',
        [sql_dir / 'create_or_update_oblivion_enchant_tables.py'],
    )


def update_skyrim_smithing() -> None:
    """Scrape → JSON → SQL for all Skyrim smithing tables."""
    smt_dir = _SCRIPT_DIR / 'Skyrim' / 'smithing'

    run_step('Skyrim smithing scrape',
             [smt_dir / 'smithing_parse' / 'skyrim_scrape_smithing.py',
              '--out-dir', smt_dir / 'smithing_parse'])
    run_step('Skyrim smithing armor scrape',
             [smt_dir / 'armor_parse' / 'skyrim_scrape_smithing_armor.py',
              '--out-dir', smt_dir / 'armor_parse'])
    run_step('Skyrim smithing weapons scrape',
             [smt_dir / 'weapons_parse' / 'skyrim_scrape_smithing_weapons.py',
              '--out-dir', smt_dir / 'weapons_parse'])

    for label, json_dir_name, script_name in [
        ('Skyrim smithing perks JSON',
         'perks_json', 'skyrim_parse_smithing_perks_to_json.py'),
        ('Skyrim smithing armor JSON',
         'armor_json', 'skyrim_parse_smithing_armor_to_json.py'),
        ('Skyrim smithing weapons JSON',
         'weapons_json', 'skyrim_parse_smithing_weapons_to_json.py'),
        ('Skyrim smithing improvement JSON',
         'improvement_json', 'skyrim_parse_smithing_improvement_to_json.py'),
        ('Skyrim smithing materials JSON',
         'materials_json', 'skyrim_parse_smithing_materials_to_json.py'),
    ]:
        run_step(label, [smt_dir / json_dir_name / script_name])

    sql_pairs = [
        ('Skyrim smithing perks SQL',
         smt_dir / 'perks_json',
         smt_dir / 'perks_sql' / 'create_or_update_skyrim_smithing_perks.py'),
        ('Skyrim smithing armor SQL',
         smt_dir / 'armor_json',
         smt_dir / 'armor_sql' / 'create_or_update_skyrim_smithing_armor.py'),
        ('Skyrim smithing weapons SQL',
         smt_dir / 'weapons_json',
         smt_dir / 'weapons_sql' / 'create_or_update_skyrim_smithing_weapons.py'),
        ('Skyrim smithing improvement SQL',
         smt_dir / 'improvement_json',
         smt_dir / 'improvement_sql' / 'create_or_update_skyrim_smithing_improvement.py'),
        ('Skyrim smithing materials SQL',
         smt_dir / 'materials_json',
         smt_dir / 'materials_sql' / 'create_or_update_skyrim_smithing_materials.py'),
    ]
    for label, json_dir, sql_script in sql_pairs:
        if not has_diff_files(json_dir):
            log.info('[%s] no changes — database update skipped', label)
            continue
        run_step(label, [sql_script])


def update_skyrim_enchanting() -> None:
    """Scrape → JSON → SQL for all Skyrim enchanting tables."""
    enc_dir = _SCRIPT_DIR / 'Skyrim' / 'enchanting'

    run_step('Skyrim enchanting souls scrape',
             [enc_dir / 'souls_parse' / 'skyrim_scrape_souls.py',
              '--out-dir', enc_dir / 'souls_parse'])
    run_step('Skyrim enchanting scrape',
             [enc_dir / 'enchant_parse' / 'skyrim_scrape_enchanting.py',
              '--out-dir', enc_dir / 'enchant_parse'])

    for label, json_dir_name, script_name in [
        ('Skyrim gem types JSON',
         'gem_types_json', 'skyrim_parse_gem_types_to_json.py'),
        ('Skyrim creature souls JSON',
         'creature_souls_json', 'skyrim_parse_creature_souls_to_json.py'),
        ('Skyrim enchant perks JSON',
         'perks_json', 'skyrim_parse_enchant_perks_to_json.py'),
        ('Skyrim enchant effects JSON',
         'enchant_effects_json', 'skyrim_parse_enchant_effects_to_json.py'),
        ('Skyrim enchant apparel JSON',
         'enchant_apparel_json', 'skyrim_parse_enchant_apparel_to_json.py'),
    ]:
        run_step(label, [enc_dir / json_dir_name / script_name])

    sql_pairs = [
        ('Skyrim gem types SQL',
         enc_dir / 'gem_types_json',
         enc_dir / 'gem_types_sql' / 'create_or_update_skyrim_enchant_soulgems.py'),
        ('Skyrim creature souls SQL',
         enc_dir / 'creature_souls_json',
         enc_dir / 'creature_souls_sql' / 'create_or_update_skyrim_enchant_souls.py'),
        ('Skyrim enchant perks SQL',
         enc_dir / 'perks_json',
         enc_dir / 'perks_sql' / 'create_or_update_skyrim_enchant_perks.py'),
        ('Skyrim enchant effects SQL',
         enc_dir / 'enchant_effects_json',
         enc_dir / 'enchant_effects_sql' / 'create_or_update_skyrim_enchant_effects.py'),
        ('Skyrim enchant apparel SQL',
         enc_dir / 'enchant_apparel_json',
         enc_dir / 'enchant_apparel_sql' / 'create_or_update_skyrim_enchant_apparel.py'),
    ]
    for label, json_dir, sql_script in sql_pairs:
        if not has_diff_files(json_dir):
            log.info('[%s] no changes — database update skipped', label)
            continue
        run_step(label, [sql_script])


def update_skyrim_alchemy_perks() -> None:
    """Scrape → JSON → SQL for Skyrim alchemy perks."""
    game_dir  = _SCRIPT_DIR / 'Skyrim'
    parse_dir = game_dir / 'alchemy' / 'perks_parse'
    json_dir  = game_dir / 'alchemy' / 'perks_json'
    sql_dir   = game_dir / 'alchemy' / 'perks_sql'

    run_step(
        'Skyrim alchemy perks scrape',
        [parse_dir / 'skyrim_scrape_alchemy_perks.py', '--out-dir', parse_dir],
    )
    run_step(
        'Skyrim alchemy perks JSON',
        [json_dir / 'skyrim_parse_perks_to_json.py'],
    )

    if not has_diff_files(json_dir):
        log.info('[Skyrim alchemy perks] no changes — database update skipped')
        return

    run_step(
        'Skyrim alchemy perks SQL',
        [sql_dir / 'create_or_update_skyrim_alchemy_perks.py'],
    )


if __name__ == '__main__':
    log.info('=== TES data pipeline starting ===')

    for game in ['Morrowind', 'Oblivion', 'Skyrim']:
        log.info('--- %s alchemy ---', game)
        update_alchemy(game)

    log.info('--- Skyrim alchemy perks ---')
    update_skyrim_alchemy_perks()

    log.info('--- Morrowind enchanting ---')
    update_morrowind_enchanting()

    log.info('--- Oblivion enchanting ---')
    update_oblivion_enchanting()

    log.info('--- Skyrim enchanting ---')
    update_skyrim_enchanting()

    log.info('--- Skyrim smithing ---')
    update_skyrim_smithing()

    log.info('=== TES data pipeline complete ===')
