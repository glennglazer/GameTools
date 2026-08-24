"""Unit tests for Oblivion enchant SQL loader (read_csv and rows_match — no DB)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module

_mod = load_module(
    "TES/Oblivion/enchanting/enchant_sql/create_or_update_oblivion_enchant_tables.py",
    "ob_enchant_sql",
)
read_csv = _mod.read_csv
rows_match = _mod.rows_match
TABLE_NAME = _mod.TABLE_NAME

SAMPLE_CSV = (
    "SLGM,Oblivion.esm,0x000193,AzurasStar,0.700000,2500\n"
    "SLGM,Oblivion.esm,0x000192,BlackSoulGem,0.500000,500\n"
)
SAMPLE_ROWS = [
    {'ID': 'AzurasStar',   'object_index': '0x000193', 'weight': 0.7,  'value': 2500},
    {'ID': 'BlackSoulGem', 'object_index': '0x000192', 'weight': 0.5,  'value':  500},
]


def make_csv(tmp_path, content=SAMPLE_CSV):
    p = tmp_path / "soul_gems.csv"
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# read_csv (unit tests — filesystem CSV only, no DB)
# ---------------------------------------------------------------------------

def test_read_csv_returns_correct_row_count(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert len(rows) == 2

def test_read_csv_maps_columns_correctly(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert rows[0]['ID'] == 'AzurasStar'
    assert rows[0]['object_index'] == '0x000193'
    assert rows[0]['weight'] == 0.7
    assert rows[0]['value'] == 2500

def test_read_csv_weight_is_float(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert isinstance(rows[0]['weight'], float)

def test_read_csv_value_is_int(tmp_path):
    rows = read_csv(make_csv(tmp_path))
    assert isinstance(rows[0]['value'], int)

def test_read_csv_missing_file_raises():
    with pytest.raises(OSError):
        read_csv("/nonexistent_dir_xyz/soul_gems.csv")

def test_read_csv_bad_value_field_raises(tmp_path):
    bad_csv = "SLGM,Oblivion.esm,0x000193,AzurasStar,0.700000,NOT_AN_INT\n"
    with pytest.raises(ValueError):
        read_csv(make_csv(tmp_path, bad_csv))


# ---------------------------------------------------------------------------
# rows_match (unit tests — pure in-memory comparison, no DB)
# ---------------------------------------------------------------------------

def test_rows_match_identical_data():
    db_rows = sorted(SAMPLE_ROWS, key=lambda r: r['ID'])
    assert rows_match(SAMPLE_ROWS, db_rows) is True

def test_rows_match_different_value():
    db_rows = [{'ID': 'AzurasStar', 'object_index': '0x000193', 'weight': 0.7, 'value': 9999}]
    assert rows_match(SAMPLE_ROWS[:1], db_rows) is False

def test_rows_match_different_row_count():
    db_rows = sorted(SAMPLE_ROWS, key=lambda r: r['ID'])
    assert rows_match(SAMPLE_ROWS[:1], db_rows) is False

def test_rows_match_empty_vs_empty():
    assert rows_match([], []) is True
