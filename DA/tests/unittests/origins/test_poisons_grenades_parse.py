"""Unit tests for DA/Origins/poisons_grenades/poisons_grenades_json/origins_parse_poisons_grenades.py"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

parser = load_module(
    "DA/Origins/poisons_grenades/poisons_grenades_json/origins_parse_poisons_grenades.py",
    "origins_parse_poisons_grenades",
)

strip_wiki_link = parser.strip_wiki_link
get_field = parser.get_field
parse_recipe = parser.parse_recipe
parse_locations = parser.parse_locations
_split_vendor_entries = parser._split_vendor_entries
_parse_vendor_entry = parser._parse_vendor_entry

# Canonical grenade result names (Tier Two DAO only)
GRENADE_RESULTS = {"Acid Flask", "Fire Bomb", "Freeze Bomb", "Shock Bomb", "Soulrot Bomb"}

# ─── RecipeTransformer sample blocks ──────────────────────────────────────────

_DEATHROOT_EXTRACT = """\
<onlyinclude>{{RecipeTransformer
|name=[[Deathroot Extract Recipe]]
|ingredient1=[[Deathroot (Origins)|Deathroot]]
|quantity1=1
|ingredient2=[[Flask]]
|quantity2=1
|result=[[Deathroot Extract]]
|requires=[[Poison-Making#|Poison-Making: Rank 1]]
|item_id=gen_im_cft_psn_102
}}</onlyinclude>
"""

_FIRE_BOMB = """\
<onlyinclude>{{RecipeTransformer
|name=[[Fire Bomb Recipe]]
|ingredient1=[[Fire Crystal]]
|quantity1=1
|ingredient2=[[Flask]]
|quantity2=1
|ingredient3=[[Corrupter Agent]]
|quantity3=1
|result=[[Fire Bomb]]
|requires=[[Poison-Making#Tiers|Poison-Making: Rank 2]]
|item_id=gen_im_cft_psn_206
}}</onlyinclude>
"""

_MAGEBANE = """\
<onlyinclude>{{RecipeTransformer
|name=[[Magebane Poison Recipe]]
|ingredient1=[[Lyrium Dust]]
|quantity1=3
|ingredient2=[[Flask]]
|quantity2=1
|ingredient3=[[Corrupter Agent]]
|quantity3=2
|ingredient4=[[Concentrator Agent]]
|quantity4=1
|result=[[Magebane]]
|requires=[[Poison-Making#|Poison-Making: Rank 3]]
|item_id=gen_im_cft_psn_310
}}</onlyinclude>
"""


# ─── strip_wiki_link ──────────────────────────────────────────────────────────

class TestStripWikiLink:
    def test_display_pipe(self):
        assert strip_wiki_link("[[Poison-Making#Tiers|Poison-Making: Rank 2]]") == "Poison-Making: Rank 2"

    def test_simple(self):
        assert strip_wiki_link("[[Fire Bomb]]") == "Fire Bomb"

    def test_piped(self):
        assert strip_wiki_link("[[Deathroot (Origins)|Deathroot]]") == "Deathroot"

    def test_none_returns_none(self):
        assert strip_wiki_link(None) is None


# ─── parse_recipe: type classification ───────────────────────────────────────

class TestParseRecipeType:
    def test_poison_type(self):
        rec = parse_recipe("Deathroot Extract Recipe", _DEATHROOT_EXTRACT, GRENADE_RESULTS)
        assert rec["type"] == "poison"

    def test_grenade_type(self):
        rec = parse_recipe("Fire Bomb Recipe", _FIRE_BOMB, GRENADE_RESULTS)
        assert rec["type"] == "grenade"

    def test_poison_with_four_ingredients(self):
        rec = parse_recipe("Magebane Poison Recipe", _MAGEBANE, GRENADE_RESULTS)
        assert rec["type"] == "poison"


# ─── parse_recipe: tier extraction ───────────────────────────────────────────

class TestParseRecipeTier:
    def test_tier_1(self):
        rec = parse_recipe("Deathroot Extract Recipe", _DEATHROOT_EXTRACT, GRENADE_RESULTS)
        assert rec["tier"] == 1

    def test_tier_2_grenade(self):
        rec = parse_recipe("Fire Bomb Recipe", _FIRE_BOMB, GRENADE_RESULTS)
        assert rec["tier"] == 2

    def test_tier_3(self):
        rec = parse_recipe("Magebane Poison Recipe", _MAGEBANE, GRENADE_RESULTS)
        assert rec["tier"] == 3

    def test_both_requires_formats(self):
        # Poison-Making#|...: Rank N  (no "Tiers" in anchor) → still extracts tier
        rec = parse_recipe("Deathroot Extract Recipe", _DEATHROOT_EXTRACT, GRENADE_RESULTS)
        assert rec["tier"] == 1


# ─── parse_recipe: ingredient columns ────────────────────────────────────────

class TestParseRecipeIngredients:
    def test_two_ingredient_recipe(self):
        rec = parse_recipe("Deathroot Extract Recipe", _DEATHROOT_EXTRACT, GRENADE_RESULTS)
        assert rec["ingredient1"] == "Deathroot"
        assert rec["ingredient2"] == "Flask"
        assert rec["ingredient3"] is None
        assert rec["ingredient4"] is None

    def test_three_ingredient_grenade(self):
        rec = parse_recipe("Fire Bomb Recipe", _FIRE_BOMB, GRENADE_RESULTS)
        assert rec["ingredient1"] == "Fire Crystal"
        assert rec["ingredient2"] == "Flask"
        assert rec["ingredient3"] == "Corrupter Agent"
        assert rec["ingredient4"] is None

    def test_four_ingredient_poison(self):
        rec = parse_recipe("Magebane Poison Recipe", _MAGEBANE, GRENADE_RESULTS)
        assert rec["ingredient1"] == "Lyrium Dust"
        assert rec["ingredient2"] == "Flask"
        assert rec["ingredient3"] == "Corrupter Agent"
        assert rec["ingredient4"] == "Concentrator Agent"

    def test_quantities_correct(self):
        rec = parse_recipe("Magebane Poison Recipe", _MAGEBANE, GRENADE_RESULTS)
        assert rec["quantity1"] == 3
        assert rec["quantity4"] == 1

    def test_result_field(self):
        rec = parse_recipe("Magebane Poison Recipe", _MAGEBANE, GRENADE_RESULTS)
        assert rec["result"] == "Magebane"

    def test_name_field(self):
        rec = parse_recipe("Magebane Poison Recipe", _MAGEBANE, GRENADE_RESULTS)
        assert rec["name"] == "Magebane Poison Recipe"


# ─── _parse_vendor_entry: "your " prefix stripping ───────────────────────────

class TestParseVendorEntry:
    def test_at_your_stripped(self):
        vendor, location, note = _parse_vendor_entry("Bodahn Feddic at your Party Camp")
        assert vendor == "Bodahn Feddic"
        assert location == "Party Camp"
        assert note is None

    def test_at_the_stripped(self):
        vendor, location, note = _parse_vendor_entry("Quartermaster at the Circle Tower")
        assert vendor == "Quartermaster"
        assert location == "Circle Tower"

    def test_in_first_preposition(self):
        # "Ruck in Ruck's Cave in..." → vendor=Ruck, location has rest
        vendor, location, note = _parse_vendor_entry(
            "Ruck in Ruck's Cave in the Ortan Thaig area of The Deep Roads"
        )
        assert vendor == "Ruck"
        assert "Cave" in location

    def test_note_with_trailing_period(self):
        # Key regression: "(note)." at end must be extracted as note, not left in location
        vendor, location, note = _parse_vendor_entry(
            "Alimar in Dust Town (If not forced to accept bribe of 10 silvers for information)."
        )
        assert vendor == "Alimar"
        assert location == "Dust Town"
        assert note is not None
        assert "bribe" in note

    def test_note_without_trailing_period(self):
        vendor, location, note = _parse_vendor_entry(
            "Varathorn at the Dalish Camp (if you side with werewolves he will be unavailable)"
        )
        assert vendor == "Varathorn"
        assert location == "Dalish Camp"
        assert "werewolves" in note

    def test_figor_nested_in(self):
        # "Figor in Figor's Imports in Orzammar" → vendor=Figor, location includes "Imports"
        vendor, location, note = _parse_vendor_entry(
            "Figor in Figor's Imports in Orzammar (you must scare off the Carta thugs first)"
        )
        assert vendor == "Figor"
        assert "Figor's Imports" in location
        assert note == "you must scare off the Carta thugs first"


# ─── _split_vendor_entries: four-entry Flask case ────────────────────────────

class TestSplitFourVendors:
    def test_flask_four_vendors(self):
        text = (
            "Bartender in the Gnawed Noble Tavern in Denerim Market District, "
            "Innkeeper at The Spoiled Princess, "
            "Figor in Figor's Imports in Orzammar (you must scare off the Carta thugs first), "
            "and Bodahn Feddic at your Party Camp"
        )
        entries = _split_vendor_entries(text)
        assert len(entries) == 4
        assert "Bartender" in entries[0]
        assert "Innkeeper" in entries[1]
        assert "Figor" in entries[2]
        assert "Bodahn" in entries[3]


# ─── parse_locations ──────────────────────────────────────────────────────────

_LOCATIONS_WIKITEXT = """\
== Locations for unlimited supplies ==
The following vendors sell unlimited supplies of important poison-making ingredients.

* [[Concentrator Agent]]: Bartender in the [[Gnawed Noble Tavern]] in [[Denerim Market District]] and [[Bodahn Feddic]] at your [[Party Camp]]
* [[Corrupter Agent]]: [[Bodahn Feddic]] at your [[Party Camp]] and [[Alimar]] in [[Dust Town]] (If not forced to accept bribe of 10 silvers for information).
* [[Flask]]s: Bartender in the [[Gnawed Noble Tavern]] in Denerim Market District, Innkeeper at [[The Spoiled Princess]], Figor in Figor's Imports in [[Orzammar]] (you must scare off the Carta thugs first), and [[Bodahn Feddic]] at your Party Camp
* [[Lyrium Dust]]: Quartermaster in the [[Circle Tower]]
"""

class TestParseLocations:
    def setup_method(self):
        self.records = parse_locations(_LOCATIONS_WIKITEXT)

    def test_concentrator_agent_two_vendors(self):
        ca = [r for r in self.records if r["ingredient"] == "Concentrator Agent"]
        assert len(ca) == 2
        vendors = {r["vendor"] for r in ca}
        assert "Bartender" in vendors
        assert "Bodahn Feddic" in vendors

    def test_party_camp_stripped_your(self):
        ca = [r for r in self.records if r["ingredient"] == "Concentrator Agent"]
        bodahn = next(r for r in ca if r["vendor"] == "Bodahn Feddic")
        assert bodahn["location"] == "Party Camp"

    def test_corrupter_agent_alimar_note(self):
        ca = [r for r in self.records if r["ingredient"] == "Corrupter Agent"]
        alimar = next(r for r in ca if r["vendor"] == "Alimar")
        assert alimar["location"] == "Dust Town"
        assert alimar["note"] is not None
        assert "bribe" in alimar["note"]

    def test_flask_four_vendors(self):
        flasks = [r for r in self.records if r["ingredient"] == "Flask"]
        assert len(flasks) == 4

    def test_flask_figor_note(self):
        flasks = [r for r in self.records if r["ingredient"] == "Flask"]
        figor = next(r for r in flasks if r["vendor"] == "Figor")
        assert "Imports" in figor["location"]
        assert figor["note"] == "you must scare off the Carta thugs first"

    def test_flask_innkeeper_the_stripped(self):
        flasks = [r for r in self.records if r["ingredient"] == "Flask"]
        innkeeper = next(r for r in flasks if r["vendor"] == "Innkeeper")
        # "The Spoiled Princess" → "Spoiled Princess"
        assert innkeeper["location"] == "Spoiled Princess"

    def test_lyrium_dust_one_vendor(self):
        ld = [r for r in self.records if r["ingredient"] == "Lyrium Dust"]
        assert len(ld) == 1
        assert ld[0]["vendor"] == "Quartermaster"
        assert ld[0]["location"] == "Circle Tower"

    def test_all_have_ingredient_and_location(self):
        for r in self.records:
            assert r["ingredient"] is not None
            assert r["location"] is not None
