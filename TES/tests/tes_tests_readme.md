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
└── integrationtests/        ← tests that spin up a real SQLite database (256 tests)
    ├── conftest.py          ← shared fixtures and REPO_ROOT (same as unittests/)
    ├── morrowind/
    ├── oblivion/
    └── skyrim/
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

## conftest.py Fixtures

Both `unittests/conftest.py` and `integrationtests/conftest.py` provide:

- **`REPO_ROOT`** — absolute path to the repository root (used to locate source scripts)
- **`tmp_db`** — pytest fixture; creates a temporary SQLite file and returns its path (integration tests only)
- **`make_json`** — pytest fixture factory; writes a list of dicts to a temp JSON file
- **`load_module(rel_path, name)`** — imports a pipeline script as a module by repo-relative path
