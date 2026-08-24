"""Unit tests for Oblivion alchemy SQL loader scripts (load_diff_file only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_ing_mod = load_module(
    "TES/Oblivion/alchemy/ingredients_sql/create_or_update_oblivion_alchemy_ingredients.py",
    "ob_ing_sql",
)

load_diff_file = _ing_mod.load_diff_file


# ---------------------------------------------------------------------------
# load_diff_file (unit test — no DB)
# ---------------------------------------------------------------------------

def test_load_diff_file_missing_returns_false(tmp_path):
    data, found = load_diff_file(str(tmp_path / "missing.json"))
    assert not found
    assert data == []
