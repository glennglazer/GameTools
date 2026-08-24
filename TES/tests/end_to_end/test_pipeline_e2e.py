#!/usr/bin/env python3
"""
TES end-to-end pipeline test.

Creates a blank database, runs all SQL-loading pipeline steps against it using
checked-in JSON/CSV source files, then compares the result against the production
database table-by-table.

The scrape and JSON-parse stages (which require network access) are NOT run.
Only the SQL-loading stage is tested. The existing JSON/CSV files in the repo
are the source of truth for the load.

Fail-fast: any non-zero exit from a pipeline step stops the test immediately
and prints the step label, exit code, and captured stdout/stderr so the problem
is clear without scrolling.

Usage (inside the dev Docker container, from the repo root):
    python TES/tests/end_to_end/test_pipeline_e2e.py [morrowind|oblivion|skyrim|all]

Exit code 0 = all steps succeeded and all tables match production.
Exit code 1 = failure (step error or data mismatch).
"""

import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
TES_ROOT  = REPO_ROOT / 'TES'
PROD_DB   = TES_ROOT / 'database' / 'gametools.sqlite3'

MW = TES_ROOT / 'Morrowind'
OB = TES_ROOT / 'Oblivion'
SK = TES_ROOT / 'Skyrim'
CC = SK / 'creation_club'

_MAX_DIFF_SAMPLE = 5   # rows to show per table when data differs


# ─── Step descriptor ─────────────────────────────────────────────────────────

@dataclass
class Step:
    label: str
    game: str                              # 'morrowind' | 'oblivion' | 'skyrim'
    script: Path                           # absolute path to SQL loader
    mode: str                              # see mode constants below
    source: Optional[Path] = None          # single source file (diff / direct)
    source_dir: Optional[Path] = None      # source directory (diff_dir mode)
    dir_prefixes: List[str] = field(default_factory=list)     # diff_dir prefix list
    named_sources: Dict[str, Path] = field(default_factory=dict)  # flag→path (named mode)

# Mode constants and what they mean:
#
#   diff      Copy source JSON to a per-step temp dir, synthesize
#             <stem>.upsert.json (= all rows) and <stem>.delete.json (= {}),
#             then run: script <tmp/source.json> <test_db>
#
#   direct    Pass source file directly (CSV, full-replace JSON, or UPDATE-style):
#             script <source> <test_db>
#
#   diff_dir  Copy each <prefix>.json from source_dir to a temp dir, synthesize
#             per-prefix diff files, then run: script <tmp_dir> <test_db>
#             (Morrowind enchanting tables only)
#
#   named     Run: script [--flag path ...] <test_db>
#             (Oblivion sigil stone only — takes three named JSON inputs)


def _s(label, game, script, mode, *, source=None, source_dir=None,
       dir_prefixes=None, named_sources=None) -> Step:
    return Step(
        label=label, game=game, script=script, mode=mode,
        source=source, source_dir=source_dir,
        dir_prefixes=dir_prefixes or [],
        named_sources=named_sources or {},
    )


# ─── Pipeline steps (in execution order) ─────────────────────────────────────

