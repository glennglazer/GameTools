"""Unit tests for skyrim disenchant SQL loaders (load_diff_file only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_apparel = load_module(
    'TES/Skyrim/enchanting/disenchant_apparel_sql/create_or_update_skyrim_enchant_disenchant_apparel.py',
    'sk_disenchant_apparel_sql',
)
_weapons = load_module(
    'TES/Skyrim/enchanting/disenchant_weapons_sql/create_or_update_skyrim_enchant_disenchant_weapons.py',
    'sk_disenchant_weapons_sql',
)


# ---------------------------------------------------------------------------
# load_diff_file (unit tests — no DB)
# ---------------------------------------------------------------------------

def test_apparel_load_diff_file_missing(tmp_path):
    data, found = _apparel.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found


def test_weapons_load_diff_file_missing(tmp_path):
    data, found = _weapons.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found
