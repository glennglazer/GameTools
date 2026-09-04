"""Unit tests for DA/Origins/herbalism/herbalism_json/origins_parse_herbalism.py

Tests cover the pure-function parsing logic — no filesystem, no DB, no network.
"""
import sys
from pathlib import Path

import pytest

# Load the module without executing __main__
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from conftest import REPO_ROOT, load_module

parser = load_module(
    "DA/Origins/herbalism/herbalism_json/origins_parse_herbalism.py",
    "origins_parse_herbalism",
)

strip_wiki_link = parser.strip_wiki_link
get_field = parser.get_field
parse_recipe = parser.parse_recipe
parse_locations = parser.parse_locations
_split_vendor_entries = parser._split_vendor_entries
_parse_vendor_entry = parser._parse_vendor_entry


# ─── strip_wiki_link ──────────────────────────────────────────────────────────

class TestStripWikiLink:
    def test_display_pipe(self):
        assert strip_wiki_link("[[Herbalism#Tiers|Herbalism: Rank 2]]") == "Herbalism: Rank 2"

    def test_simple_link(self):
        assert strip_wiki_link("[[Flask]]") == "Flask"

    def test_piped_ingredient(self):
        assert strip_wiki_link("[[Elfroot (Origins)|Elfroot]]") == "Elfroot"

    def test_plain_text_unchanged(self):
        assert strip_wiki_link("Elfroot") == "Elfroot"

    def test_none_returns_none(self):
        assert strip_wiki_link(None) is None


# ─── get_field ────────────────────────────────────────────────────────────────

_SAMPLE_BLOCK = """
{{RecipeTransformer
|name=Elixir of Grounding
|ingredient1=[[Elfroot (Origins)|Elfroot]]
|quantity1=1
|ingredient2=[[Lifestone (Origins)|Lifestone]]
|quantity2=1
|ingredient3=[[Deep Mushroom (Origins)|Deep Mushroom]]
|quantity3=2
|result=[[Elixir of Grounding]]
|requires=[[Herbalism#Tiers|Herbalism: Rank 3]]
|item_id=gen_im_alc_elx_grounding
}}
"""

class TestGetField:
    def test_name(self):
        assert get_field("name", _SAMPLE_BLOCK) == "Elixir of Grounding"

    def test_ingredient1(self):
        assert get_field("ingredient1", _SAMPLE_BLOCK) == "[[Elfroot (Origins)|Elfroot]]"

    def test_quantity1(self):
        assert get_field("quantity1", _SAMPLE_BLOCK) == "1"

    def test_requires(self):
        assert "Rank 3" in get_field("requires", _SAMPLE_BLOCK)

    def test_missing_field_returns_none(self):
        assert get_field("description", _SAMPLE_BLOCK) is None

    def test_item_id(self):
        assert get_field("item_id", _SAMPLE_BLOCK) == "gen_im_alc_elx_grounding"


# ─── parse_recipe ─────────────────────────────────────────────────────────────

_RECIPE_WIKITEXT_3ING = """\
<onlyinclude>
{{RecipeTransformer
|name=Elixir of Grounding
|ingredient1=[[Elfroot (Origins)|Elfroot]]
|quantity1=1
|ingredient2=[[Lifestone (Origins)|Lifestone]]
|quantity2=1
|ingredient3=[[Deep Mushroom (Origins)|Deep Mushroom]]
|quantity3=2
|result=[[Elixir of Grounding]]
|requires=[[Herbalism#Tiers|Herbalism: Rank 3]]
|item_id=gen_im_alc_elx_grounding
}}
</onlyinclude>
"""

_RECIPE_WIKITEXT_2ING = """\
<onlyinclude>
{{RecipeTransformer
|name=Health Poultice
|ingredient1=[[Elfroot (Origins)|Elfroot]]
|quantity1=2
|ingredient2=[[Flask]]
|quantity2=1
|result=[[Health Poultice]]
|requires=[[Herbalism#Tiers|Herbalism: Rank 1]]
|item_id=gen_im_alc_hlp_minor
}}
</onlyinclude>
"""

class TestParseRecipe:
    def test_name_stripped(self):
        rec = parse_recipe("Elixir of Grounding Recipe", _RECIPE_WIKITEXT_3ING)
        assert rec["name"] == "Elixir of Grounding"

    def test_tier_extracted(self):
        rec = parse_recipe("Elixir of Grounding Recipe", _RECIPE_WIKITEXT_3ING)
        assert rec["tier"] == 3

    def test_three_ingredients(self):
        rec = parse_recipe("Elixir of Grounding Recipe", _RECIPE_WIKITEXT_3ING)
        assert rec["ingredient1"] == "Elfroot"
        assert rec["ingredient2"] == "Lifestone"
        assert rec["ingredient3"] == "Deep Mushroom"
        assert rec["ingredient4"] is None

    def test_quantities(self):
        rec = parse_recipe("Elixir of Grounding Recipe", _RECIPE_WIKITEXT_3ING)
        assert rec["quantity1"] == 1
        assert rec["quantity2"] == 1
        assert rec["quantity3"] == 2
        assert rec["quantity4"] is None

    def test_two_ingredient_nulls(self):
        rec = parse_recipe("Health Poultice Recipe", _RECIPE_WIKITEXT_2ING)
        assert rec["ingredient3"] is None
        assert rec["quantity3"] is None
        assert rec["ingredient4"] is None
        assert rec["quantity4"] is None

    def test_tier_1(self):
        rec = parse_recipe("Health Poultice Recipe", _RECIPE_WIKITEXT_2ING)
        assert rec["tier"] == 1

    def test_item_id_preserved(self):
        rec = parse_recipe("Elixir of Grounding Recipe", _RECIPE_WIKITEXT_3ING)
        assert rec["item_id"] == "gen_im_alc_elx_grounding"


