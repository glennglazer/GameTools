"""Unit tests for skyrim_enchant_soulgems SQL loader (load_diff_file only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_gem = load_module(
    'TES/Skyrim/enchanting/gem_types_sql/create_or_update_skyrim_enchant_soulgems.py',
    'sk_gem_sql',
)


# ---------------------------------------------------------------------------
# load_diff_file (unit tests — no DB)
# ---------------------------------------------------------------------------

def test_gem_load_diff_file_missing(tmp_path):
    data, found = _gem.load_diff_file(str(tmp_path / 'missing.json'))
    assert not found

def test_gem_load_diff_file_sentinel_dict(tmp_path):
    p = tmp_path / 'f.json'
    p.write_text('{}')
    data, found = _gem.load_diff_file(str(p))
    assert found
    assert data == []
