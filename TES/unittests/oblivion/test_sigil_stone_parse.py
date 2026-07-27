"""Unit tests for oblivion_parse_sigil_stone.py"""
import json
import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent /
                       "TES" / "Oblivion" / "enchanting" / "sigil_stone_json"))
from oblivion_parse_sigil_stone import parse, LEVELS

# Minimal HTML with one stone group: Absorb Agility / Fortify Agility
SIMPLE_HTML = """
<div class="mw-parser-output">
<table class="wikitable" style="text-align:center; width:100%">
<tbody>
<tr>
<th>Effect</th>
<th colspan="2">Descendent <small>(Form ID)</small></th>
<th colspan="2">Subjacent <small>(Form ID)</small></th>
<th colspan="2">Latent <small>(Form ID)</small></th>
<th colspan="2">Ascendent <small>(Form ID)</small></th>
<th colspan="2">Transcendent <small>(Form ID)</small></th>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Absorb_Agility">Absorb Agility</a>, 30 secs</td>
<td>5 pts<br /><small>(880/22=40)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB1</span></span>)</span></td>
<td>10 pts<br /><small>(1890/54=35)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB2</span></span>)</span></td>
<td>15 pts<br /><small>(2730/91=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB3</span></span>)</span></td>
<td>20 pts<br /><small>(3930/131=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB4</span></span>)</span></td>
<td>25 pts<br /><small>(5250/175=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB5</span></span>)</span></td>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Fortify_Agility">Fortify Agility</a></td>
<td>7 pts</td>
<td>8 pts</td>
<td>9 pts</td>
<td>10 pts</td>
<td>12 pts</td>
</tr>
</tbody>
</table>
</div>
"""

# HTML with Demoralize (level-based weapon magnitude)
DEMORALIZE_HTML = """
<div class="mw-parser-output">
<table class="wikitable">
<tbody>
<tr>
<th>Effect</th>
<th colspan="2">Descendent <small>(Form ID)</small></th>
<th colspan="2">Subjacent <small>(Form ID)</small></th>
<th colspan="2">Latent <small>(Form ID)</small></th>
<th colspan="2">Ascendent <small>(Form ID)</small></th>
<th colspan="2">Transcendent <small>(Form ID)</small></th>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Demoralize">Demoralize</a>**, 20 secs</td>
<td>level 2<br />(=10 pts)<br /><small>(810/18=45)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">04200B</span></span>)</span></td>
<td>level 5<br />(=20 pts)<br /><small>(1575/45=35)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">04200C</span></span>)</span></td>
<td>level 7<br />(=30 pts)<br /><small>(2660/76=35)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">04200D</span></span>)</span></td>
<td>level 10<br />(=40 pts)<br /><small>(3300/110=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">04200E</span></span>)</span></td>
<td>level 12<br />(=50 pts)<br /><small>(4380/146=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">04200F</span></span>)</span></td>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Fortify_Willpower">Fortify Willpower</a></td>
<td>7 pts</td>
<td>8 pts</td>
<td>9 pts</td>
<td>10 pts</td>
<td>12 pts</td>
</tr>
</tbody>
</table>
</div>
"""

# HTML with Night-Eye (NULL armor magnitudes)
NIGHT_EYE_HTML = """
<div class="mw-parser-output">
<table class="wikitable">
<tbody>
<tr>
<th>Effect</th>
<th colspan="2">Descendent <small>(Form ID)</small></th>
<th colspan="2">Subjacent <small>(Form ID)</small></th>
<th colspan="2">Latent <small>(Form ID)</small></th>
<th colspan="2">Ascendent <small>(Form ID)</small></th>
<th colspan="2">Transcendent <small>(Form ID)</small></th>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Shock_Damage">Shock Damage</a></td>
<td>5 pts<br /><small>(480/6=80)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">042083</span></span>)</span></td>
<td>10 pts<br /><small>(1120/14=80)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">042084</span></span>)</span></td>
<td>15 pts<br /><small>(1920/24=80)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">042085</span></span>)</span></td>
<td>20 pts<br /><small>(2770/36=75)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">042086</span></span>)</span></td>
<td>25 pts<br /><small>(3360/48=70)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">042087</span></span>)</span></td>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Night-Eye">Night-Eye</a></td>
<td>-</td>
<td>-</td>
<td>-</td>
<td>-</td>
<td>-</td>
</tr>
</tbody>
</table>
</div>
"""

