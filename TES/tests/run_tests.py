#!/usr/bin/env python3
"""Driver script for the GameTools TES test suite.

Usage (from the repo root, inside the dev Docker container):

    python TES/tests/run_tests.py             # all tests
    python TES/tests/run_tests.py unit        # unit tests only
    python TES/tests/run_tests.py integration # integration tests only

Any extra arguments after the mode word are passed through to pytest, e.g.:
    python TES/tests/run_tests.py unit -v -k test_load_diff
"""
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).parent.resolve()
UNIT_DIR = THIS_DIR / "unittests"
INTEG_DIR = THIS_DIR / "integrationtests"

USAGE = (
    "Usage: python run_tests.py [unit|integration|all] [pytest-args...]\n"
    "  unit        — run TES/tests/unittests/ only\n"
    "  integration — run TES/tests/integrationtests/ only\n"
    "  all         — run both (default if no mode given)\n"
)


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] in ("unit", "integration", "all"):
        mode, extra = args[0], args[1:]
    elif not args or args[0].startswith("-"):
        # No mode token — treat everything as pytest args, run all
        mode, extra = "all", args
    else:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    if mode == "unit":
        targets = [str(UNIT_DIR)]
    elif mode == "integration":
        targets = [str(INTEG_DIR)]
    else:
        targets = [str(UNIT_DIR), str(INTEG_DIR)]

    cmd = [sys.executable, "-m", "pytest"] + targets + list(extra)
    print(f"Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
