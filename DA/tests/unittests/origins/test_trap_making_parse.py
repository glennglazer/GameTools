"""Unit tests for origins_parse_trap_making.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

parser = load_module(
    "DA/Origins/trap_making/trap_making_json/origins_parse_trap_making.py",
    "origins_parse_trap_making",
)

strip_wiki_link = parser.strip_wiki_link
parse_recipe = parser.parse_recipe
_parse_damage_pairs = parser._parse_damage_pairs
parse_trap_effects = parser.parse_trap_effects
parse_locations = parser.parse_locations


# ─── strip_wiki_link ──────────────────────────────────────────────────────────

class TestStripWikiLink:
    def test_simple(self):
        assert strip_wiki_link("[[Fire Trap]]") == "Fire Trap"

    def test_piped(self):
        assert strip_wiki_link("[[Deathroot (Origins)|Deathroot]]") == "Deathroot"

    def test_none_returns_none(self):
        assert strip_wiki_link(None) is None

    def test_plain_text_unchanged(self):
        assert strip_wiki_link("Fire Trap") == "Fire Trap"


# ─── parse_recipe ─────────────────────────────────────────────────────────────

_FIRE_TRAP_WIKITEXT = """\
<onlyinclude>{{RecipeTransformer
|style       = {{{style|}}}
|name        = [[Fire Trap Plans]]
|description = Directions for building a fire trap.
|type        = [[Recipes (Origins)|Recipe]]
|value       = 12800
|icon        = rcp_ico_traps_2.png

|ingredient1      = [[Fire Crystal]]
|quantity1        = 1
|ingredient_icon1 = rgt_ico_firecrystal.png

|ingredient2      = [[Corrupter Agent]]
|quantity2        = 1
|ingredient_icon2 = rgt_ico_corrup_agnt.png

|ingredient3      = [[Trap Trigger]]
|quantity3        = 1
|ingredient_icon3 = rgt_ico_traptrig.png

|result      = [[Fire Trap]]
|result_icon = ico_fire_trap.png

|requires    = [[Trap-Making#Tiers|Trap-Making: Rank 3]]
|item_id     = gen_im_cft_trp_208
|appearances = [[Dragon Age: Origins]]
}}</onlyinclude>
"""

_SPRING_TRAP_WIKITEXT = """\
<onlyinclude>{{RecipeTransformer
|name        = [[Spring Trap Plans]]
|description = Plans for a spring trap.
|ingredient1 = [[Metal Shard]]
|quantity1   = 2
|ingredient2 = [[Trap Trigger]]
|quantity2   = 1
|result      = [[Spring Trap]]
|requires    = [[Trap-Making#Tiers|Trap-Making: Rank 1]]
|item_id     = gen_im_cft_trp_101
}}</onlyinclude>
"""

_ACIDIC_GREASE_WIKITEXT = """\
<onlyinclude>{{RecipeTransformer
|name        = [[Acidic Grease Trap Plans]]
|description = Directions for creating an acidic grease trap.
|ingredient1 = [[Lifestone]]
|quantity1   = 3
|ingredient2 = [[Corrupter Agent]]
|quantity2   = 2
|ingredient3 = [[Concentrator Agent]]
|quantity3   = 2
|ingredient4 = [[Trap Trigger]]
|quantity4   = 1
|result      = [[Acidic Grease Trap]]
|requires    = [[Trap-Making#Tiers|Trap-Making: Rank 4]]
|item_id     = gen_im_cft_trp_307
}}</onlyinclude>
"""


class TestParseRecipeName:
    def test_plan_name_extracted(self):
        rec = parse_recipe("Fire Trap Plans", _FIRE_TRAP_WIKITEXT)
        assert rec["name"] == "Fire Trap Plans"

    def test_result_trap_name(self):
        rec = parse_recipe("Fire Trap Plans", _FIRE_TRAP_WIKITEXT)
        assert rec["result"] == "Fire Trap"

    def test_item_id(self):
        rec = parse_recipe("Fire Trap Plans", _FIRE_TRAP_WIKITEXT)
        assert rec["item_id"] == "gen_im_cft_trp_208"


class TestParseRecipeTier:
    def test_tier_3(self):
        rec = parse_recipe("Fire Trap Plans", _FIRE_TRAP_WIKITEXT)
        assert rec["tier"] == 3

    def test_tier_1(self):
        rec = parse_recipe("Spring Trap Plans", _SPRING_TRAP_WIKITEXT)
        assert rec["tier"] == 1

    def test_tier_4(self):
        rec = parse_recipe("Acidic Grease Trap Plans", _ACIDIC_GREASE_WIKITEXT)
        assert rec["tier"] == 4


class TestParseRecipeIngredients:
    def test_three_ingredient_recipe(self):
        rec = parse_recipe("Fire Trap Plans", _FIRE_TRAP_WIKITEXT)
        assert rec["ingredient1"] == "Fire Crystal"
        assert rec["ingredient2"] == "Corrupter Agent"
        assert rec["ingredient3"] == "Trap Trigger"
        assert rec["ingredient4"] is None

    def test_four_ingredient_recipe(self):
        rec = parse_recipe("Acidic Grease Trap Plans", _ACIDIC_GREASE_WIKITEXT)
        assert rec["ingredient1"] == "Lifestone"
        assert rec["ingredient4"] == "Trap Trigger"

    def test_quantities(self):
        rec = parse_recipe("Acidic Grease Trap Plans", _ACIDIC_GREASE_WIKITEXT)
        assert rec["quantity1"] == 3
        assert rec["quantity2"] == 2
        assert rec["quantity4"] == 1


# ─── _parse_damage_pairs ─────────────────────────────────────────────────────

class TestParseDamagePairs:
    def test_physical_damage(self):
        pairs = _parse_damage_pairs("100 physical damage to whoever triggers it")
        assert pairs == [("physical", 100)]

    def test_fire_damage(self):
        pairs = _parse_damage_pairs("100 fire damage to those nearby")
        assert pairs == [("fire", 100)]

    def test_cold_damage(self):
        pairs = _parse_damage_pairs("100 cold damage to those nearby")
        assert pairs == [("cold", 100)]

    def test_nature_damage(self):
        pairs = _parse_damage_pairs("100 nature damage to those nearby")
        assert pairs == [("nature", 100)]

    def test_electricity_damage(self):
        pairs = _parse_damage_pairs("100 electricity damage to those nearby")
        assert pairs == [("electricity", 100)]

    def test_spirit_damage(self):
        pairs = _parse_damage_pairs("100 spirit damage to those nearby")
        assert pairs == [("spirit", 100)]

    def test_periodic_damage(self):
        pairs = _parse_damage_pairs("8 physical damage every 2 seconds to creatures in the area")
        assert pairs == [("physical", 8)]

    def test_dual_damage_returns_two_pairs(self):
        # Poisoned Caltrop Trap splits into two separate rows
        pairs = _parse_damage_pairs(
            "8 physical and 8 nature damage every 2 seconds to creatures in the area"
        )
        assert len(pairs) == 2
        assert ("physical", 8) in pairs
        assert ("nature", 8) in pairs

    def test_dual_damage_order(self):
        pairs = _parse_damage_pairs("8 physical and 8 nature damage every 2 seconds")
        assert pairs[0] == ("physical", 8)
        assert pairs[1] == ("nature", 8)

    def test_empty_string_returns_none_pair(self):
        pairs = _parse_damage_pairs("")
        assert pairs == [(None, None)]

    def test_no_damage_keyword_returns_none_pair(self):
        # Effect-only trap: no damage text
        pairs = _parse_damage_pairs("")
        assert pairs == [(None, None)]


# ─── parse_trap_effects ───────────────────────────────────────────────────────

_TRAPS_WIKITEXT = """\
== Traps ==
{| class="daotable"
|-
! width="25%" | Tier One Traps
! width="25%" | Damage per hit
! Effect
|-
|[[Small Caltrop Trap]] || 8 physical damage every 2 seconds to creatures in the area ||-40% movement speed to creatures in the area
|-
|[[Small Shrapnel Trap]] || 60 physical damage to nearby creatures ||
|-
|[[Spring Trap]] || || Trap knocks down the target, target is motionless for several seconds before standing back up
|-
! Tier Three Traps !! Damage per hit !! Effect
|-
|[[Fire Trap]] || 100 fire damage to those nearby ||
|-
|[[Poisoned Caltrop Trap]] || 8 physical and 8 nature damage every 2 seconds to creatures in the area ||-40% movement speed to creatures in the area
|-
! Tier Four Traps !! Damage per hit !! Effect
|-
|[[Acidic Grease Trap]] || -4 nature damage every second || -50% movement speed to creatures who enter the area
|-
|}

{| class="daotable"
|-
! width="25%" | Tier Four Traps (Awakening)
! width="25%" | Damage per hit
! Effect
|-
| [[Elemental Trap]] || 200 || Deals cold, fire, electricity, nature, spirit damage
|}
"""


class TestParseTrapEffects:
    def setup_method(self):
        self.records = parse_trap_effects(_TRAPS_WIKITEXT)

    def test_awakening_traps_excluded(self):
        names = {r["name"] for r in self.records}
        assert "Elemental Trap" not in names

    def test_dao_trap_count(self):
        # 6 trap names in the fixture; Poisoned Caltrop Trap produces 2 rows → 7 total
        assert len(self.records) == 7

    def test_sorted_by_name(self):
        names = [r["name"] for r in self.records]
        assert names == sorted(names)

    def test_physical_damage_parsed(self):
        trap = next(r for r in self.records if r["name"] == "Small Shrapnel Trap")
        assert trap["damage_type"] == "physical"
        assert trap["power"] == 60

    def test_fire_damage_parsed(self):
        trap = next(r for r in self.records if r["name"] == "Fire Trap")
        assert trap["damage_type"] == "fire"
        assert trap["power"] == 100

    def test_negative_damage_parsed(self):
        trap = next(r for r in self.records if r["name"] == "Acidic Grease Trap")
        assert trap["damage_type"] == "nature"
        assert trap["power"] == -4

    def test_dual_damage_parsed(self):
        # Poisoned Caltrop Trap produces two rows — one per damage type
        rows = [r for r in self.records if r["name"] == "Poisoned Caltrop Trap"]
        assert len(rows) == 2
        types = {r["damage_type"] for r in rows}
        assert "physical" in types
        assert "nature" in types
        for row in rows:
            assert row["power"] == 8

    def test_damage_and_effect_both_present(self):
        trap = next(r for r in self.records if r["name"] == "Small Caltrop Trap")
        assert trap["damage_type"] == "physical"
        assert trap["power"] == 8
        assert trap["effect"] is not None
        assert "movement speed" in trap["effect"]

    def test_damage_only_effect_null(self):
        trap = next(r for r in self.records if r["name"] == "Small Shrapnel Trap")
        assert trap["effect"] is None

    def test_effect_only_no_damage(self):
        trap = next(r for r in self.records if r["name"] == "Spring Trap")
        assert trap["damage_type"] is None
        assert trap["power"] is None
        assert trap["effect"] is not None
        assert "knocks down" in trap["effect"]


# ─── parse_locations ──────────────────────────────────────────────────────────

_LOCATIONS_WIKITEXT = """\
== Locations for unlimited supplies==
The following vendors have unlimited supplies of important trap ingredients.

* [[Concentrator Agent]]: Bartender at the [[Gnawed Noble Tavern]], [[Bodahn Feddic]]
* [[Corrupter Agent]]: [[Bodahn Feddic]], [[Alimar]] in [[Dust Town]] (cheaper)
* [[Deathroot (Origins)|Deathroot]] and [[Toxin Extract]]: [[Varathorn]] at the [[Dalish Camp]]
* [[Distillation Agent]]: Bartender at the [[Gnawed Noble Tavern]], [[Bodahn Feddic]]
* [[Lifestone]]: [[Ruck]]
* [[Trap Trigger]]: [[Alimar]] in [[Dust Town]], [[Barlin]] in [[Lothering]] (cheaper)
"""


class TestParseLocations:
    def setup_method(self):
        self.records = parse_locations(_LOCATIONS_WIKITEXT)

    def test_total_count(self):
        # Concentrator Agent: 2; Corrupter Agent: 2; Deathroot: 1; Toxin Extract: 1;
        # Distillation Agent: 2; Lifestone: 1; Trap Trigger: 2  → 11 rows
        assert len(self.records) == 11

    def test_bartender_with_location(self):
        row = next(
            r for r in self.records
            if r["ingredient"] == "Concentrator Agent" and r["vendor"] == "Bartender"
        )
        assert row["location"] == "Gnawed Noble Tavern"
        assert row["note"] is None

    def test_bodahn_bare_vendor_null_location(self):
        row = next(
            r for r in self.records
            if r["ingredient"] == "Concentrator Agent" and r["vendor"] == "Bodahn Feddic"
        )
        assert row["location"] is None

    def test_alimar_note_cheaper(self):
        row = next(
            r for r in self.records
            if r["ingredient"] == "Corrupter Agent" and r["vendor"] == "Alimar"
        )
        assert row["location"] == "Dust Town"
        assert row["note"] == "cheaper"

    def test_dual_ingredient_deathroot(self):
        row = next(r for r in self.records if r["ingredient"] == "Deathroot")
        assert row["vendor"] == "Varathorn"
        assert row["location"] == "Dalish Camp"

    def test_dual_ingredient_toxin_extract(self):
        row = next(r for r in self.records if r["ingredient"] == "Toxin Extract")
        assert row["vendor"] == "Varathorn"
        assert row["location"] == "Dalish Camp"

    def test_dual_ingredient_shares_vendor(self):
        deathroot = next(r for r in self.records if r["ingredient"] == "Deathroot")
        toxin = next(r for r in self.records if r["ingredient"] == "Toxin Extract")
        assert deathroot["vendor"] == toxin["vendor"]
        assert deathroot["location"] == toxin["location"]

    def test_ruck_bare_vendor(self):
        row = next(r for r in self.records if r["ingredient"] == "Lifestone")
        assert row["vendor"] == "Ruck"
        assert row["location"] is None

    def test_barlin_note_cheaper(self):
        row = next(
            r for r in self.records
            if r["ingredient"] == "Trap Trigger" and r["vendor"] == "Barlin"
        )
        assert row["location"] == "Lothering"
        assert row["note"] == "cheaper"

    def test_trap_trigger_two_vendors(self):
        rows = [r for r in self.records if r["ingredient"] == "Trap Trigger"]
        assert len(rows) == 2
        vendors = {r["vendor"] for r in rows}
        assert "Alimar" in vendors
        assert "Barlin" in vendors

    def test_all_have_ingredient_and_vendor(self):
        for r in self.records:
            assert r["ingredient"] is not None
            assert r["vendor"] is not None
