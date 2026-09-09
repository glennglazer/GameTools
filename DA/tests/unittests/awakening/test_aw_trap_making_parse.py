"""Unit tests for DA/Awakening/trap_making/trap_making_json/awakening_parse_trap_making.py"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

parser = load_module(
    "DA/Awakening/trap_making/trap_making_json/awakening_parse_trap_making.py",
    "awakening_parse_trap_making",
)

strip_wiki_link = parser.strip_wiki_link
normalize_ingredient_name = parser.normalize_ingredient_name
get_field = parser.get_field
parse_recipe = parser.parse_recipe
_parse_elemental_trap = parser._parse_elemental_trap
parse_awakening_trap_effects = parser.parse_awakening_trap_effects


# ─── RecipeTransformer wikitext fixtures ──────────────────────────────────────

_DISPEL_TRAP = """\
<onlyinclude>{{RecipeTransformer
|name=[[Dispel Trap Plans]]
|ingredient1=[[Rashvine Nettle]]
|quantity1=1
|ingredient2=[[Corrupter Agent]]
|quantity2=2
|ingredient3=[[Trap Trigger]]
|quantity3=1
|ingredient4=[[Concentrator Agent]]
|quantity4=1
|result=[[Dispel Trap]]
|requires=[[Trap-Making#Tiers|Trap-Making: Rank 4]]
|item_id=gxa_im_cft_trp_401
}}</onlyinclude>
"""

_ELEMENTAL_TRAP = """\
<onlyinclude>{{RecipeTransformer
|name=[[Elemental Trap Plans]]
|ingredient1=[[Blood Lotus (Origins)]]
|quantity1=1
|ingredient2=[[Corrupter Agent]]
|quantity2=2
|ingredient3=[[Trap Trigger]]
|quantity3=1
|ingredient4=[[Concentrator Agent]]
|quantity4=1
|result=[[Elemental Trap]]
|requires=[[Trap-Making#Tiers|Trap-Making: Rank 4]]
|item_id=gxa_im_cft_trp_402
}}</onlyinclude>
"""

_GRAVITY_TRAP = """\
<onlyinclude>{{RecipeTransformer
|name=[[Gravity Trap Plans]]
|ingredient1=[[Glamour Charm]]
|quantity1=4
|ingredient2=[[Corrupter Agent]]
|quantity2=4
|ingredient3=[[Trap Trigger]]
|quantity3=1
|result=[[Gravity Trap]]
|requires=[[Trap-Making#Tiers|Trap-Making: Rank 4]]
|item_id=gxa_im_cft_trp_403
}}</onlyinclude>
"""

# ─── Traps wikitext fixture (both DAO and Awakening daotables) ────────────────

_TRAPS_WIKITEXT = """\
== Traps ==
{| class="daotable"
|-
! width="25%" | Tier One Traps
! width="25%" | Damage per hit
! Effect
|-
|[[Small Caltrop Trap]] || 8 physical damage every 2 seconds ||-40% movement speed
|-
|[[Spring Trap]] || || Knocks down the target
|}

{| class="daotable"
|-
! width="25%" | Tier Four Traps (Awakening)
! width="25%" | Damage per hit
! Effect
|-
| [[Dispel Trap]] || || When triggered, this trap dispels all magical effects within a large area.<br/>Friendly fire possible.
|-
| [[Elemental Trap]] || 200 || When triggered, this trap explodes with the force of the elements, dealing 40 cold, fire, electricity, nature, and spirit damage (total: 200) to everyone within a large area.<br/>Friendly fire possible.
|-
| [[Gravity Trap]] || || When triggered, this trap pulses with waves that pull nearby creatures back to the trap every few seconds.<br/>Pulses every 4 seconds.<br/>20 second duration<br/>Friendly fire bugged and does not happen.
|-
| [[Misdirection Cloud Trap]] || || When triggered, this trap generates a cloud that causes creatures within to suffer from frustrating inaccuracy. All hits become misses, while critical hits become normal hits.<br/>20 second duration.<br/>Friendly fire bugged and does not happen.
|}
"""


# ─── strip_wiki_link ──────────────────────────────────────────────────────────

class TestStripWikiLink:
    def test_simple(self):
        assert strip_wiki_link("[[Dispel Trap]]") == "Dispel Trap"

    def test_piped(self):
        assert strip_wiki_link("[[Blood Lotus (Origins)|Blood Lotus]]") == "Blood Lotus"

    def test_anchor_pipe(self):
        assert strip_wiki_link("[[Trap-Making#Tiers|Trap-Making: Rank 4]]") == "Trap-Making: Rank 4"

    def test_none_returns_none(self):
        assert strip_wiki_link(None) is None

    def test_plain_text_unchanged(self):
        assert strip_wiki_link("Trap Trigger") == "Trap Trigger"


# ─── normalize_ingredient_name ────────────────────────────────────────────────

class TestNormalizeIngredientName:
    def test_strips_origins_suffix(self):
        assert normalize_ingredient_name("Blood Lotus (Origins)") == "Blood Lotus"

    def test_no_suffix_unchanged(self):
        assert normalize_ingredient_name("Trap Trigger") == "Trap Trigger"

    def test_strips_generic_suffix(self):
        assert normalize_ingredient_name("Deathroot (Dragon Age)") == "Deathroot"

    def test_empty_string(self):
        assert normalize_ingredient_name("") == ""


# ─── parse_recipe ─────────────────────────────────────────────────────────────

class TestParseRecipeName:
    def test_plan_name(self):
        rec = parse_recipe("Dispel Trap Plans", _DISPEL_TRAP)
        assert rec["name"] == "Dispel Trap Plans"

    def test_result_trap_name(self):
        rec = parse_recipe("Dispel Trap Plans", _DISPEL_TRAP)
        assert rec["result"] == "Dispel Trap"

    def test_gxa_item_id(self):
        rec = parse_recipe("Dispel Trap Plans", _DISPEL_TRAP)
        assert rec["item_id"] == "gxa_im_cft_trp_401"

    def test_gxa_item_id_elemental(self):
        rec = parse_recipe("Elemental Trap Plans", _ELEMENTAL_TRAP)
        assert rec["item_id"] == "gxa_im_cft_trp_402"


class TestParseRecipeTier:
    def test_all_awakening_tier_4(self):
        for wikitext, title in [
            (_DISPEL_TRAP, "Dispel Trap Plans"),
            (_ELEMENTAL_TRAP, "Elemental Trap Plans"),
            (_GRAVITY_TRAP, "Gravity Trap Plans"),
        ]:
            rec = parse_recipe(title, wikitext)
            assert rec["tier"] == 4


class TestParseRecipeIngredients:
    def test_four_ingredients_dispel(self):
        rec = parse_recipe("Dispel Trap Plans", _DISPEL_TRAP)
        assert rec["ingredient1"] == "Rashvine Nettle"
        assert rec["ingredient2"] == "Corrupter Agent"
        assert rec["ingredient3"] == "Trap Trigger"
        assert rec["ingredient4"] == "Concentrator Agent"

    def test_three_ingredients_gravity(self):
        rec = parse_recipe("Gravity Trap Plans", _GRAVITY_TRAP)
        assert rec["ingredient1"] == "Glamour Charm"
        assert rec["ingredient2"] == "Corrupter Agent"
        assert rec["ingredient3"] == "Trap Trigger"
        assert rec["ingredient4"] is None
        assert rec["quantity4"] is None

    def test_disambiguation_stripped(self):
        """[[Blood Lotus (Origins)]] should be stored as 'Blood Lotus'."""
        rec = parse_recipe("Elemental Trap Plans", _ELEMENTAL_TRAP)
        assert rec["ingredient1"] == "Blood Lotus"

    def test_quantities_dispel(self):
        rec = parse_recipe("Dispel Trap Plans", _DISPEL_TRAP)
        assert rec["quantity1"] == 1
        assert rec["quantity2"] == 2
        assert rec["quantity3"] == 1
        assert rec["quantity4"] == 1

    def test_quantities_gravity(self):
        rec = parse_recipe("Gravity Trap Plans", _GRAVITY_TRAP)
        assert rec["quantity1"] == 4
        assert rec["quantity2"] == 4


# ─── _parse_elemental_trap ────────────────────────────────────────────────────

class TestParseElementalTrap:
    def test_standard_text(self):
        effect = (
            "When triggered, this trap explodes with the force of the elements, "
            "dealing 40 cold, fire, electricity, nature, and spirit damage (total: 200) "
            "to everyone within a large area. Friendly fire possible."
        )
        result = _parse_elemental_trap(effect)
        assert result is not None
        damage_type, power = result
        assert power == 200
        assert damage_type == "cold, electricity, fire, nature, spirit"

    def test_types_sorted_alphabetically(self):
        effect = "dealing 10 spirit, nature, fire, electricity, cold damage (total: 50)"
        result = _parse_elemental_trap(effect)
        assert result is not None
        damage_type, _ = result
        assert damage_type == "cold, electricity, fire, nature, spirit"

    def test_non_elemental_returns_none(self):
        assert _parse_elemental_trap("") is None
        assert _parse_elemental_trap("When triggered, dispels all magic.") is None

    def test_only_total_power_captured(self):
        # Per-element damage (40) is not stored; only the total (200)
        effect = "dealing 40 cold, fire, electricity, nature, and spirit damage (total: 200)"
        result = _parse_elemental_trap(effect)
        assert result is not None
        _, power = result
        assert power == 200


# ─── parse_awakening_trap_effects ─────────────────────────────────────────────

class TestParseAwakeningTrapEffects:
    def setup_method(self):
        self.records = parse_awakening_trap_effects(_TRAPS_WIKITEXT)

    def test_total_count(self):
        """All 4 Awakening traps parsed."""
        assert len(self.records) == 4

    def test_dao_traps_excluded(self):
        """DAO traps from the first daotable must not appear."""
        names = {r["name"] for r in self.records}
        assert "Small Caltrop Trap" not in names
        assert "Spring Trap" not in names

    def test_sorted_by_name(self):
        names = [r["name"] for r in self.records]
        assert names == sorted(names)

    def test_elemental_trap_damage_type(self):
        r = next(r for r in self.records if r["name"] == "Elemental Trap")
        assert r["damage_type"] == "cold, electricity, fire, nature, spirit"

    def test_elemental_trap_power(self):
        r = next(r for r in self.records if r["name"] == "Elemental Trap")
        assert r["power"] == 200

    def test_elemental_trap_effect_null(self):
        r = next(r for r in self.records if r["name"] == "Elemental Trap")
        assert r["effect"] is None

    def test_dispel_trap_null_damage(self):
        r = next(r for r in self.records if r["name"] == "Dispel Trap")
        assert r["damage_type"] is None
        assert r["power"] is None

    def test_dispel_trap_effect_text(self):
        r = next(r for r in self.records if r["name"] == "Dispel Trap")
        assert r["effect"] is not None
        assert "dispels" in r["effect"].lower()

    def test_gravity_trap_null_damage(self):
        r = next(r for r in self.records if r["name"] == "Gravity Trap")
        assert r["damage_type"] is None
        assert r["power"] is None

    def test_gravity_trap_effect_has_br_stripped(self):
        r = next(r for r in self.records if r["name"] == "Gravity Trap")
        assert r["effect"] is not None
        assert "<br" not in r["effect"]
        assert "pulses" in r["effect"].lower()

    def test_misdirection_cloud_trap_effect(self):
        r = next(r for r in self.records if r["name"] == "Misdirection Cloud Trap")
        assert r["effect"] is not None
        assert "misses" in r["effect"].lower()

    def test_empty_wikitext_returns_empty(self):
        assert parse_awakening_trap_effects("") == []

    def test_missing_marker_returns_empty(self):
        assert parse_awakening_trap_effects("== Some other section ==\n| [[Foo]] || ||") == []
