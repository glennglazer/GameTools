"""Unit tests for oblivion_parse_enchant_effects.py"""
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                       "TES" / "Oblivion" / "enchanting" / "enchant_effects_json"))
from oblivion_parse_enchant_effects import parse_section, parse

# Minimal Alteration table HTML (2 rows)
ALTERATION_HTML = """
<div class="mw-parser-output">
<table class="wikitable sortable">
<tbody>
<tr>
<th>Effect Name</th><th>Effect ID</th><th>Base Cost</th><th>Barter Factor</th><th>Description</th>
</tr>
<tr>
<th scope="row"><a href="/wiki/Oblivion:Burden">Burden</a></th>
<td>BRDN</td><td>0.21</td><td>0</td>
<td>Reduce the target's maximum <a href="/wiki/Oblivion:Encumbrance">encumbrance</a>.</td>
</tr>
<tr>
<th scope="row"><a href="/wiki/Oblivion:Feather">Feather</a></th>
<td>FTHR</td><td>0.01</td><td>25</td>
<td>Increase the target's maximum encumbrance.</td>
</tr>
</tbody>
</table>
</div>
"""

# Illusion HTML with fractional barter_factor and long description
ILLUSION_HTML = """
<div class="mw-parser-output">
<table class="wikitable sortable">
<tbody>
<tr>
<th>Effect Name</th><th>Effect ID</th><th>Base Cost</th><th>Barter Factor</th><th>Description</th>
</tr>
<tr>
<th scope="row"><a href="/wiki/Oblivion:Light">Light</a></th>
<td>LGHT</td><td>0.051</td><td>12.5</td>
<td>Illuminates the target.</td>
</tr>
<tr>
<th scope="row"><a href="/wiki/Oblivion:Paralyze">Paralyze</a></th>
<td>PARA</td><td>475</td><td>0</td>
<td>Render target unable to move.</td>
</tr>
<tr>
<th scope="row"><a href="/wiki/Oblivion:Charm">Charm</a></th>
<td>CHRM</td><td>0.2</td><td>0</td>
<td>Increase target's <a href="/wiki/Oblivion:Disposition">disposition</a>.</td>
</tr>
</tbody>
</table>
</div>
"""

MULTI_SECTION_DATA = {
    "page": "Oblivion:Spell_Effects",
    "sections": {
        "1": {"school": "Alteration", "html": ALTERATION_HTML},
        "4": {"school": "Illusion",   "html": ILLUSION_HTML},
    }
}


def test_parse_section_returns_list():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert isinstance(records, list)


def test_parse_section_count():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert len(records) == 2


def test_effect_id_extracted():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert records[0]["effect_id"] == "BRDN"
    assert records[1]["effect_id"] == "FTHR"


def test_base_cost_is_float():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert isinstance(records[0]["base_cost"], float)
    assert records[0]["base_cost"] == pytest.approx(0.21)


def test_barter_factor_is_float():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert isinstance(records[0]["barter_factor"], float)
    assert records[0]["barter_factor"] == pytest.approx(0.0)
    assert records[1]["barter_factor"] == pytest.approx(25.0)


def test_fractional_barter_factor():
    records = parse_section(ILLUSION_HTML, "Illusion")
    lght = next(r for r in records if r["effect_id"] == "LGHT")
    assert lght["barter_factor"] == pytest.approx(12.5)


def test_integer_looking_base_cost():
    records = parse_section(ILLUSION_HTML, "Illusion")
    para = next(r for r in records if r["effect_id"] == "PARA")
    assert para["base_cost"] == pytest.approx(475.0)


def test_school_set_correctly():
    records = parse_section(ALTERATION_HTML, "Alteration")
    for r in records:
        assert r["school"] == "Alteration"


def test_description_extracted():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert "encumbrance" in records[0]["description"]


def test_description_no_space_before_period():
    records = parse_section(ALTERATION_HTML, "Alteration")
    # "encumbrance ." should become "encumbrance."
    assert " ." not in records[0]["description"]
    assert records[0]["description"].endswith("encumbrance.")


def test_description_inline_link_words_joined():
    """Inline links should produce space-separated words, not concatenated."""
    records = parse_section(ILLUSION_HTML, "Illusion")
    chrm = next(r for r in records if r["effect_id"] == "CHRM")
    assert "disposition" in chrm["description"]
    assert "disposition." in chrm["description"]  # word + period, no space before period


def test_record_keys():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert set(records[0].keys()) == {"name", "effect_id", "base_cost", "barter_factor", "school", "description"}


def test_name_extracted():
    records = parse_section(ALTERATION_HTML, "Alteration")
    assert records[0]["name"] == "Burden"
    assert records[1]["name"] == "Feather"


def test_name_multiword():
    """Effects with multi-word names (via links in th) are joined with a space."""
    records = parse_section(ILLUSION_HTML, "Illusion")
    chrm = next(r for r in records if r["effect_id"] == "CHRM")
    assert chrm["name"] == "Charm"


def test_name_not_header():
    records = parse_section(ALTERATION_HTML, "Alteration")
    names = [r["name"] for r in records]
    assert "Effect Name" not in names


def test_parse_combines_all_sections():
    records = parse(MULTI_SECTION_DATA)
    assert len(records) == 5  # 2 Alteration + 3 Illusion


def test_parse_schools_present():
    records = parse(MULTI_SECTION_DATA)
    schools = {r["school"] for r in records}
    assert schools == {"Alteration", "Illusion"}


def test_no_wikitable_raises():
    with pytest.raises(ValueError, match="No wikitable"):
        parse_section("<div><p>No table here</p></div>", "Alteration")


def test_header_rows_excluded():
    records = parse_section(ALTERATION_HTML, "Alteration")
    # No record should have effect_id "Effect ID" (the header text)
    ids = [r["effect_id"] for r in records]
    assert "Effect ID" not in ids
    assert "Effect Name" not in ids
