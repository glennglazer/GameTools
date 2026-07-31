"""Tests for TES/Skyrim/smithing/smelting_json/skyrim_parse_smelting_to_json.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    'TES/Skyrim/smithing/smelting_json/skyrim_parse_smelting_to_json.py',
    'sk_smelting_parse',
)
parse          = _mod.parse
build_record   = _mod.build_record
compute_diff   = _mod.compute_diff
load_raw       = _mod.load_raw
write_file     = _mod.write_file
write_diff_files = _mod.write_diff_files
record_key     = _mod.record_key
STEEL_ROWS     = _mod.STEEL_ROWS
CC_RECIPES     = _mod.CC_RECIPES
STALHRIM_ROW   = _mod.STALHRIM_ROW


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_RAW = {
    'recipes': [
        {'source': 'Iron Ore', 'source_to_ingot': 1,
         'ingot': 'Iron Ingot', 'ingots_produced': 1},
        {'source': 'Silver Ore', 'source_to_ingot': 2,
         'ingot': 'Silver Ingot', 'ingots_produced': 1},
    ],
    'material_stats': {
        'Iron Ore':    {'weight': 1, 'value': 2},
        'Silver Ore':  {'weight': 1, 'value': 25},
        'Corundum Ore': {'weight': 1, 'value': 20},
        'Amber':       {'weight': 1, 'value': 75},
        'Madness Ore': {'weight': 2, 'value': 20},
    },
    'ingot_stats': {
        'Iron Ingot':    {'weight': 1, 'value': 7},
        'Silver Ingot':  {'weight': 1, 'value': 50},
        'Steel Ingot':   {'weight': 1, 'value': 20},
        'Refined Amber': {'weight': 1, 'value': 150},
        'Madness Ingot': {'weight': 1, 'value': 150},
    },
}


# ---------------------------------------------------------------------------
# build_record
# ---------------------------------------------------------------------------

def test_build_record_populates_source_stats():
    rec = build_record('Iron Ore', 1, 'Iron Ingot', 1,
                       {'Iron Ore': {'weight': 1, 'value': 2}},
                       {'Iron Ingot': {'weight': 1, 'value': 7}})
    assert rec['Source_Weight'] == 1
    assert rec['Source_Value'] == 2
    assert rec['Ingot_Weight'] == 1
    assert rec['Ingot_Value'] == 7

def test_build_record_missing_source_gives_none():
    rec = build_record('Unknown', 1, 'Iron Ingot', 1, {}, {'Iron Ingot': {'weight': 1, 'value': 7}})
    assert rec['Source_Weight'] is None
    assert rec['Source_Value'] is None

def test_build_record_note_defaults_to_none():
    rec = build_record('Iron Ore', 1, 'Iron Ingot', 1, {}, {})
    assert rec['Note'] is None

def test_build_record_note_preserved():
    rec = build_record('Iron Ore', 1, 'Steel Ingot', 1, {}, {}, note='Also requires 1 Corundum Ore')
    assert rec['Note'] == 'Also requires 1 Corundum Ore'

def test_build_record_source_to_ingot_stored():
    rec = build_record('Silver Ore', 2, 'Silver Ingot', 1, {}, {})
    assert rec['Source_To_Ingot'] == 2
    assert rec['Ingots_Produced'] == 1


# ---------------------------------------------------------------------------
# parse — basic structure
# ---------------------------------------------------------------------------

def test_parse_returns_list():
    assert isinstance(parse(MINIMAL_RAW), list)

def test_parse_includes_base_recipes():
    records = parse(MINIMAL_RAW)
    names = [r['Source_Name'] for r in records]
    assert 'Iron Ore' in names
    assert 'Silver Ore' in names

def test_parse_includes_steel_rows():
    records = parse(MINIMAL_RAW)
    steel_rows = [r for r in records if r.get('Ingot_Name') == 'Steel Ingot']
    assert len(steel_rows) == 2
    src_names = {r['Source_Name'] for r in steel_rows}
    assert 'Iron Ore' in src_names
    assert 'Corundum Ore' in src_names

def test_parse_steel_iron_ore_note():
    records = parse(MINIMAL_RAW)
    iron_steel = next(r for r in records
                      if r['Source_Name'] == 'Iron Ore' and r['Ingot_Name'] == 'Steel Ingot')
    assert 'Corundum' in iron_steel['Note']

def test_parse_steel_corundum_ore_note():
    records = parse(MINIMAL_RAW)
    cor_steel = next(r for r in records
                     if r['Source_Name'] == 'Corundum Ore' and r['Ingot_Name'] == 'Steel Ingot')
    assert 'Iron' in cor_steel['Note']

def test_parse_includes_stalhrim_row():
    records = parse(MINIMAL_RAW)
    stalhrim = [r for r in records if r['Source_Name'] == 'Stalhrim']
    assert len(stalhrim) == 1

def test_parse_stalhrim_numeric_fields_are_none():
    records = parse(MINIMAL_RAW)
    s = next(r for r in records if r['Source_Name'] == 'Stalhrim')
    for field in ('Source_Weight', 'Source_Value', 'Source_To_Ingot',
                  'Ingots_Produced', 'Ingot_Weight', 'Ingot_Value'):
        assert s[field] is None, f'{field} should be None'

def test_parse_stalhrim_ingot_name_is_none():
    records = parse(MINIMAL_RAW)
    s = next(r for r in records if r['Source_Name'] == 'Stalhrim')
    assert s['Ingot_Name'] is None

def test_parse_stalhrim_note_set():
    records = parse(MINIMAL_RAW)
    s = next(r for r in records if r['Source_Name'] == 'Stalhrim')
    assert s['Note'] and 'smelting' in s['Note'].lower()

def test_parse_includes_cc_amber():
    records = parse(MINIMAL_RAW)
    amber = [r for r in records if r['Source_Name'] == 'Amber']
    assert len(amber) == 1
    assert amber[0]['Ingot_Name'] == 'Refined Amber'
    assert amber[0]['Source_To_Ingot'] == 2

def test_parse_includes_cc_madness():
    records = parse(MINIMAL_RAW)
    madness = [r for r in records if r['Source_Name'] == 'Madness Ore']
    assert len(madness) == 1
    assert madness[0]['Ingot_Name'] == 'Madness Ingot'
    assert madness[0]['Source_To_Ingot'] == 2

def test_parse_cc_note_set():
    records = parse(MINIMAL_RAW)
    amber = next(r for r in records if r['Source_Name'] == 'Amber')
    assert amber['Note'] and 'Creation Club' in amber['Note']

def test_parse_record_has_all_columns():
    records = parse(MINIMAL_RAW)
    expected = {'Source_Name', 'Source_Weight', 'Source_Value', 'Source_To_Ingot',
                'Ingot_Name', 'Ingots_Produced', 'Ingot_Weight', 'Ingot_Value', 'Note'}
    for r in records:
        assert set(r.keys()) == expected

def test_parse_integer_types():
    records = parse(MINIMAL_RAW)
    for r in records:
        for field in ('Source_Weight', 'Source_Value', 'Source_To_Ingot',
                      'Ingots_Produced', 'Ingot_Weight', 'Ingot_Value'):
            if r[field] is not None:
                assert isinstance(r[field], int), f'{r["Source_Name"]}.{field} should be int'


# ---------------------------------------------------------------------------
# parse — Dwemer ingots_produced
# ---------------------------------------------------------------------------

DWEMER_RAW = {
    'recipes': [
        {'source': 'Solid Dwemer Metal', 'source_to_ingot': 1,
         'ingot': 'Dwarven Metal Ingot', 'ingots_produced': 5},
        {'source': 'Large Decorative Dwemer Strut', 'source_to_ingot': 1,
         'ingot': 'Dwarven Metal Ingot', 'ingots_produced': 2},
    ],
    'material_stats': {
        'Solid Dwemer Metal': {'weight': 25, 'value': 25},
        'Large Decorative Dwemer Strut': {'weight': 15, 'value': 10},
        'Corundum Ore': {'weight': 1, 'value': 20},
        'Amber': {'weight': 1, 'value': 75},
        'Madness Ore': {'weight': 2, 'value': 20},
    },
    'ingot_stats': {
        'Dwarven Metal Ingot': {'weight': 1, 'value': 30},
        'Steel Ingot': {'weight': 1, 'value': 20},
        'Refined Amber': {'weight': 1, 'value': 150},
        'Madness Ingot': {'weight': 1, 'value': 150},
    },
}

def test_parse_dwemer_ingots_produced():
    records = parse(DWEMER_RAW)
    solid = next(r for r in records if r['Source_Name'] == 'Solid Dwemer Metal')
    assert solid['Ingots_Produced'] == 5

def test_parse_dwemer_source_to_ingot():
    records = parse(DWEMER_RAW)
    strut = next(r for r in records if r['Source_Name'] == 'Large Decorative Dwemer Strut')
    assert strut['Source_To_Ingot'] == 1
    assert strut['Ingots_Produced'] == 2

def test_parse_dwemer_source_weight():
    records = parse(DWEMER_RAW)
    solid = next(r for r in records if r['Source_Name'] == 'Solid Dwemer Metal')
    assert solid['Source_Weight'] == 25


# ---------------------------------------------------------------------------
# record_key
# ---------------------------------------------------------------------------

def test_record_key_normal():
    r = {'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot'}
    assert record_key(r) == ('Iron Ore', 'Iron Ingot')

def test_record_key_null_ingot():
    r = {'Source_Name': 'Stalhrim', 'Ingot_Name': None}
    assert record_key(r) == ('Stalhrim', None)


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------

def test_compute_diff_no_change():
    data = [{'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot', 'Source_Value': 2}]
    u, d = compute_diff(data, data)
    assert u == [] and d == []

def test_compute_diff_new_row():
    old = [{'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot', 'Source_Value': 2}]
    new = old + [{'Source_Name': 'Gold Ore', 'Ingot_Name': 'Gold Ingot', 'Source_Value': 50}]
    u, d = compute_diff(old, new)
    assert len(u) == 1 and u[0]['Source_Name'] == 'Gold Ore'
    assert d == []

def test_compute_diff_deleted_row():
    old = [
        {'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot', 'Source_Value': 2},
        {'Source_Name': 'Gold Ore', 'Ingot_Name': 'Gold Ingot', 'Source_Value': 50},
    ]
    new = [old[0]]
    u, d = compute_diff(old, new)
    assert d[0]['Source_Name'] == 'Gold Ore'
    assert u == []

def test_compute_diff_changed_value():
    old = [{'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot', 'Source_Value': 2}]
    new = [{'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot', 'Source_Value': 99}]
    u, d = compute_diff(old, new)
    assert len(u) == 1
    assert u[0]['Source_Value'] == 99


# ---------------------------------------------------------------------------
# write_file / write_diff_files
# ---------------------------------------------------------------------------

def test_write_file_creates_valid_json(tmp_path):
    outfile = str(tmp_path / 'out.json')
    data = [{'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot'}]
    write_file(data, outfile)
    loaded = json.loads(Path(outfile).read_text())
    assert loaded == data

def test_write_file_bad_path_raises():
    with pytest.raises(OSError):
        write_file([], '/nonexistent_dir_xyz/out.json')

def test_write_diff_files_creates_upsert_and_delete(tmp_path):
    outfile = str(tmp_path / 'skyrim_smelting.json')
    u = [{'Source_Name': 'Iron Ore', 'Ingot_Name': 'Iron Ingot'}]
    d = [{'Source_Name': 'Gold Ore', 'Ingot_Name': 'Gold Ingot'}]
    write_diff_files(outfile, u, d)
    assert (tmp_path / 'skyrim_smelting.upsert.json').exists()
    assert (tmp_path / 'skyrim_smelting.delete.json').exists()

def test_write_diff_files_bad_path_raises():
    with pytest.raises(OSError):
        write_diff_files('/nonexistent_dir_xyz/out.json', [], [])


# ---------------------------------------------------------------------------
# load_raw
# ---------------------------------------------------------------------------

def test_load_raw_valid_json(tmp_path):
    p = tmp_path / 'raw.json'
    p.write_text(json.dumps(MINIMAL_RAW))
    result = load_raw(str(p))
    assert 'recipes' in result

def test_load_raw_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        load_raw(str(tmp_path / 'nonexistent.json'))

def test_load_raw_invalid_json_raises(tmp_path):
    p = tmp_path / 'bad.json'
    p.write_text('{not valid json')
    with pytest.raises(json.JSONDecodeError):
        load_raw(str(p))