# HTML with a repeated header row (should be skipped)
REPEATED_HEADER_HTML = """
<div class="mw-parser-output">
<table class="wikitable">
<tbody>
<tr>
<th>Effect</th>
<th colspan="2">Descendent <small>(Form ID)</small></th>
<th colspan="2">Subjacent <small>(Form ID)</small></th>
<th colspan="2">Latent <small>(Form ID)</small></th>
<th colspan="2">Ascendent <small>(Form ID)</small></th>
<th colspan="2">Transcendent <small>(Form ID)</small></th>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Absorb_Agility">Absorb Agility</a></td>
<td>5 pts<br /><small>(880/22=40)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB1</span></span>)</span></td>
<td>10 pts<br /><small>(1890/54=35)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB2</span></span>)</span></td>
<td>15 pts<br /><small>(2730/91=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB3</span></span>)</span></td>
<td>20 pts<br /><small>(3930/131=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB4</span></span>)</span></td>
<td>25 pts<br /><small>(5250/175=30)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FB5</span></span>)</span></td>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Fortify_Agility">Fortify Agility</a></td>
<td>7 pts</td>
<td>8 pts</td>
<td>9 pts</td>
<td>10 pts</td>
<td>12 pts</td>
</tr>
<tr>
<th>Effect</th>
<th colspan="2">Descendent <small>(Form ID)</small></th>
<th colspan="2">Subjacent <small>(Form ID)</small></th>
<th colspan="2">Latent <small>(Form ID)</small></th>
<th colspan="2">Ascendent <small>(Form ID)</small></th>
<th colspan="2">Transcendent <small>(Form ID)</small></th>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Burden">Burden</a>, 30 secs</td>
<td>20 pts<br /><small>(1305/29=45)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FD5</span></span>)</span></td>
<td>40 pts<br /><small>(2800/70=40)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FD6</span></span>)</span></td>
<td>60 pts<br /><small>(4130/118=35)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FD7</span></span>)</span></td>
<td>80 pts<br /><small>(5985/171=35)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FD8</span></span>)</span></td>
<td>100 pts<br /><small>(7980/228=35)</small></td>
<td rowspan="2"><span class="idall">(<span class="idref">00<span class="idcase">041FD9</span></span>)</span></td>
</tr>
<tr>
<td><a href="/wiki/Oblivion:Feather">Feather</a></td>
<td>25 pts</td>
<td>50 pts</td>
<td>75 pts</td>
<td>100 pts</td>
<td>125 pts</td>
</tr>
</tbody>
</table>
</div>
"""


def test_parse_returns_three_lists():
    stones, wmags, amags = parse(SIMPLE_HTML)
    assert isinstance(stones, list)
    assert isinstance(wmags, list)
    assert isinstance(amags, list)


def test_one_group_produces_five_records():
    stones, wmags, amags = parse(SIMPLE_HTML)
    assert len(stones) == 5
    assert len(wmags) == 5
    assert len(amags) == 5


def test_stone_effects_set_correctly():
    stones, _, _ = parse(SIMPLE_HTML)
    for s in stones:
        assert s["weapon_effect"] == "Absorb Agility"
        assert s["armor_effect"] == "Fortify Agility"


def test_form_ids_are_uppercase_hex():
    stones, _, _ = parse(SIMPLE_HTML)
    expected = ["00041FB1", "00041FB2", "00041FB3", "00041FB4", "00041FB5"]
    assert [s["form_id"] for s in stones] == expected