STEPS: List[Step] = [
    # ── Morrowind alchemy ─────────────────────────────────────────────────
    _s('MW alchemy ingredients', 'morrowind',
       MW / 'alchemy/ingredients_sql/create_or_update_morrowind_alchemy_ingredients.py',
       'diff', source=MW / 'alchemy/ingredients_json/morrowind_all_ingredients.json'),
    _s('MW alchemy effects', 'morrowind',
       MW / 'alchemy/ingredients_sql/create_or_update_morrowind_alchemy_effects.py',
       'diff', source=MW / 'alchemy/ingredients_json/morrowind_all_effects.json'),
    _s('MW alchemy apparatus', 'morrowind',
       MW / 'alchemy/apparatus_sql/create_or_update_morrowind_alchemy_apparatus.py',
       'direct', source=MW / 'alchemy/apparatus_json/morrowind_apparatus_records.json'),

    # ── Morrowind enchanting ──────────────────────────────────────────────
    # enchant_sql takes a json_dir and applies per-prefix diff files.
    _s('MW enchanting tables', 'morrowind',
       MW / 'enchanting/enchant_sql/create_or_update_morrowind_enchant_tables.py',
       'diff_dir', source_dir=MW / 'enchanting/enchant_json',
       dir_prefixes=['armor', 'books', 'clothing', 'weapons',
                     'soul_gems', 'magic_effects', 'magic_schools']),
    _s('MW enchant souls', 'morrowind',
       MW / 'enchanting/souls_sql/create_or_update_morrowind_enchant_souls.py',
       'direct', source=MW / 'enchanting/souls_json/morrowind_souls_records.json'),

    # ── Oblivion alchemy ──────────────────────────────────────────────────
    _s('OB alchemy ingredients', 'oblivion',
       OB / 'alchemy/ingredients_sql/create_or_update_oblivion_alchemy_ingredients.py',
       'diff', source=OB / 'alchemy/ingredients_json/oblivion_all_ingredients.json'),
    _s('OB alchemy effects', 'oblivion',
       OB / 'alchemy/ingredients_sql/create_or_update_oblivion_alchemy_effects.py',
       'diff', source=OB / 'alchemy/ingredients_json/oblivion_all_effects.json'),
    _s('OB alchemy apparatus', 'oblivion',
       OB / 'alchemy/apparatus_sql/create_or_update_oblivion_alchemy_apparatus.py',
       'direct', source=OB / 'alchemy/apparatus_json/oblivion_apparatus_records.json'),

    # ── Oblivion enchanting ───────────────────────────────────────────────
    # CSV-based; full-replace (no diff files).
    _s('OB enchant soul gems', 'oblivion',
       OB / 'enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py',
       'direct', source=OB / 'enchanting/enchant_parse/soul_gems.csv'),
    # Full-replace (if_exists='replace').
    _s('OB enchant effects', 'oblivion',
       OB / 'enchanting/enchant_effects_sql/create_or_update_oblivion_enchant_effects.py',
       'direct', source=OB / 'enchanting/enchant_effects_json/oblivion_enchant_effects.json'),
    # Three named JSON inputs; full-replace per table.
    _s('OB sigil stones', 'oblivion',
       OB / 'enchanting/sigil_stone_sql/create_or_update_oblivion_sigil_stone.py',
       'named', named_sources={
           '--in-stones':  OB / 'enchanting/sigil_stone_json/sigil_stone_records.json',
           '--in-weapons': OB / 'enchanting/sigil_stone_json/sigil_stone_weapon_magnitudes.json',
           '--in-armor':   OB / 'enchanting/sigil_stone_json/sigil_stone_armor_magnitudes.json',
       }),
    # Full-replace (no diff files).
    _s('OB enchant souls', 'oblivion',
       OB / 'enchanting/souls_sql/create_or_update_oblivion_enchant_souls.py',
       'direct', source=OB / 'enchanting/souls_json/oblivion_souls_records.json'),

    # ── Skyrim alchemy ────────────────────────────────────────────────────
    _s('SK alchemy ingredients', 'skyrim',
       SK / 'alchemy/ingredients_sql/create_or_update_skyrim_alchemy_ingredients.py',
       'diff', source=SK / 'alchemy/ingredients_json/skyrim_all_ingredients.json'),
    _s('SK alchemy effects', 'skyrim',
       SK / 'alchemy/ingredients_sql/create_or_update_skyrim_alchemy_effects.py',
       'diff', source=SK / 'alchemy/ingredients_json/skyrim_all_effects.json'),
    _s('SK alchemy perks', 'skyrim',
       SK / 'alchemy/perks_sql/create_or_update_skyrim_alchemy_perks.py',
       'diff', source=SK / 'alchemy/perks_json/skyrim_alchemy_perks.json'),

    # ── Skyrim enchanting ─────────────────────────────────────────────────
    _s('SK enchant soul gems', 'skyrim',
       SK / 'enchanting/gem_types_sql/create_or_update_skyrim_enchant_soulgems.py',
       'diff', source=SK / 'enchanting/gem_types_json/skyrim_enchant_soulgems.json'),
    # Full-replace (no diff files).
    _s('SK enchant souls', 'skyrim',
       SK / 'enchanting/creature_souls_sql/create_or_update_skyrim_enchant_souls.py',
       'direct', source=SK / 'enchanting/creature_souls_json/skyrim_enchant_souls.json'),
    _s('SK enchant perks', 'skyrim',
       SK / 'enchanting/perks_sql/create_or_update_skyrim_enchant_perks.py',
       'diff', source=SK / 'enchanting/perks_json/skyrim_enchant_perks.json'),
    _s('SK enchant weapon effects', 'skyrim',
       SK / 'enchanting/enchant_effects_sql/create_or_update_skyrim_enchant_effects.py',
       'diff', source=SK / 'enchanting/enchant_effects_json/skyrim_enchant_weapons.json'),
    _s('SK enchant apparel effects', 'skyrim',
       SK / 'enchanting/enchant_apparel_sql/create_or_update_skyrim_enchant_apparel.py',
       'diff', source=SK / 'enchanting/enchant_apparel_json/skyrim_enchant_apparel.json'),
    _s('SK disenchant apparel', 'skyrim',
       SK / 'enchanting/disenchant_apparel_sql/create_or_update_skyrim_enchant_disenchant_apparel.py',
       'diff', source=SK / 'enchanting/disenchant_apparel_json/disenchant_apparel.json'),
    _s('SK disenchant weapons', 'skyrim',
       SK / 'enchanting/disenchant_weapons_sql/create_or_update_skyrim_enchant_disenchant_weapons.py',
       'diff', source=SK / 'enchanting/disenchant_weapons_json/disenchant_weapons.json'),

    # ── Skyrim smithing ───────────────────────────────────────────────────
    _s('SK smithing perks', 'skyrim',
       SK / 'smithing/perks_sql/create_or_update_skyrim_smithing_perks.py',
       'diff', source=SK / 'smithing/perks_json/skyrim_smithing_perks.json'),
    _s('SK smithing armor', 'skyrim',
       SK / 'smithing/armor_sql/create_or_update_skyrim_smithing_armor.py',
       'diff', source=SK / 'smithing/armor_json/skyrim_smithing_armor.json'),
    _s('SK smithing weapons', 'skyrim',
       SK / 'smithing/weapons_sql/create_or_update_skyrim_smithing_weapons.py',
       'diff', source=SK / 'smithing/weapons_json/skyrim_smithing_weapons.json'),
    _s('SK smithing improvement', 'skyrim',
       SK / 'smithing/improvement_sql/create_or_update_skyrim_smithing_improvement.py',
       'diff', source=SK / 'smithing/improvement_json/skyrim_smithing_improvement.json'),
    _s('SK smithing materials', 'skyrim',
       SK / 'smithing/materials_sql/create_or_update_skyrim_smithing_materials.py',
       'diff', source=SK / 'smithing/materials_json/skyrim_smithing_materials.json'),
    _s('SK smelting', 'skyrim',
       SK / 'smithing/smelting_sql/create_or_update_skyrim_smelting.py',
       'diff', source=SK / 'smithing/smelting_json/skyrim_smelting.json'),

    # ── Skyrim homestead ──────────────────────────────────────────────────
    # All homestead loaders use full-replace on every run.
    _s('SK homestead build', 'skyrim',
       SK / 'homestead/build_sql/create_or_update_skyrim_homestead_build.py',
       'direct', source=SK / 'homestead/build_json/build_records.json'),
    _s('SK homestead exclusive exterior', 'skyrim',
       SK / 'homestead/exclusive_exterior_sql/create_or_update_skyrim_homestead_exclusive_exterior.py',
       'direct', source=SK / 'homestead/exclusive_exterior_json/exclusive_exterior_records.json'),
    _s('SK homestead steward cost', 'skyrim',
       SK / 'homestead/steward_cost_sql/create_or_update_skyrim_homestead_steward_cost.py',
       'direct', source=SK / 'homestead/steward_cost_json/steward_cost_records.json'),
    _s('SK homestead crafted components', 'skyrim',
       SK / 'homestead/crafted_components_sql/create_or_update_skyrim_homestead_crafted_components.py',
       'direct', source=SK / 'homestead/crafted_components_json/crafted_components_records.json'),

    # ── Skyrim Creation Club ──────────────────────────────────────────────
    # CC loaders use delete-then-insert per key (idempotent); no diff files.
    _s('SK CC armor', 'skyrim',
       CC / 'cc_armor_sql/create_or_update_skyrim_cc_armor.py',
       'direct', source=CC / 'cc_armor_json/cc_armor_records.json'),
    _s('SK CC weapons', 'skyrim',
       CC / 'cc_weapons_sql/create_or_update_skyrim_cc_weapons.py',
       'direct', source=CC / 'cc_weapons_json/cc_weapons_records.json'),
    _s('SK CC ammo', 'skyrim',
       CC / 'cc_ammo_sql/create_or_update_skyrim_cc_ammo.py',
       'direct', source=CC / 'cc_ammo_json/cc_ammo_records.json'),
    _s('SK CC homestead (Aquarium)', 'skyrim',
       CC / 'cc_homestead_sql/create_or_update_skyrim_cc_homestead.py',
       'direct', source=CC / 'cc_homestead_json/cc_homestead_records.json'),
    _s('SK CC tempering materials', 'skyrim',
       CC / 'cc_materials_sql/create_or_update_skyrim_cc_materials.py',
       'direct', source=CC / 'cc_materials_json/cc_tempering_materials.json'),
    # Must run after SK alchemy effects: does UPDATE on skyrim_alchemy_effects rows.
    _s('SK CC effects (UPDATE)', 'skyrim',
       CC / 'cc_effects_sql/create_or_update_skyrim_cc_effects.py',
       'direct', source=CC / 'cc_effects_json/cc_effects_records.json'),
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _banner(msg: str) -> None:
    print(f'\n── {msg}', flush=True)


def _abort(msg: str) -> None:
    print(f'\nFAIL: {msg}', file=sys.stderr, flush=True)
    sys.exit(1)


def _safe_label(label: str) -> str:
    """Convert a step label to a filesystem-safe string."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', label)


# ─── Step runner ─────────────────────────────────────────────────────────────

def run_step(step: Step, test_db: Path, tmp_root: Path, step_num: int,
             total: int) -> None:
    """Execute one SQL-loading step against test_db. Aborts the process on failure."""
    step_tmp = tmp_root / _safe_label(step.label)
    step_tmp.mkdir(parents=True, exist_ok=True)

    if step.mode == 'diff':
        src = step.source
        if not src.exists():
            _abort(f'[{step.label}] source not found: {src}')
        # Copy JSON to temp dir so diff files land there, not in the repo.
        dst = step_tmp / src.name
        shutil.copy2(src, dst)
        # Synthesize diff files: every row is an upsert; nothing to delete.
        records = json.loads(src.read_text())
        stem = src.stem
        (step_tmp / f'{stem}.upsert.json').write_text(json.dumps(records))
        (step_tmp / f'{stem}.delete.json').write_text('{}')
        cmd = [sys.executable, str(step.script), str(dst), str(test_db)]

    elif step.mode == 'direct':
        src = step.source
        if not src.exists():
            _abort(f'[{step.label}] source not found: {src}')
        cmd = [sys.executable, str(step.script), str(src), str(test_db)]

    elif step.mode == 'diff_dir':
        src_dir = step.source_dir
        if not src_dir.exists():
            _abort(f'[{step.label}] source directory not found: {src_dir}')
        # Copy each prefix.json and synthesize diff pairs in the temp dir.
        for prefix in step.dir_prefixes:
            src_file = src_dir / f'{prefix}.json'
            if not src_file.exists():
                _abort(f'[{step.label}] missing prefix file: {src_file}')
            records = json.loads(src_file.read_text())
            shutil.copy2(src_file, step_tmp / f'{prefix}.json')
            (step_tmp / f'{prefix}.upsert.json').write_text(json.dumps(records))
            (step_tmp / f'{prefix}.delete.json').write_text('{}')
        cmd = [sys.executable, str(step.script), str(step_tmp), str(test_db)]

    elif step.mode == 'named':
        for path in step.named_sources.values():
            if not path.exists():
                _abort(f'[{step.label}] source not found: {path}')
        cmd = [sys.executable, str(step.script)]
        for flag, path in step.named_sources.items():
            cmd += [flag, str(path)]
        cmd.append(str(test_db))

    else:
        _abort(f'[{step.label}] unknown mode: {step.mode!r}')

    print(f'  [{step_num}/{total}] {step.label} ... ', end='', flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print('FAILED', flush=True)
        print(f'\nFAIL: [{step.label}] exited with code {result.returncode}',
              file=sys.stderr)
        print(f'  script: {step.script}', file=sys.stderr)
        if result.stdout.strip():
            print('── stdout ──────────────────────────────────────────────',
                  file=sys.stderr)
            print(result.stdout.rstrip(), file=sys.stderr)
        if result.stderr.strip():
            print('── stderr ──────────────────────────────────────────────',
                  file=sys.stderr)
            print(result.stderr.rstrip(), file=sys.stderr)
        print('\nFix the issue above, then re-run.', file=sys.stderr)
        sys.exit(1)

    print('ok', flush=True)


# ─── Database comparison ──────────────────────────────────────────────────────

def _table_list(conn: sqlite3.Connection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]


def compare_databases(test_db: Path, games_filter: set) -> bool:
    """
    Compare test_db against the production database table-by-table.

    For each table in production (filtered by game):
      1. Check the table exists in test_db.
      2. Compare row counts.
      3. Use SQL EXCEPT to find rows present in one database but not the other.

    Returns True if all tables match, False if any differ.
    SQL errors (e.g. table missing) are caught per-table and reported clearly.

    The column named `index` is excluded from comparison everywhere it appears.
    That column is a pandas row-number artifact (written by to_sql with index=True)
    whose value depends on the order items appeared in the source JSON at load time.
    It carries no game data and would produce false positives whenever the JSON is
    re-ordered between pipeline runs.
    """
    prod_conn = sqlite3.connect(str(PROD_DB))
    test_conn = sqlite3.connect(str(test_db))

    try:
        prod_tables = _table_list(prod_conn)

        # Filter to the requested game(s).
        if 'all' not in games_filter:
            prod_tables = [t for t in prod_tables
                           if any(t.startswith(g) for g in games_filter)]

        test_tables = set(_table_list(test_conn))
        all_ok = True
        pad = max((len(t) for t in prod_tables), default=0)

        for table in prod_tables:
            label = table.ljust(pad)

            # ── 1. Existence check ──────────────────────────────────────
            if table not in test_tables:
                print(f'  {label}  MISSING — table was not created')
                all_ok = False
                continue

            # ── 2. Row count ────────────────────────────────────────────
            try:
                prod_n = prod_conn.execute(
                    f'SELECT COUNT(*) FROM {table}'
                ).fetchone()[0]
                test_n = test_conn.execute(
                    f'SELECT COUNT(*) FROM {table}'
                ).fetchone()[0]
            except sqlite3.OperationalError as exc:
                print(f'  {label}  SQL ERROR (count): {exc}')
                all_ok = False
                continue

            if prod_n != test_n:
                print(f'  {label}  ROW COUNT MISMATCH  '
                      f'prod={prod_n}  test={test_n}')
                _show_count_diff_sample(table, prod_conn, test_conn, prod_n, test_n)
                all_ok = False
                continue

            # ── 3. Full data comparison via SQL EXCEPT ──────────────────
            # Exclude the `index` column (pandas integer row-number artifact).
            # Its value depends on the order items appeared in the source JSON at
            # load time and carries no game data.
            all_cols = [r[1] for r in prod_conn.execute(
                f'PRAGMA table_info({table})'
            )]
            compare_cols = [c for c in all_cols if c != 'index']
            col_select = ', '.join(f'"{c}"' for c in compare_cols)

            # ATTACH the test DB to the prod connection for cross-DB queries.
            try:
                prod_conn.execute(f"ATTACH '{test_db}' AS testdb")
                try:
                    in_prod_only = prod_conn.execute(f"""
                        SELECT {col_select} FROM main.{table}
                        EXCEPT
                        SELECT {col_select} FROM testdb.{table}
                    """).fetchall()
                    in_test_only = prod_conn.execute(f"""
                        SELECT {col_select} FROM testdb.{table}
                        EXCEPT
                        SELECT {col_select} FROM main.{table}
                    """).fetchall()
                finally:
                    prod_conn.execute("DETACH testdb")
            except sqlite3.OperationalError as exc:
                print(f'  {label}  SQL ERROR (compare): {exc}')
                all_ok = False
                continue

            if not in_prod_only and not in_test_only:
                skipped = ' [index excluded]' if 'index' in all_cols else ''
                print(f'  {label}  OK  ({prod_n} rows){skipped}', flush=True)
            else:
                print(f'  {label}  DATA MISMATCH  '
                      f'{len(in_prod_only)} row(s) only in prod  '
                      f'{len(in_test_only)} row(s) only in test')
                if in_prod_only:
                    print(f'    prod-only (up to {_MAX_DIFF_SAMPLE}): '
                          f'{in_prod_only[:_MAX_DIFF_SAMPLE]}')
                if in_test_only:
                    print(f'    test-only (up to {_MAX_DIFF_SAMPLE}): '
                          f'{in_test_only[:_MAX_DIFF_SAMPLE]}')
                all_ok = False

    finally:
        prod_conn.close()
        test_conn.close()

    return all_ok


def _show_count_diff_sample(table: str, prod_conn, test_conn,
                             prod_n: int, test_n: int) -> None:
    """Print column names and a few rows from each side to aid diagnosis."""
    cols = [r[1] for r in prod_conn.execute(f'PRAGMA table_info({table})')]
    col_summary = ', '.join(cols[:6]) + ('...' if len(cols) > 6 else '')
    print(f'    columns ({len(cols)}): {col_summary}')
    if prod_n > 0:
        sample = prod_conn.execute(f'SELECT * FROM {table} LIMIT 2').fetchall()
        print(f'    prod sample: {sample}')
    if test_n > 0:
        sample = test_conn.execute(f'SELECT * FROM {table} LIMIT 2').fetchall()
        print(f'    test sample: {sample}')


# ─── Entry point ─────────────────────────────────────────────────────────────

USAGE = """\
Usage: python test_pipeline_e2e.py [morrowind|oblivion|skyrim|all]

  morrowind  Run Morrowind pipeline steps; compare morrowind_* tables.
  oblivion   Run Oblivion pipeline steps; compare oblivion_* tables.
  skyrim     Run Skyrim pipeline steps; compare skyrim_* tables.
  all        Run all steps; compare all tables. (default)

Run inside the dev Docker container from the repo root:
  sg docker -c "docker compose run --rm dev python TES/tests/end_to_end/test_pipeline_e2e.py [game]"
"""


def main() -> None:
    raw_args = sys.argv[1:]
    valid = {'morrowind', 'oblivion', 'skyrim', 'all'}

    if raw_args:
        if raw_args[0].lower() not in valid or len(raw_args) > 1:
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        games_filter = {raw_args[0].lower()}
    else:
        games_filter = {'all'}

    filter_label = next(iter(games_filter)).title() if 'all' not in games_filter \
        else 'All games'

    if not PROD_DB.exists():
        _abort(f'Production database not found: {PROD_DB}')

    steps = [s for s in STEPS
             if 'all' in games_filter or s.game in games_filter]

    print(f'TES End-to-End Pipeline Test — {filter_label}')
    print(f'Production DB : {PROD_DB}')
    print(f'Pipeline steps: {len(steps)}')

    tmp_root = Path(tempfile.mkdtemp(prefix='tes_e2e_'))
    test_db  = tmp_root / 'gametools_test.sqlite3'
    step_tmp = tmp_root / 'step_tmp'
    step_tmp.mkdir()

    print(f'Test DB       : {test_db}')

    # ── Phase 1: run all SQL-loading steps ───────────────────────────
    _banner(f'Phase 1 of 2 — loading {len(steps)} pipeline step(s)')
    for i, step in enumerate(steps, 1):
        run_step(step, test_db, step_tmp, i, len(steps))

    # ── Phase 2: compare test DB to production DB ────────────────────
    _banner('Phase 2 of 2 — comparing tables')
    ok = compare_databases(test_db, games_filter)

    if ok:
        shutil.rmtree(tmp_root)
        _banner('PASS — test database matches production')
        sys.exit(0)
    else:
        _banner(f'FAIL — one or more tables differ (see above)\n'
                f'       Test DB left for inspection: {test_db}')
        sys.exit(1)


if __name__ == '__main__':
    main()
