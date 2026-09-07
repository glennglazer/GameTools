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
classify_effect = parser.classify_effect
parse_crafted_item_effects = parser.parse_crafted_item_effects


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


# ─── classify_effect ──────────────────────────────────────────────────────────

class TestClassifyEffect:
    # Health — power computed at SP=0: (base) * multiplier
    def test_health_poultice(self):
        t, p = classify_effect("Instantly restores (50 + SP) health")
        assert t == "Health"
        assert p == 50

    def test_health_formula_mult2(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 2 health")
        assert t == "Health"
        assert p == 100

    def test_health_formula_mult3(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 3 health")
        assert t == "Health"
        assert p == 150

    def test_health_formula_mult4(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 4 health")
        assert t == "Health"
        assert p == 200

    # Mana — power computed at SP=0: base constant only
    def test_mana_lyrium(self):
        t, p = classify_effect("Instantly restores (50 + 0.5 * SP) mana")
        assert t == "Mana"
        assert p == 50

    def test_mana_greater(self):
        t, p = classify_effect("Instantly restores (150 + 0.5 * SP) mana")
        assert t == "Mana"
        assert p == 150

    def test_mana_base_100(self):
        # "Restores" (no "Instantly") — Lyrium Potion
        t, p = classify_effect("Restores (100 + 0.5 * SP) mana")
        assert t == "Mana"
        assert p == 100

    def test_mana_base_200(self):
        t, p = classify_effect("Instantly restores (200 + 0.5 * SP) mana")
        assert t == "Mana"
        assert p == 200

    # Mabari
    def test_mabari_crunch(self):
        t, p = classify_effect(
            "Increases the mabari hound's health and stamina regeneration by +8/+16 "
            "for 10 seconds, and cures a single injury"
        )
        assert t == "Mabari"
        assert p is None

    def test_mabari_double_baked(self):
        t, p = classify_effect(
            "Increases the mabari hound's health and stamina regeneration by +8/+16 "
            "for 10 seconds, and cures up to three injuries"
        )
        assert t == "Mabari"
        assert p is None

    # Injury
    def test_lesser_injury_kit(self):
        t, p = classify_effect(
            "Instantly regains 10 health and is cured of a single injury"
        )
        assert t == "Injury"
        assert p == 10

    def test_injury_kit(self):
        t, p = classify_effect(
            "User instantly regains 20 health and is cured of up to three injuries"
        )
        assert t == "Injury"
        assert p == 20

    def test_greater_injury_kit(self):
        t, p = classify_effect(
            "User instantly regains 40 health and is cured of all injuries"
        )
        assert t == "Injury"
        assert p == 40

    # Cold resistance
    def test_lesser_ice_salve(self):
        t, p = classify_effect("+30% cold resistance for 180 seconds")
        assert t == "Cold Resistance"
        assert p == 30

    def test_greater_ice_salve(self):
        t, p = classify_effect("+60% cold resistance for 180 seconds")
        assert t == "Cold Resistance"
        assert p == 60

    # Nature resistance
    def test_nature_salve(self):
        t, p = classify_effect("+30% nature resistance for 180 seconds")
        assert t == "Nature Resistance"
        assert p == 30

    # Fire resistance
    def test_warmth_balm(self):
        t, p = classify_effect("+30% fire resistance for 180 seconds")
        assert t == "Fire Resistance"
        assert p == 30

    # Spirit resistance
    def test_spirit_balm(self):
        t, p = classify_effect("+30% spirit resistance for 180 seconds")
        assert t == "Spirit Resistance"
        assert p == 30

    # Electricity — two surface forms
    def test_lesser_elixir_of_grounding(self):
        # Lesser form: "resistance to electricity damage by N%"
        t, p = classify_effect(
            "Increases the user's resistance to electricity damage by 30% for 3 minutes; "
            "additionally reduces the stamina drained by electricity"
        )
        assert t == "Electricity Resistance"
        assert p == 30

    def test_greater_elixir_of_grounding(self):
        # Greater form: "+N% electrical resistance"
        t, p = classify_effect(
            "+60% electrical resistance for 180 seconds; "
            "additionally reduces the stamina drained by electricity"
        )
        assert t == "Electricity Resistance"
        assert p == 60

    # Buffs (type=None, power=None)
    def test_incense_of_awareness(self):
        t, p = classify_effect(
            "+10 Defense for 120 seconds, -10 Mental Resistance for 120 seconds"
        )
        assert t is None
        assert p is None

    def test_rock_salve(self):
        t, p = classify_effect(
            "+5 Armor for 120 seconds, +10 Physical Resistance for 120 seconds, "
            "reduced Speed for 120 seconds"
        )
        assert t is None
        assert p is None

    def test_swift_salve(self):
        t, p = classify_effect(
            "Increased movement speed for 60 seconds, increased attack speed for 60 seconds"
        )
        assert t is None
        assert p is None

    def test_dwarven_regicide_antidote(self):
        t, p = classify_effect("The antidote for an exotic dwarven poison")
        assert t is None
        assert p is None


# ─── parse_crafted_item_effects ───────────────────────────────────────────────

_CRAFTED_ITEMS_WIKITEXT = """\
=== Dragon Age: Origins ===

{| class="daotable"
|-
! width="25%" | Tier One Herbalism
! width="25%" | Effect
|-
|[[Lesser Health Poultice]] || Instantly restores (50 + SP) health
|-
|[[Lesser Lyrium Potion]] || Instantly restores (50 + 0.5 * SP) mana
|-
|[[Mabari Crunch]] || Increases the mabari hound's health and stamina regeneration by +8/+16 for 10 seconds, and cures a single injury
|-
! Tier Two Herbalism !! Effect
|-
|[[Incense of Awareness]] || +10 Defense for 120 seconds, -10 Mental Resistance for 120 seconds
|-
|[[Lesser Injury Kit]] || Instantly regains 10 health and is cured of a single injury
|-
|[[Lesser Ice Salve]] || +30% cold resistance for 180 seconds
|}
"""

class TestParseCraftedItemEffects:
    def setup_method(self):
        self.records = parse_crafted_item_effects(_CRAFTED_ITEMS_WIKITEXT)

    def test_six_records_parsed(self):
        assert len(self.records) == 6

    def test_health_poultice_type(self):
        r = next(r for r in self.records if r["name"] == "Lesser Health Poultice")
        assert r["type"] == "Health"
        assert r["power"] == 50  # (50 + SP) at SP=0

    def test_lyrium_potion_type(self):
        r = next(r for r in self.records if r["name"] == "Lesser Lyrium Potion")
        assert r["type"] == "Mana"
        assert r["power"] == 50  # (50 + 0.5*SP) at SP=0

    def test_mabari_type(self):
        r = next(r for r in self.records if r["name"] == "Mabari Crunch")
        assert r["type"] == "Mabari"
        assert r["power"] is None

    def test_buff_type_null(self):
        r = next(r for r in self.records if r["name"] == "Incense of Awareness")
        assert r["type"] is None
        assert r["power"] is None

    def test_injury_kit_power(self):
        r = next(r for r in self.records if r["name"] == "Lesser Injury Kit")
        assert r["type"] == "Injury"
        assert r["power"] == 10

    def test_cold_resistance_power(self):
        r = next(r for r in self.records if r["name"] == "Lesser Ice Salve")
        assert r["type"] == "Cold Resistance"
        assert r["power"] == 30

    def test_effects_verbatim(self):
        r = next(r for r in self.records if r["name"] == "Lesser Health Poultice")
        assert "50 + SP" in r["effects"]

    def test_all_records_have_name_and_effects(self):
        for r in self.records:
            assert r["name"]
            assert r["effects"]