# ─── _split_vendor_entries ────────────────────────────────────────────────────

class TestSplitVendorEntries:
    def test_single_entry(self):
        result = _split_vendor_entries("Jetta in Denerim Market District")
        assert result == ["Jetta in Denerim Market District"]

    def test_two_entries_and(self):
        result = _split_vendor_entries("Vendor A in Place A and Vendor B in Place B")
        assert len(result) == 2
        assert result[0] == "Vendor A in Place A"
        assert result[1] == "Vendor B in Place B"

    def test_three_entries_comma_and(self):
        # Flask pattern: "A in X, B in Y, and C in Z"
        result = _split_vendor_entries(
            "Barlin in Dane's Refuge, Levi Dryden's Warehouse in Warden's Keep (DLC), "
            "and Cesar in Denerim Market District"
        )
        assert len(result) == 3
        assert "Barlin" in result[0]
        assert "Levi Dryden" in result[1]
        assert "Cesar" in result[2]

    def test_parenthetical_not_split(self):
        # Parenthetical notes should not be split even if they contain "and"
        result = _split_vendor_entries("Ruck in Ruck's Cave (kills you, and you die)")
        assert len(result) == 1

    def test_comma_split(self):
        result = _split_vendor_entries("Vendor A in Place A, Vendor B in Place B")
        assert len(result) == 2


# ─── _parse_vendor_entry ──────────────────────────────────────────────────────

class TestParseVendorEntry:
    def test_basic_in(self):
        vendor, location, note = _parse_vendor_entry("Jetta in Denerim Market District")
        assert vendor == "Jetta"
        assert location == "Denerim Market District"
        assert note is None

    def test_at_the(self):
        vendor, location, note = _parse_vendor_entry("Merchant at the Circle Tower")
        assert vendor == "Merchant"
        assert location == "Circle Tower"
        assert note is None

    def test_strips_leading_the(self):
        vendor, location, note = _parse_vendor_entry("Merchant in the Denerim Market District")
        assert location == "Denerim Market District"

    def test_parenthetical_note_extracted(self):
        vendor, location, note = _parse_vendor_entry(
            "Ruck in Ruck's Cave (cheapest)"
        )
        assert vendor == "Ruck"
        assert "Cave" in location
        assert note == "cheapest"

    def test_ruck_in_rocks_cave(self):
        # "Ruck in Ruck's Cave" — vendor=Ruck (first ' in '), not "Ruck's Cave"
        vendor, location, note = _parse_vendor_entry("Ruck in Ruck's Cave in the Frostback Mountains")
        assert vendor == "Ruck"
        assert "Cave" in location or "Mountains" in location

    def test_no_preposition(self):
        # Location-only entry (no vendor)
        vendor, location, note = _parse_vendor_entry("Ruck's Cave")
        assert vendor is None
        assert location == "Ruck's Cave"


# ─── parse_locations ──────────────────────────────────────────────────────────

_LOCATIONS_WIKITEXT = """\
== Locations for unlimited supplies ==
* [[Elfroot (Origins)|Elfroot]]: Jetta in Denerim Market District and Cesar in Denerim Market District
* [[Deep Mushroom (Origins)|Deep Mushroom]]: Ruck in Ruck's Cave
* [[Flask]]s: Barlin in Dane's Refuge, Levi Dryden's Warehouse in Warden's Keep (DLC), and Cesar in Denerim Market District
"""

class TestParseLocations:
    def setup_method(self):
        self.records = parse_locations(_LOCATIONS_WIKITEXT)

    def test_elfroot_two_vendors(self):
        elfroot = [r for r in self.records if r["ingredient"] == "Elfroot"]
        assert len(elfroot) == 2
        vendors = {r["vendor"] for r in elfroot}
        assert "Jetta" in vendors
        assert "Cesar" in vendors

    def test_deep_mushroom_ruck(self):
        dm = [r for r in self.records if r["ingredient"] == "Deep Mushroom"]
        assert len(dm) == 1
        assert dm[0]["vendor"] == "Ruck"

    def test_flask_three_vendors(self):
        flasks = [r for r in self.records if r["ingredient"] == "Flask"]
        assert len(flasks) == 3

    def test_flask_dlc_note(self):
        flasks = [r for r in self.records if r["ingredient"] == "Flask"]
        levi = next(r for r in flasks if r["vendor"] and "Levi" in r["vendor"])
        assert levi["note"] == "DLC"

    def test_all_have_ingredient(self):
        for r in self.records:
            assert r["ingredient"] is not None
            assert r["location"] is not None
