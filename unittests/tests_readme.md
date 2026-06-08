# GameTools Test Suite

Unit and integration tests for all GameTools source modules, organized by game.

## Prerequisites

```bash
pip install pytest pandas
```

> **Note:** The default `python3` on this system (3.13) is missing the `_sqlite3` C extension.
> Use `/usr/bin/python3.11` to run the tests.

## Running the Tests

From the repository root:

```bash
# Run all tests
/usr/bin/python3.11 -m pytest unittests/

# Run with verbose output
/usr/bin/python3.11 -m pytest unittests/ -v

# Run a specific game's tests
/usr/bin/python3.11 -m pytest unittests/morrowind/
/usr/bin/python3.11 -m pytest unittests/oblivion/
/usr/bin/python3.11 -m pytest unittests/skyrim/

# Run a specific test file
/usr/bin/python3.11 -m pytest unittests/morrowind/test_alchemy_parse.py

# Run a specific test function
/usr/bin/python3.11 -m pytest unittests/morrowind/test_alchemy_parse.py::test_parse_single_entry_ingredient_fields

# Show output from print statements (useful for debugging failures)
/usr/bin/python3.11 -m pytest unittests/ -s
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
