"""Unit tests for morrowind_parse_souls.py"""
import json
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Morrowind" / "enchanting" / "souls_json"))
from morrowind_parse_souls import parse_souls

MINIMAL_HTML = """
<div class="mw-parser-output">
<div style="display:inline-table">
<table class="vtop wikitable">
<tr><th colspan="3">Petty Soul Gem<br/><p>Max Soul strength: 30</p></th></tr>
<tr>
  <th>5</th>
  <td><ul><li>Mudcrab</li><li>Diseased Mudcrab</li></ul></td>
  <td><ul><li>Old Blue Fin</li></ul></td>
</tr>
<tr>
  <th>10</th>
  <td colspan="2"><ul><li>Scamp</li><li>Rat</li></ul></td>
</tr>
</table>
</div>
<div style="display:inline-table">
<table class="vtop wikitable">
<tr><th colspan="3">Greater Soul Gem<br/><p>Max Soul strength: 180</p></th></tr>
<tr>
  <th>100</th>
  <td><ul><li>Scamp</li></ul></td>
  <td><ul><li>Ancestor Ghost</li></ul></td>
</tr>
<tr>
  <th>1000</th>
  <td colspan="2"><ul><li>Vivec</li></ul></td>
</tr>
</table>
</div>
</div>
"""


def test_basic_extraction():
    records = parse_souls(MINIMAL_HTML)
    names = [r["name"] for r in records]
    assert "Mudcrab" in names
    assert "Old Blue Fin" in names
    assert "Scamp" in names


def test_correct_soul_sizes():
    records = parse_souls(MINIMAL_HTML)
    by_name = {r["name"]: r["soul_size"] for r in records}
    assert by_name["Mudcrab"] == 5
    assert by_name["Diseased Mudcrab"] == 5
    assert by_name["Old Blue Fin"] == 5
    assert by_name["Rat"] == 10
    assert by_name["Vivec"] == 1000


def test_colspan_headers_skipped():
    records = parse_souls(MINIMAL_HTML)
    names = [r["name"] for r in records]
    assert "Petty Soul Gem" not in names
    assert "Greater Soul Gem" not in names
    assert "Max Soul strength" not in names


def test_multiple_td_columns_per_row():
    records = parse_souls(MINIMAL_HTML)
    names_at_5 = [r["name"] for r in records if r["soul_size"] == 5]
    assert "Mudcrab" in names_at_5
    assert "Old Blue Fin" in names_at_5


def test_same_creature_multiple_sizes():
    records = parse_souls(MINIMAL_HTML)
    scamp_sizes = {r["soul_size"] for r in records if r["name"] == "Scamp"}
    assert scamp_sizes == {10, 100}


def test_deduplication():
    dupe_html = """
    <div class="mw-parser-output">
    <table class="wikitable">
    <tr><th>5</th><td><ul><li>Mudcrab</li></ul></td></tr>
    <tr><th>5</th><td><ul><li>Mudcrab</li></ul></td></tr>
    </table>
    </div>
    """
    records = parse_souls(dupe_html)
    mudcrab_rows = [r for r in records if r["name"] == "Mudcrab"]
    assert len(mudcrab_rows) == 1


def test_soul_size_is_integer():
    records = parse_souls(MINIMAL_HTML)
    for r in records:
        assert isinstance(r["soul_size"], int)


def test_two_tables_both_parsed():
    records = parse_souls(MINIMAL_HTML)
    sizes = {r["soul_size"] for r in records}
    assert 5 in sizes
    assert 100 in sizes
    assert 1000 in sizes


def test_returns_list_of_dicts():
    records = parse_souls(MINIMAL_HTML)
    assert isinstance(records, list)
    assert all("name" in r and "soul_size" in r for r in records)


def test_empty_html_returns_empty():
    records = parse_souls("<div></div>")
    assert records == []
