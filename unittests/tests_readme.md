# GameTools Test Suite

Unit and integration tests for all GameTools source modules, organized by game.

## Prerequisites — Docker (recommended)

Development runs inside a Docker container (Python 3.14). From the repo root:

```bash
# Build the image (only needed once, or after requirements.txt changes)
docker compose build

# Run all tests
docker compose run --rm dev python -m pytest unittests/ -v

# Run a specific game's tests
docker compose run --rm dev python -m pytest unittests/morrowind/

# Open an interactive shell in the container
docker compose run --rm dev bash
```

> **Note:** If `docker` commands fail with a permissions error, either log out and back in
> (to pick up the `docker` group), or prefix with `sg docker -c "..."`.

## Prerequisites — System Python fallback

```bash
pip install -r requirements.txt
```

> **Note:** The default `python3` (3.13) on this Debian system is missing `_sqlite3`.
> Use `/usr/bin/python3.11` if running outside Docker.

```bash
/usr/bin/python3.11 -m pytest unittests/ -v
```

## Test Structure

```
unittests/
  conftest.py              shared fixtures (tmp_db, make_json, load_module helper)
  morrowind/
    test_alchemy_parse.py  remove_pipe, remove_wiki_link, dash_to_null, parse, write_file
    test_alchemy_sql.py    create_morrowind_alchemy_ingredients.py / _effects.py (subprocess)
    test_enchant_parse.py  write_file, check_for_files
    test_enchant_sql.py    check_for_files, create_morrowind_enchant_tables.py (subprocess)
  oblivion/
    test_alchemy_parse.py  remove_pipe, remove_wiki_link, parse, write_file
    test_alchemy_sql.py    create_oblivion_alchemy_ingredients.py / _effects.py (subprocess)
    test_enchant_parse.py  write_file, check_for_files (CSV parser), MGEF data + write_file
  skyrim/
    test_alchemy_parse.py  remove_pipe, remove_wiki_link, parse, write_file
    test_alchemy_sql.py    create_skyrim_alchemy_ingredients.py / _effects.py (subprocess)
```

## Test Coverage

Each source module has:
- **At least one positive test** — verifies correct output given well-formed input
- **At least one negative test** — verifies correct handling of bad input (exception raised,
  empty return value, or non-zero exit code as appropriate)

### Notes on SQL script tests

The SQL loader scripts contain all logic inside `if __name__ == "__main__":` blocks and have
no importable functions, so they are tested by running them as subprocesses. These tests:
- Create a temporary SQLite database in a `tmp_path` directory (cleaned up after each test)
- Pass minimal sample JSON data to the script
- Verify the database contents using the standard `sqlite3` module

All temp files and databases are managed by pytest's `tmp_path` fixture and are automatically
removed after each test run.
