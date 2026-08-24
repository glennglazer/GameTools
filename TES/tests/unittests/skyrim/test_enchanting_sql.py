"""Unit tests for Skyrim enchanting SQL loaders (load_diff_file only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_perks = load_module(
    'TES/Skyrim/enchanting/perks_sql/create_or_update_skyrim_enchant_perks.py',
    'sk_enchant_perks_sql',
)


# ---------------------------------------------------------------------------
# load_diff_file (unit test — no DB)
# ---------------------------------------------------------------------------

def test_perks_load_diff_file_missing(tmp_path):
    data, found = _perks.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found
