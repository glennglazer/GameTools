import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()


def load_module(rel_path: str, module_name: str):
    """Load a source module by repo-relative path, avoiding __main__ execution."""
    abs_path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.sqlite3")


@pytest.fixture
def make_json(tmp_path):
    """Factory: write data as JSON to a temp file and return its path."""
    def _make(data, filename="data.json"):
        p = tmp_path / filename
        p.write_text(json.dumps(data))
        return str(p)
    return _make
