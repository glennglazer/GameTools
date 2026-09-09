"""Unit tests for DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_parse_poisons_grenades.py"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

parser = load_module(
    "DA/Awakening/poisons_grenades/poisons_grenades_json/awakening_parse_poisons_grenades.py",
    "awakening_parse_poisons_grenades",
)

strip_wiki_link = parser.strip_wiki_link
get_field = parser.get_field
parse_recipe = parser.parse_recipe
_parse_elemental = parser._parse_elemental
_parse_dispel_effect = parser._parse_dispel_effect
parse_awakening_effects = parser.parse_awakening_effects

# Grenade results as extracted from the Awakening wiki section
GRENADE_RESULTS = {"Dispel Grenade", "Elemental Grenade"}

# ─── RecipeTransformer sample blocks ──────────────────────────────────────────

_DISPEL_GRENADE = """\
<onlyinclude>{{RecipeTransformer
|name=[[Dispel Grenade Recipe]]
|ingredient1=[[Rashvine Nettle]]
|quantity1=1
|ingredient2=[[Flask]]
|quantity2=1
|ingredient3=[[Corrupter Agent]]
|quantity3=2
|ingredient4=[[Concentrator Agent]]
|quantity4=1
|result=[[Dispel Grenade]]
|requires=[[Poison-Making#|Poison-Making: Rank 4]]
|item_id=gxa_im_cft_psn_401
}}</onlyinclude>
"""

_DISPEL_POISON = """\
<onlyinclude>{{RecipeTransformer
|name=[[Dispel Poison Recipe]]
|ingredient1=[[Rashvine Nettle]]
|quantity1=2
|ingredient2=[[Flask]]
|quantity2=1
|ingredient3=[[Corrupter Agent]]
|quantity3=4
|ingredient4=[[Concentrator Agent]]
|quantity4=2
|result=[[Dispel Coating]]
|requires=[[Poison-Making#Tiers|Poison-Making: Rank 4]]
|item_id=gxa_
}}</onlyinclude>
"""

_ELEMENTAL_GRENADE = """\
<onlyinclude>{{RecipeTransformer
|name=[[Elemental Grenade Recipe]]
|ingredient1=[[Blood Lotus (Origins)|Blood Lotus]]
|quantity1=1
|ingredient2=[[Flask]]
|quantity2=1
|ingredient3=[[Corrupter Agent]]
|quantity3=2
|ingredient4=[[Concentrator Agent]]
|quantity4=1
|result=[[Elemental Grenade]]
|requires=[[Poison-Making#Tiers|Poison-Making: Rank 4]]
|item_id=gxa_im_cft_psn_402
}}</onlyinclude>
"""

# ─── Awakening effects wikitext fixture ───────────────────────────────────────

_AWAKENING_EFFECTS_WIKITEXT = """\
== Dragon Age: Origins - Awakening ==
Note that both poisons and the Dispel Grenade are bugged, see their pages for details.

{| class="daotable"
! Tier Four Poisons !! Damage Per Hit || Effect
|-
| [[Elemental Coating]] || 2 cold, fire, electricity, nature, and spirit damage for a total of 10. ||
|-
| [[Dispel Coating]] || || None. Dispels magic on hit.
|}


{| class="daotable"
! Tier Four Grenades !! Damage
|-
| [[Elemental Grenade]] || 30 cold, electricity, fire, nature and spirit damage for a total of 150.
|-
| [[Dispel Grenade]] || None. Dispels magic in affected area.
|}
"""


# ─── strip_wiki_link ──────────────────────────────────────────────────────────

class TestStripWikiLink:
    def test_simple(self):
        assert strip_wiki_link("[[Dispel Grenade]]") == "Dispel Grenade"

    def test_piped(self):
        assert strip_wiki_link("[[Blood Lotus (Origins)|Blood Lotus]]") == "Blood Lotus"

    def test_display_pipe(self):
        assert strip_wiki_link("[[Poison-Making#Tiers|Poison-Making: Rank 4]]") == "Poison-Making: Rank 4"

    def test_none_returns_none(self):
        assert strip_wiki_link(None) is None


# ─── parse_recipe: type classification ───────────────────────────────────────

class TestParseRecipeType:
    def test_grenade_type(self):
        rec = parse_recipe("Dispel Grenade Recipe", _DISPEL_GRENADE, GRENADE_RESULTS)
        assert rec["type"] == "grenade"

    def test_poison_type(self):
        rec = parse_recipe("Dispel Poison Recipe", _DISPEL_POISON, GRENADE_RESULTS)
        assert rec["type"] == "poison"

    def test_elemental_grenade_type(self):
        rec = parse_recipe("Elemental Grenade Recipe", _ELEMENTAL_GRENADE, GRENADE_RESULTS)
        assert rec["type"] == "grenade"


# ─── parse_recipe: tier extraction ───────────────────────────────────────────

class TestParseRecipeTier:
    def test_tier_4_no_tiers_anchor(self):
        rec = parse_recipe("Dispel Grenade Recipe", _DISPEL_GRENADE, GRENADE_RESULTS)
        assert rec["tier"] == 4

    def test_tier_4_with_tiers_anchor(self):
        rec = parse_recipe("Dispel Poison Recipe", _DISPEL_POISON, GRENADE_RESULTS)
        assert rec["tier"] == 4

    def test_all_awakening_tier_4(self):
        for wikitext in [_DISPEL_GRENADE, _DISPEL_POISON, _ELEMENTAL_GRENADE]:
            rec = parse_recipe("Any Recipe", wikitext, GRENADE_RESULTS)
            assert rec["tier"] == 4


# ─── parse_recipe: fields ─────────────────────────────────────────────────────

class TestParseRecipeFields:
    def test_name(self):
        rec = parse_recipe("Dispel Grenade Recipe", _DISPEL_GRENADE, GRENADE_RESULTS)
        assert rec["name"] == "Dispel Grenade Recipe"

    def test_result(self):
        rec = parse_recipe("Dispel Grenade Recipe", _DISPEL_GRENADE, GRENADE_RESULTS)
        assert rec["result"] == "Dispel Grenade"

    def test_gxa_item_id(self):
        rec = parse_recipe("Dispel Grenade Recipe", _DISPEL_GRENADE, GRENADE_RESULTS)
        assert rec["item_id"] == "gxa_im_cft_psn_401"

    def test_piped_ingredient_link(self):
        rec = parse_recipe("Elemental Grenade Recipe", _ELEMENTAL_GRENADE, GRENADE_RESULTS)
        assert rec["ingredient1"] == "Blood Lotus"

    def test_four_ingredients(self):
        rec = parse_recipe("Dispel Grenade Recipe", _DISPEL_GRENADE, GRENADE_RESULTS)
        assert rec["ingredient1"] == "Rashvine Nettle"
        assert rec["ingredient2"] == "Flask"
        assert rec["ingredient3"] == "Corrupter Agent"
        assert rec["ingredient4"] == "Concentrator Agent"

    def test_quantities(self):
        rec = parse_recipe("Dispel Poison Recipe", _DISPEL_POISON, GRENADE_RESULTS)
        assert rec["quantity1"] == 2
        assert rec["quantity3"] == 4
        assert rec["quantity4"] == 2

    def test_nullable_ingredient_slots_absent(self):
        # All four Awakening recipes have exactly 4 ingredients, so no nulls
        rec = parse_recipe("Dispel Grenade Recipe", _DISPEL_GRENADE, GRENADE_RESULTS)
        assert rec["ingredient4"] == "Concentrator Agent"


# ─── _parse_elemental ─────────────────────────────────────────────────────────

class TestParseElemental:
    def test_coating_total_10(self):
        cell = "2 cold, fire, electricity, nature, and spirit damage for a total of 10."
        result = _parse_elemental(cell)
        assert result is not None
        types_str, total = result
        assert total == 10
        # Types are sorted alphabetically and joined
        assert types_str == "cold, electricity, fire, nature, spirit"

    def test_grenade_total_150(self):
        cell = "30 cold, electricity, fire, nature and spirit damage for a total of 150."
        result = _parse_elemental(cell)
        assert result is not None
        types_str, total = result
        assert total == 150
        assert types_str == "cold, electricity, fire, nature, spirit"

    def test_dispel_cell_returns_none(self):
        assert _parse_elemental("") is None
        assert _parse_elemental("None. Dispels magic on hit.") is None

    def test_types_sorted_consistently(self):
        # "fire, cold" order in wiki should come out alphabetically
        cell = "1 fire, cold damage for a total of 2."
        result = _parse_elemental(cell)
        assert result is not None
        types_str, _ = result
        assert types_str == "cold, fire"


# ─── _parse_dispel_effect ────────────────────────────────────────────────────

class TestParseDispelEffect:
    def test_none_prefix_stripped_single_cell(self):
        eff = _parse_dispel_effect("None. Dispels magic in affected area.", "")
        assert eff == "Dispels magic in affected area."

    def test_none_prefix_stripped_second_cell(self):
        eff = _parse_dispel_effect("", "None. Dispels magic on hit.")
        assert eff == "Dispels magic on hit."

    def test_empty_both_returns_none(self):
        eff = _parse_dispel_effect("", "")
        assert eff is None


# ─── parse_awakening_effects ─────────────────────────────────────────────────

class TestParseAwakeningEffects:
    def setup_method(self):
        self.records = parse_awakening_effects(_AWAKENING_EFFECTS_WIKITEXT)

    def test_total_count(self):
        assert len(self.records) == 4

    def test_sorted_by_name(self):
        names = [r["name"] for r in self.records]
        assert names == sorted(names)

    def test_elemental_coating_damage_type(self):
        r = next(r for r in self.records if r["name"] == "Elemental Coating")
        assert r["damage_type"] == "cold, electricity, fire, nature, spirit"

    def test_elemental_coating_total_power(self):
        r = next(r for r in self.records if r["name"] == "Elemental Coating")
        assert r["power"] == 10

    def test_elemental_coating_no_effect(self):
        r = next(r for r in self.records if r["name"] == "Elemental Coating")
        assert r["effect"] is None

    def test_elemental_grenade_total_power(self):
        r = next(r for r in self.records if r["name"] == "Elemental Grenade")
        assert r["power"] == 150

    def test_elemental_grenade_damage_type(self):
        r = next(r for r in self.records if r["name"] == "Elemental Grenade")
        assert r["damage_type"] == "cold, electricity, fire, nature, spirit"

    def test_dispel_coating_null_damage(self):
        r = next(r for r in self.records if r["name"] == "Dispel Coating")
        assert r["damage_type"] is None
        assert r["power"] is None

    def test_dispel_coating_effect(self):
        r = next(r for r in self.records if r["name"] == "Dispel Coating")
        assert r["effect"] is not None
        assert "Dispels magic" in r["effect"]

    def test_dispel_grenade_null_damage(self):
        r = next(r for r in self.records if r["name"] == "Dispel Grenade")
        assert r["damage_type"] is None
        assert r["power"] is None

    def test_dispel_grenade_effect(self):
        r = next(r for r in self.records if r["name"] == "Dispel Grenade")
        assert r["effect"] is not None
        assert "Dispels magic" in r["effect"]

    def test_both_elemental_same_damage_type(self):
        elemental = [r for r in self.records if r["name"].startswith("Elemental")]
        assert len(elemental) == 2
        types = {r["damage_type"] for r in elemental}
        assert len(types) == 1  # same damage type string for both
        assert "cold" in types.pop()

    def test_both_dispel_have_null_power(self):
        dispel = [r for r in self.records if r["name"].startswith("Dispel")]
        assert len(dispel) == 2
        for r in dispel:
            assert r["power"] is None
