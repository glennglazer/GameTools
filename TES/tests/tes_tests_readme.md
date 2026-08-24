# TES Tests

Test suite for the Elder Scrolls data pipeline (Morrowind, Oblivion, Skyrim).

## Layout

```
TES/tests/
├── tes_tests_readme.md      ← this file
├── run_tests.py             ← driver script (see Usage below)
├── unittests/               ← tests with no external dependencies (760 tests)
│   ├── conftest.py          ← shared fixtures and REPO_ROOT
│   ├── test_json_diff.py    ← shared json_diff utility tests
│   ├── morrowind/
│   ├── oblivion/
│   └── skyrim/
├── integrationtests/        ← tests that spin up a real SQLite database (256 tests)
│   ├── conftest.py          ← shared fixtures and REPO_ROOT (same as unittests/)
│   ├── morrowind/
│   ├── oblivion/
│   └── skyrim/
└── end_to_end/              ← full pipeline smoke test (1 script)
    └── test_pipeline_e2e.py ← builds a fresh DB from all checked-in JSON, then diffs against prod
```

## Test Classification

**Unit tests** have no external dependencies, or mock any they have. This includes:
- Parser and scraper logic (wiki HTML → JSON transformations, field extraction, diff computation)
- `load_diff_file` helpers (file-not-found and sentinel-dict cases)
- Subprocess tests that invoke a script only against the local filesystem (no database)

**Integration tests** spin up a temporary SQLite database via the `tmp_db` fixture. This includes:
- `apply_deletes` / `apply_upserts` tests that write and read a real SQLite file
- Full pipeline subprocess tests (`first_run_*`, `upsert_*`, `delete_*`, `schema_migration_*`)

## Test Counts (as of 2026-08-24)

| Suite | Tests |
|---|---|
| Unit | 760 |
| Integration | 256 |
| **Total** | **1016** |
| End-to-end | 1 script, 38 steps, 41 table comparisons |

## Usage

All commands must be run inside the dev Docker container from the repo root:

```bash
# All tests
sg docker -c "docker compose run --rm dev python TES/tests/run_tests.py"

# Unit tests only
sg docker -c "docker compose run --rm dev python TES/tests/run_tests.py unit"

# Integration tests only
sg docker -c "docker compose run --rm dev python TES/tests/run_tests.py integration"
```

Any arguments after the mode word are passed through to pytest:

```bash
# Verbose output, filter by name
sg docker -c "docker compose run --rm dev python TES/tests/run_tests.py unit -v -k test_load_diff"

# Stop on first failure
sg docker -c "docker compose run --rm dev python TES/tests/run_tests.py integration -x"
```

You can also invoke pytest directly against a subdirectory:

```bash
sg docker -c "docker compose run --rm dev python -m pytest TES/tests/unittests/skyrim/ -v"
```

## End-to-End Pipeline Test

`TES/tests/end_to_end/test_pipeline_e2e.py` is a standalone script (not pytest) that:

1. Creates a blank SQLite database in a temp directory
2. Runs all 38 SQL-loading steps from the checked-in JSON source files
3. Compares every table in the result against the production DB (`TES/database/gametools.sqlite3`)

It runs the SQL-loading stage only — scrape and JSON-parse stages require network and are not included.

### Usage

```bash
# All three games (38 steps, 41 tables)
sg docker -c "docker compose run --rm dev python TES/tests/end_to_end/test_pipeline_e2e.py all"

# Single game (subset of steps/tables)
sg docker -c "docker compose run --rm dev python TES/tests/end_to_end/test_pipeline_e2e.py morrowind"
sg docker -c "docker compose run --rm dev python TES/tests/end_to_end/test_pipeline_e2e.py oblivion"
sg docker -c "docker compose run --rm dev python TES/tests/end_to_end/test_pipeline_e2e.py skyrim"
```

**Fail-fast behavior**: any non-zero exit from a pipeline step aborts immediately with the step label, exit code, and full stdout/stderr. SQL errors during comparison are caught per table and reported. The script exits 0 on full match, 1 on any mismatch.

## conftest.py Fixtures

Both `unittests/conftest.py` and `integrationtests/conftest.py` provide:

- **`REPO_ROOT`** — absolute path to the repository root (used to locate source scripts)
- **`tmp_db`** — pytest fixture; creates a temporary SQLite file and returns its path (integration tests only)
- **`make_json`** — pytest fixture factory; writes a list of dicts to a temp JSON file
- **`load_module(rel_path, name)`** — imports a pipeline script as a module by repo-relative path
