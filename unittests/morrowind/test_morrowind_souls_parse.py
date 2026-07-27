"""Unit tests for morrowind_parse_souls.py"""
import json
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Morrowind" / "enchanting" / "souls_json"))
from morrowind_parse_souls import parse_souls, parse

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


# --- Footnote stripping ---

FOOTNOTE_HTML = """
<div class="mw-parser-output">
<table class="wikitable">
<tr>
  <th>10</th>
  <td><ul>
    <li><a href="#">Rat</a> <sup class="reference"><a href="#">&#91;1&#93;</a></sup></li>
    <li><a href="#">Scrib</a> <sup class="reference"><a href="#">&#91;1&#93;</a></sup></li>
    <li><a href="#">Verminous Fabricant</a> <sup class="reference"><a href="#">&#91;2&#93;</a></sup></li>
    <li><a href="#">Clean Name</a></li>
  </ul></td>
</tr>
</table>
</div>
"""


def test_footnote_refs_stripped():
    records = parse_souls(FOOTNOTE_HTML)
    names = [r["name"] for r in records]
    assert "Rat" in names
    assert "Scrib" in names
    assert "Verminous Fabricant" in names
    assert "Clean Name" in names
    assert not any("[" in n for n in names)


# --- Multi-page parse() ---

TRIBUNAL_HTML = """
<div class="mw-parser-output">
<table class="wikitable">
<tr><th colspan="2">Petty Soul Gem</th></tr>
<tr>
  <th>10</th>
  <td><ul><li>Diseased Durzog</li><li>Rat</li></ul></td>
</tr>
</table>
<table class="wikitable">
<tr><th colspan="2">Grand Soul Gem</th></tr>
<tr>
  <th>1500</th>
  <td><ul><li>Almalexia</li></ul></td>
</tr>
</table>
</div>
"""

MULTI_PAGE_DATA = {
    "pages": [
        {"page": "Morrowind:Souls", "section": "0", "html": MINIMAL_HTML},
        {"page": "Tribunal:Souls",  "section": "0", "html": TRIBUNAL_HTML},
    ]
}


def test_parse_combines_pages():
    records = parse(MULTI_PAGE_DATA)
    names = [r["name"] for r in records]
    assert "Mudcrab" in names       # from Morrowind
    assert "Almalexia" in names     # from Tribunal
    assert "Diseased Durzog" in names


def test_parse_deduplicates_across_pages():
    """Rat appears in both pages at size 10; should appear only once."""
    records = parse(MULTI_PAGE_DATA)
    rat_rows = [r for r in records if r["name"] == "Rat" and r["soul_size"] == 10]
    assert len(rat_rows) == 1


def test_parse_tribunal_soul_size():
    records = parse(MULTI_PAGE_DATA)
    almalexia = next(r for r in records if r["name"] == "Almalexia")
    assert almalexia["soul_size"] == 1500


def test_parse_backward_compat_single_page():
    """parse() must still work when given the old single-page dict format."""
    data = {"page": "Morrowind:Souls", "section": "0", "html": MINIMAL_HTML}
    records = parse(data)
    assert any(r["name"] == "Mudcrab" for r in records)


# --- Bloodmoon souls ---

BLOODMOON_HTML = """
<div class="mw-parser-output">
<div style="display:inline-table">
<table class="vtop wikitable">
<tr><th colspan="3">Petty Soul Gem<br/><p>Max Soul strength: 30</p></th></tr>
<tr>
  <th>20</th>
  <td colspan="2"><ul>
    <li><a href="#">Werewolf</a> <sup class="reference"><a href="#">&#91;1&#93;</a></sup></li>
  </ul></td>
</tr>
<tr><th colspan="3">Lesser Soul Gem<br/><p>Max Soul strength: 60</p></th></tr>
<tr>
  <th>50</th>
  <td><ul>
    <li><a href="#">Grizzly Bear</a> <sup class="reference"><a href="#">&#91;3&#93;</a></sup></li>
    <li><a href="#">Snow Wolf</a></li>
  </ul></td>
  <td><ul>
    <li><a href="#">Wolf</a></li>
  </ul></td>
</tr>
</table>
</div>
<div style="display:inline-table">
<table class="vtop wikitable">
<tr><th colspan="3">Common Soul Gem<br/><p>Max Soul strength: 120</p></th></tr>
<tr>
  <th>100</th>
  <td><ul>
    <li><a href="#">Grizzly Bear</a></li>
    <li><a href="#">Karstaag</a></li>
  </ul></td>
  <td><ul>
    <li><a href="#">Riekling</a></li>
  </ul></td>
</tr>
<tr><th colspan="3">Grand Soul Gem<br/><p>Max Soul strength: 600</p></th></tr>
<tr>
  <th>350</th>
  <td colspan="2"><ul>
    <li><a href="#">Spriggan</a></li>
  </ul></td>
</tr>
</table>
</div>
</div>
"""

THREE_PAGE_DATA = {
    "pages": [
        {"page": "Morrowind:Souls", "section": "0", "html": MINIMAL_HTML},
        {"page": "Tribunal:Souls",  "section": "0", "html": TRIBUNAL_HTML},
        {"page": "Bloodmoon:Souls", "section": "0", "html": BLOODMOON_HTML},
    ]
}


def test_parse_combines_bloodmoon_page():
    records = parse(THREE_PAGE_DATA)
    names = [r["name"] for r in records]
    assert "Mudcrab" in names       # from Morrowind
    assert "Almalexia" in names     # from Tribunal
    assert "Spriggan" in names      # from Bloodmoon
    assert "Karstaag" in names      # from Bloodmoon


def test_parse_bloodmoon_grizzly_bear_two_sizes():
    """Grizzly Bear appears at size 50 and 100 in Bloodmoon — both are distinct entries."""
    records = parse(THREE_PAGE_DATA)
    grizzly_sizes = {r["soul_size"] for r in records if r["name"] == "Grizzly Bear"}
    assert grizzly_sizes == {50, 100}


def test_parse_bloodmoon_footnote_stripped():
    """Werewolf has a footnote in Bloodmoon HTML; name must be clean."""
    records = parse(THREE_PAGE_DATA)
    names = [r["name"] for r in records]
    assert "Werewolf" in names
    assert not any("[" in n for n in names)
