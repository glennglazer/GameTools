"""Tests for TES/Oblivion/alchemy/apparatus_json/oblivion_parse_apparatus.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "TES/Oblivion/alchemy/apparatus_json/oblivion_parse_apparatus.py",
    "ob_apparatus_parse",
)
parse_apparatus = _mod.parse_apparatus

# ---------------------------------------------------------------------------
# Synthetic HTML fixtures
# ---------------------------------------------------------------------------

# Single item, 2 grades — mirrors real rowspan structure
TWO_GRADE_TABLE = """
<table class="wikitable">
<tr><th></th><th>Name</th><th>Grade</th><th>ID</th><th>W</th><th>V</th><th>Str</th><th>Notes</th></tr>
<tr>
  <td rowspan="2"><img/></td>
  <td rowspan="2"><span id="Alembic"></span>Alembic</td>
  <td>Novice</td>
  <td><span class="idall"><span class="idref">00<span class="idcase">010604</span></span></span></td>
  <td>7.0</td><td>50</td><td>0.1</td>
  <td rowspan="2">Decreases negative effects.</td>
</tr>
<tr>
  <td>Apprentice</td>
  <td><span class="idall"><span class="idref">00<span class="idcase">06E310</span></span></span></td>
  <td>7.25</td><td>100</td><td>0.25</td>
</tr>
</table>
"""

# Mortar & Pestle with italic tutorial first row + 2 regular grades
MORTAR_TABLE = """
<table class="wikitable">
<tr><th></th><th>Name</th><th>Grade</th><th>ID</th><th>W</th><th>V</th><th>Str</th><th>Notes</th></tr>
<tr>
  <td rowspan="3"><img/></td>
  <td rowspan="3"><span id="Mortar_.26_Pestle"></span>Mortar &amp; Pestle</td>
  <td><i>Novice</i></td>
  <td><i><span class="idall"><span class="idref">00<span class="idcase">0C7968</span></span></span></i></td>
  <td><i>1.0</i></td><td><i>25</i></td><td><i>0.1</i></td>
  <td rowspan="3">Required for all Alchemy.</td>
</tr>
<tr>
  <td>Novice</td>
  <td><span class="idall"><span class="idref">00<span class="idcase">0105E3</span></span></span></td>
  <td>1.0</td><td>25</td><td>0.1</td>
</tr>
<tr>
  <td>Apprentice</td>
  <td><span class="idall"><span class="idref">00<span class="idcase">06E312</span></span></span></td>
  <td>1.25</td><td>75</td><td>0.25</td>
</tr>
</table>
"""

# Two tables in the HTML — only the first should be parsed
TWO_TABLE_HTML = """
<table class="wikitable">
<tr><th></th><th>Name</th><th>Grade</th><th>ID</th><th>W</th><th>V</th><th>Str</th><th>Notes</th></tr>
<tr>
  <td rowspan="1"><img/></td>
  <td rowspan="1"><span id="Alembic"></span>Alembic</td>
  <td>Novice</td>
  <td><span class="idall"><span class="idref">00<span class="idcase">010604</span></span></span></td>
  <td>7.0</td><td>50</td><td>0.1</td>
  <td rowspan="1">Notes here.</td>
</tr>
</table>
<table class="wikitable">
<tr><th>Level</th><th>Vendor</th><th>Dungeon</th></tr>
<tr><td>Novice</td><td>1</td><td>1</td></tr>
</table>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parses_two_grades():
    records = parse_apparatus(TWO_GRADE_TABLE)
    assert len(records) == 2

def test_record_fields_present():
    r = parse_apparatus(TWO_GRADE_TABLE)[0]
    assert set(r.keys()) == {"name", "grade", "id", "weight", "cost", "strength"}

def test_name_carried_across_rows():
    records = parse_apparatus(TWO_GRADE_TABLE)
    assert all(r["name"] == "Alembic" for r in records)

def test_first_row_grade():
    records = parse_apparatus(TWO_GRADE_TABLE)
    assert records[0]["grade"] == "Novice"

