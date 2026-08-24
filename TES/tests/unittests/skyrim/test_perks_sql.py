"""Unit tests for Skyrim alchemy perks SQL loader (load_diff_file only)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_mod = load_module(
    'TES/Skyrim/alchemy/perks_sql/create_or_update_skyrim_alchemy_perks.py',
    'sk_perks_sql',
)
load_diff_file = _mod.load_diff_file

SAMPLE_PERKS = [
    {'name': 'Alchemist (1/5)', 'skill_level': 0, 'prerequisite': 'None',
     'description': 'Potions and poisons are 20% stronger.'},
    {'name': 'Physician', 'skill_level': 20, 'prerequisite': 'Alchemist (1/5)',
     'description': 'Potions restore health 25% more.'},
]


# ---------------------------------------------------------------------------
# load_diff_file (unit tests — no DB)
# ---------------------------------------------------------------------------

def test_load_diff_file_missing_returns_false(tmp_path):
    data, found = load_diff_file(str(tmp_path / 'missing.json'))
    assert not found
    assert data == []

def test_load_diff_file_present_returns_data(tmp_path):
    p = tmp_path / 'data.json'
    p.write_text(json.dumps(SAMPLE_PERKS))
    data, found = load_diff_file(str(p))
    assert found
    assert data == SAMPLE_PERKS

def test_load_diff_file_sentinel_dict_returns_empty(tmp_path):
    p = tmp_path / 'empty.json'
    p.write_text('{}')
    data, found = load_diff_file(str(p))
    assert found
    assert data == []