def test_weapon_magnitude_regular():
    _, wmags, _ = parse(SIMPLE_HTML)
    # Descendent: 5 pts, 40 uses
    desc = next(w for w in wmags if w["descendent_magnitude"] is not None)
    assert desc["descendent_magnitude"] == 5
    assert desc["descendent_charges"] == 40
    # Transcendent: 25 pts, 30 uses
    trans = next(w for w in wmags if w["transcendent_magnitude"] is not None)
    assert trans["transcendent_magnitude"] == 25
    assert trans["transcendent_charges"] == 30


def test_weapon_only_one_level_populated_per_row():
    _, wmags, _ = parse(SIMPLE_HTML)
    for row in wmags:
        populated = [lv for lv in LEVELS if row[f"{lv}_magnitude"] is not None]
        assert len(populated) == 1


def test_armor_only_one_level_populated_per_row():
    _, _, amags = parse(SIMPLE_HTML)
    for row in amags:
        populated = [lv for lv in LEVELS if row[f"{lv}_magnitude"] is not None]
        assert len(populated) == 1


def test_armor_magnitudes_correct():
    _, _, amags = parse(SIMPLE_HTML)
    desc_row = next(a for a in amags if a["descendent_magnitude"] is not None)
    assert desc_row["descendent_magnitude"] == 7
    trans_row = next(a for a in amags if a["transcendent_magnitude"] is not None)
    assert trans_row["transcendent_magnitude"] == 12


def test_demoralize_uses_level_not_pts():
    stones, wmags, _ = parse(DEMORALIZE_HTML)
    assert stones[0]["weapon_effect"] == "Demoralize"
    desc = next(w for w in wmags if w["descendent_magnitude"] is not None)
    assert desc["descendent_magnitude"] == 2   # level 2, not 10 pts
    assert desc["descendent_charges"] == 45
    trans = next(w for w in wmags if w["transcendent_magnitude"] is not None)
    assert trans["transcendent_magnitude"] == 12  # level 12, not 50 pts


def test_night_eye_armor_all_null():
    _, _, amags = parse(NIGHT_EYE_HTML)
    for row in amags:
        for lv in LEVELS:
            assert row[f"{lv}_magnitude"] is None


def test_weapon_magnitude_not_null_when_armor_is_null():
    _, wmags, _ = parse(NIGHT_EYE_HTML)
    desc = next(w for w in wmags if w["descendent_magnitude"] is not None)
    assert desc["descendent_magnitude"] == 5   # Shock Damage descendent
    assert desc["descendent_charges"] == 80


def test_repeated_header_rows_skipped():
    stones, _, _ = parse(REPEATED_HEADER_HTML)
    assert len(stones) == 10  # two groups × 5 levels


def test_effect_name_strips_duration_suffix():
    stones, _, _ = parse(SIMPLE_HTML)
    # "Absorb Agility, 30 secs" → "Absorb Agility"
    assert stones[0]["weapon_effect"] == "Absorb Agility"


def test_effect_name_strips_footnote_marker():
    stones, _, _ = parse(DEMORALIZE_HTML)
    # "Demoralize**" → "Demoralize"
    assert stones[0]["weapon_effect"] == "Demoralize"


def test_all_form_ids_unique_in_group():
    stones, _, _ = parse(SIMPLE_HTML)
    ids = [s["form_id"] for s in stones]
    assert len(ids) == len(set(ids))


def test_no_wikitable_raises():
    with pytest.raises(ValueError, match="No wikitable"):
        parse("<div><p>No table here</p></div>")


def test_charges_uses_final_equals_value():
    """Charges should be the '=N' at the end of the formula string, not any intermediate '='."""
    _, wmags, _ = parse(SIMPLE_HTML)
    # (880/22=40) → charges=40 (not 22 or 880)
    desc = next(w for w in wmags if w["descendent_magnitude"] is not None)
    assert desc["descendent_charges"] == 40