def test_subsequent_row_grade():
    records = parse_apparatus(TWO_GRADE_TABLE)
    assert records[1]["grade"] == "Apprentice"

def test_id_extraction_concatenates_spans():
    records = parse_apparatus(TWO_GRADE_TABLE)
    assert records[0]["id"] == "00010604"
    assert records[1]["id"] == "0006E310"

def test_weight_as_float():
    r = parse_apparatus(TWO_GRADE_TABLE)[0]
    assert r["weight"] == 7.0
    assert isinstance(r["weight"], float)

def test_cost_as_int():
    r = parse_apparatus(TWO_GRADE_TABLE)[0]
    assert r["cost"] == 50
    assert isinstance(r["cost"], int)

def test_strength_as_float():
    r = parse_apparatus(TWO_GRADE_TABLE)[0]
    assert r["strength"] == 0.1
    assert isinstance(r["strength"], float)

def test_no_notes_in_records():
    r = parse_apparatus(TWO_GRADE_TABLE)[0]
    assert "notes" not in r

def test_html_entity_in_name():
    records = parse_apparatus(MORTAR_TABLE)
    assert all(r["name"] == "Mortar & Pestle" for r in records)

def test_italic_tutorial_row_included():
    records = parse_apparatus(MORTAR_TABLE)
    assert len(records) == 3

def test_italic_tutorial_id():
    records = parse_apparatus(MORTAR_TABLE)
    assert records[0]["id"] == "000C7968"

def test_italic_values_parsed_correctly():
    records = parse_apparatus(MORTAR_TABLE)
    tutorial = records[0]
    assert tutorial["weight"] == 1.0
    assert tutorial["cost"] == 25
    assert tutorial["strength"] == 0.1

def test_only_first_table_parsed():
    records = parse_apparatus(TWO_TABLE_HTML)
    # Second table has 3-column rows — none match 8 or 5, so only first table rows
    assert len(records) == 1
    assert records[0]["name"] == "Alembic"

def test_raises_on_missing_table():
    with pytest.raises(ValueError, match="No wikitable"):
        parse_apparatus("<div>no table</div>")

def test_empty_table_returns_empty_list():
    html = '<table class="wikitable"><tr><th>X</th></tr></table>'
    assert parse_apparatus(html) == []


# ---------------------------------------------------------------------------
# Integration test against real raw JSON
# ---------------------------------------------------------------------------

_RAW_JSON = REPO_ROOT / "TES/Oblivion/alchemy/apparatus_parse/oblivion_apparatus_raw.json"

@pytest.mark.skipif(not _RAW_JSON.exists(), reason="raw JSON not present")
def test_integration_record_count():
    with open(_RAW_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    records = parse_apparatus(raw["html"])
    assert len(records) == 21  # 4 items × 5 grades + 1 tutorial Mortar

@pytest.mark.skipif(not _RAW_JSON.exists(), reason="raw JSON not present")
def test_integration_all_have_required_fields():
    with open(_RAW_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    records = parse_apparatus(raw["html"])
    for r in records:
        assert r["name"] and r["grade"] and r["id"]
        assert isinstance(r["weight"], float)
        assert isinstance(r["cost"], int)
        assert isinstance(r["strength"], float)

@pytest.mark.skipif(not _RAW_JSON.exists(), reason="raw JSON not present")
def test_integration_master_alembic():
    with open(_RAW_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    records = parse_apparatus(raw["html"])
    master = next(r for r in records if r["name"] == "Alembic" and r["grade"] == "Master")
    assert master["id"] == "0006EE64"
    assert master["strength"] == 1.0
    assert master["cost"] == 1000

@pytest.mark.skipif(not _RAW_JSON.exists(), reason="raw JSON not present")
def test_integration_mortar_six_rows():
    with open(_RAW_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    records = parse_apparatus(raw["html"])
    mortars = [r for r in records if r["name"] == "Mortar & Pestle"]
    assert len(mortars) == 6
