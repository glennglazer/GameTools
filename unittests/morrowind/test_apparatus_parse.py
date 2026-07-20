"""Tests for TES/Morrowind/alchemy/apparatus_json/morrowind_parse_apparatus.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

_mod = load_module(
    "TES/Morrowind/alchemy/apparatus_json/morrowind_parse_apparatus.py",
    "mw_apparatus_parse",
)
parse_apparatus = _mod.parse_apparatus

# ---------------------------------------------------------------------------
# Synthetic HTML fixtures
# ---------------------------------------------------------------------------

# Standard data row (Apprentice's Mortar and Pestle)
SIMPLE_ROW = """
<table class="wikitable">
<tr><th colspan="2">Object ID</th><th>Name</th><th>Type</th><th>W</th><th>V</th><th>Q</th><th>Count</th></tr>
<tr class="OBMagicRes">
  <td><img alt="img"/></td>
  <td>apparatus_a_mortar_01</td>
  <td><span id="Apprentice.27s_Mortar_and_Pestle"></span>Apprentice's Mortar and Pestle</td>
  <td>Mortar/Pestle</td>
  <td>5</td><td>100</td><td>0.5</td><td>65</td>
</tr>
<tr><td colspan="8"><div class="mw-collapsible mw-collapsed">Locations...</div></td></tr>
</table>
"""

# Secret Master row with decorated span on "Pestl" (intentional game typo)
SECRET_MASTER_ROW = """
<table class="wikitable">
<tr><th colspan="2">Object ID</th><th>Name</th><th>Type</th><th>W</th><th>V</th><th>Q</th><th>Count</th></tr>
<tr class="MWMagicMys">
  <td><img/></td>
  <td>apparatus_sm_mortar_01</td>
  <td><span id="SecretMaster.27s_Mortar_and_Pestl"></span>SecretMaster's Mortar and
      <span style="border-bottom:1px dotted" title="intentional">Pestl</span></td>
  <td>Mortar/Pestle</td>
  <td>1</td><td>6000</td><td>2</td><td>2</td>
</tr>
<tr><td colspan="8"></td></tr>
</table>
"""

# Multiple rows including one location row (to verify skipping)
MULTI_ROW = """
<table class="wikitable">
<tr><th colspan="2">Object ID</th><th>Name</th><th>Type</th><th>W</th><th>V</th><th>Q</th><th>Count</th></tr>
<tr class="OBMagicRes">
  <td><img/></td><td>apparatus_a_mortar_01</td>
  <td><span id="x"></span>Apprentice's Mortar and Pestle</td>
  <td>Mortar/Pestle</td><td>5</td><td>100</td><td>0.5</td><td>65</td>
</tr>
<tr><td colspan="8"><div class="mw-collapsible">Balmora, shop</div></td></tr>
<tr class="OBMagicRes">
  <td><img/></td><td>apparatus_a_alembic_01</td>
  <td><span id="x"></span>Apprentice's Alembic</td>
  <td>Alembic</td><td>10</td><td>50</td><td>0.5</td><td>28</td>
</tr>
<tr><td colspan="8"><div class="mw-collapsible">Sadrith Mora</div></td></tr>
</table>
"""

# Skooma Pipe row
SKOOMA_ROW = """
<table class="wikitable">
<tr><th colspan="2">Object ID</th><th>Name</th><th>Type</th><th>W</th><th>V</th><th>Q</th><th>Count</th></tr>
<tr class="RaceErr">
  <td><img/></td>
  <td>apparatus_a_spipe_01</td>
  <td><span id="Good_Skooma_Pipe"></span>Good Skooma Pipe</td>
  <td>Mortar/Pestle</td>
  <td>2</td><td>50</td><td>0.15</td><td>3</td>
</tr>
<tr><td colspan="8"></td></tr>
</table>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parses_single_record():
    records = parse_apparatus(SIMPLE_ROW)
    assert len(records) == 1

def test_record_fields_present():
    r = parse_apparatus(SIMPLE_ROW)[0]
    assert set(r.keys()) == {"id", "name", "weight", "value", "quality"}

def test_parses_id():
    r = parse_apparatus(SIMPLE_ROW)[0]
    assert r["id"] == "apparatus_a_mortar_01"

def test_parses_name():
    r = parse_apparatus(SIMPLE_ROW)[0]
    assert r["name"] == "Apprentice's Mortar and Pestle"

def test_parses_weight_as_float():
    r = parse_apparatus(SIMPLE_ROW)[0]
    assert r["weight"] == 5.0
    assert isinstance(r["weight"], float)

def test_parses_value_as_int():
    r = parse_apparatus(SIMPLE_ROW)[0]
    assert r["value"] == 100
    assert isinstance(r["value"], int)

def test_parses_quality_as_float():
    r = parse_apparatus(SIMPLE_ROW)[0]
    assert r["quality"] == 0.5
    assert isinstance(r["quality"], float)

def test_skips_location_rows():
    records = parse_apparatus(MULTI_ROW)
    assert len(records) == 2

def test_parses_multiple_rows():
    records = parse_apparatus(MULTI_ROW)
    ids = [r["id"] for r in records]
    assert "apparatus_a_mortar_01" in ids
    assert "apparatus_a_alembic_01" in ids

def test_no_type_or_count_in_records():
    r = parse_apparatus(SIMPLE_ROW)[0]
    assert "type" not in r
    assert "count" not in r

def test_secret_master_name_normalised():
    r = parse_apparatus(SECRET_MASTER_ROW)[0]
    assert r["name"] == "SecretMaster's Mortar and Pestl"

def test_secret_master_quality():
    r = parse_apparatus(SECRET_MASTER_ROW)[0]
    assert r["quality"] == 2.0

def test_skooma_pipe_included():
    records = parse_apparatus(SKOOMA_ROW)
    assert len(records) == 1
    assert records[0]["id"] == "apparatus_a_spipe_01"
    assert records[0]["quality"] == 0.15

def test_empty_table_returns_empty_list():
    html = '<table class="wikitable"><tr><th>H1</th></tr></table>'
    assert parse_apparatus(html) == []

def test_raises_on_missing_table():
    with pytest.raises(ValueError, match="No wikitable"):
        parse_apparatus("<div>no table here</div>")


# ---------------------------------------------------------------------------
# Integration test against real raw JSON
# ---------------------------------------------------------------------------

_RAW_JSON = REPO_ROOT / "TES/Morrowind/alchemy/apparatus_parse/morrowind_apparatus_raw.json"

@pytest.mark.skipif(not _RAW_JSON.exists(), reason="raw JSON not present")
def test_integration_record_count():
    with open(_RAW_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    records = parse_apparatus(raw["html"])
    assert len(records) == 22  # 5 grades × 4 types + 2 Skooma Pipes

@pytest.mark.skipif(not _RAW_JSON.exists(), reason="raw JSON not present")
def test_integration_all_have_required_fields():
    with open(_RAW_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    records = parse_apparatus(raw["html"])
    for r in records:
        assert "id" in r and r["id"]
        assert "name" in r and r["name"]
        assert isinstance(r["weight"], float)
        assert isinstance(r["value"], int)
        assert isinstance(r["quality"], float)

@pytest.mark.skipif(not _RAW_JSON.exists(), reason="raw JSON not present")
def test_integration_grandmaster_quality():
    with open(_RAW_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    records = parse_apparatus(raw["html"])
    gm = next(r for r in records if r["id"] == "apparatus_g_mortar_01")
    assert gm["quality"] == 1.5
    assert gm["value"] == 4000
