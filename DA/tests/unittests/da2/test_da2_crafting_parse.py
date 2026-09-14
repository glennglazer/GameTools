"""
Unit tests for da2_parse_crafting.py

Covers:
  - parse_recipe_locations: act range parsing, wiki link stripping, location text
  - parse_resources: act tagging, display text extraction, empty quest
  - parse_recipes: ingredient column mapping, currency conversion, 4-ingredient recipes
  - parse_item_effects: ColorPositiveStat extraction, multi-effect joining
"""

import json
import pytest
from conftest import load_module

mod = load_module(
    "DA/DA2/crafting/crafting_json/da2_parse_crafting.py",
    "da2_parse_crafting",
)

parse_recipe_locations = mod.parse_recipe_locations
parse_resources = mod.parse_resources
parse_recipes = mod.parse_recipes
parse_item_effects = mod.parse_item_effects
value_to_currency = mod.value_to_currency
canonical_ingredient = mod.canonical_ingredient
extract_template_block = mod.extract_template_block


# ── fixture data ──────────────────────────────────────────────────────────────

_CRAFTING_WIKITEXT = """\
== Crafting recipes ==
=== Potions ===
* Act 1: [[Elfroot Potion]] given by [[Lady Elegant]] in [[Lowtown]].
* Act 1-3: [[Restoration Potion]] bought from [[Formari Herbalist]] shop in [[The Gallows]].
* Act 2: [[Rock Armor Potion]] found in [[Lowtown]] at night, in a Pile of Rubble next to the entrance to Gamlen's house.
* Act 2: [[Elixir of Heroism]] found in [[Hightown]] During quest [[Demands of The Qun]].
=== Runes ===
* Act 1: [[Rune of Protection]] gift from [[Worthy]] in [[Hightown]] the first time you talk to him.
* Act 1-3: [[Rune of Fortune]] bought at the [[Black Emporium]](DLC).
* Act 3: [[Rune of Devastation]] found in the Sewer Passage during the quest [[On The Loose]].
=== Poisons and grenades ===
* Act 1: [[Debilitating Poison]] given in [[Darktown]] from Tomwise.
* Act 2-3: [[Arcane Poison]] Looted from Elven Fanatic in Side Alley during [[Blackpowder Courtesy]] main quest.
* Act 3: [[Fell Poison]] can be looted from the corpse of Huon during the quest "[[On The Loose]]".

== Crafting resource locations ==
"""

_SUPPLIER_WIKITEXT = """\
== Crafting resources ==
=== Act 1 ===
:{| class="sortable daotable" width="100%"
!Location
!Quest
!Resource
!Description
|-
|[[The Bone Pit]]||||[[Elfroot (Dragon Age II)|Elfroot]]||On the far south east end of the map.
|-
|[[Darktown]]||||[[Deathroot (Dragon Age II)|Deathroot]]||On the south end of the map.
|-
|[[Sundermount Caverns]]||||[[Silverite]]||Next to the door in the fire pit room.
|-
|[[Bone Pit Mines]]||[[The Bone Pit (quest)|The Bone Pit]]||[[Deep Mushroom (Dragon Age II)|Deep Mushroom]]||Up the first set of stairs after killing the dragonlings.
|-
|[[Deep Roads]]||[[The Deep Roads Expedition]]||[[Lyrium (crafting resource)|Lyrium]]||Where Sandal is found.
|}

=== Act 2 ===
:{| class="sortable daotable" width="100%"
!Location
!Quest
!Resource
!Description
|-
|[[Holding Caves]]||[[A Bitter Pill]]||[[Glitterdust]]||Near where the four paths meet.
|-
|[[Holding Caves]]||[[A Bitter Pill]]||[[Embrium]]||On the west path near the start.
|-
|[[Sundermount]]||||[[Elfroot (Dragon Age II)|Elfroot]]||In the stone ruin on the low path.
|}

=== Act 3 ===
:{| class="sortable daotable" width="100%"
!Location
!Quest
!Resource
!Description
|-
|[[The Bone Pit]]||[[Mine Massacre]]||[[Dragon's Blood]]||Collected from the High Dragon's corpse.
|-
|[[Pride's End]]||[[A New Path]]||[[Felandaris (Dragon Age II)|Felandaris]]||To the right of Audacity's idol.
|}

== Summaries ==
"""

_ELFROOT_RECIPE_WT = """\
<onlyinclude>{{RecipeTransformer
|style            = {{{style|}}}
|name             = [[Recipe: Elfroot Potion]]
|type             = [[Recipes (Dragon Age II)|Crafting Recipe]]
|ingredient1      = [[Elfroot (Dragon Age II)|Elfroot]]
|quantity1        = 1
|ingredient_icon1 = Elfroot DA2.png
|result           = [[Elfroot Potion]]
}}</onlyinclude>

== Crafting ==
* It costs {{Currency|3750}} to order an [[Elfroot Potion]].
"""

_RESTORATION_RECIPE_WT = """\
<onlyinclude>{{RecipeTransformer
|style            = {{{style|}}}
|name             = [[Recipe: Restoration Potion]]
|ingredient1      = [[Elfroot (Dragon Age II)|Elfroot]]
|quantity1        = 3
|ingredient_icon1 = Elfroot DA2.png
|ingredient2      = [[Spindleweed]]
|quantity2        = 2
|ingredient_icon2 = Spindleweed.png
|result           = [[Restoration Potion]]
}}</onlyinclude>

== Crafting ==
* It costs {{Currency|4900}} to order a [[Restoration Potion]].
"""

_DEVASTATION_RECIPE_WT = """\
<onlyinclude>{{RecipeTransformer
|style            = {{{style|}}}
|name             = [[Design: Rune of Devastation]]
|ingredient1      = [[Lyrium (crafting resource)|Lyrium]]
|quantity1        = 3
|ingredient_icon1 = Lyrium.png
|ingredient2      = [[Silverite]]
|quantity2        = 4
|ingredient_icon2 = Silverite.png
|ingredient3      = [[Orichalcum]]
|quantity3        = 4
|ingredient_icon3 = Orichalcum.png
|ingredient4      = [[Dragon's Blood]]
|quantity4        = 1
|ingredient_icon4 = Dragon's Blood.png
|result           = [[Rune of Devastation]]
}}</onlyinclude>

== Crafting ==
* It costs {{Currency|7500}} to order a [[Rune of Devastation]].
"""

_HEROISM_RECIPE_WT = """\
<onlyinclude>{{RecipeTransformer
|style            = {{{style|}}}
|name             = [[Recipe: Elixir of Heroism]]
|ingredient1      = [[Elfroot (Dragon Age II)|Elfroot]]
|quantity1        = 5
|ingredient_icon1 = Elfroot DA2.png
|ingredient2      = [[Spindleweed]]
|quantity2        = 4
|ingredient_icon2 = Spindleweed.png
|ingredient3      = [[Embrium]]
|quantity3        = 4
|ingredient_icon3 = Embrium.png
|ingredient4      = [[Ambrosia]]
|quantity4        = 1
|ingredient_icon4 = Ambrosia.png
|result           = [[Elixir of Heroism]]
}}</onlyinclude>

== Crafting ==
* It costs {{Currency|80000}} to order an [[Elixir of Heroism]].
"""

_ELFROOT_ITEM_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Elfroot Potion]]
|type        = Potion
|effects     = {{ColorPositiveStat|Health regeneration: 80%}}<br>{{ColorPositiveStat|Injuries: -1}}
|value       = 365.2
}}</onlyinclude>
"""

# Realistic template with empty fields BEFORE the effects field —
# this is the regression case: |image = \n|px = \n triggered the \s*=\s* bug
# where a trailing \n was consumed, causing (.*?) to start at the next field name.
_ITEM_WITH_EMPTY_FIELDS_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Restoration Potion]]
|supertitle  = Usable Item
|icon        = RestorationPotion.png
|image       =
|px          =
|type        = Potion
|restriction =
|effects     = {{ColorPositiveStat|Health regeneration: 80%}}<br>{{ColorPositiveStat|Mana/stamina regeneration: 40%}}
|locations   =
|act         =
|value       = 1000
}}</onlyinclude>
"""

_RUNE_PROTECTION_ITEM_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Rune of Protection]]
|type        = Armor Rune
|effects     = {{ColorPositiveStat|+10% armor}}
|value       = 256.4
}}</onlyinclude>
"""

_HEROISM_ITEM_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Elixir of Heroism]]
|type        = Potion
|effects     = {{ColorPositiveStat|Level: +1 for all party members}}
|value       = 13159
}}</onlyinclude>
"""


def _make_items(entries: list[tuple]) -> list[dict]:
    """Build the items list format expected by parse_recipes / parse_item_effects."""
    result = []
    for name, category, prefix, recipe_wt, item_wt in entries:
        result.append({
            "name": name,
            "category": category,
            "prefix": prefix,
            "recipe_wikitext": recipe_wt,
            "item_wikitext": item_wt,
        })
    return result


# ── TestValueToCurrency ───────────────────────────────────────────────────────

class TestValueToCurrency:
    def test_3750_bronze(self):
        assert value_to_currency("3750") == (0, 37, 50)

    def test_4900_bronze(self):
        assert value_to_currency("4900") == (0, 49, 0)

    def test_80000_bronze(self):
        assert value_to_currency("80000") == (8, 0, 0)

    def test_7500_bronze(self):
        assert value_to_currency("7500") == (0, 75, 0)

    def test_20000_bronze(self):
        assert value_to_currency("20000") == (2, 0, 0)

    def test_6250_bronze(self):
        assert value_to_currency("6250") == (0, 62, 50)

    def test_zero(self):
        assert value_to_currency("0") == (0, 0, 0)


# ── TestCanonicalIngredient ───────────────────────────────────────────────────

class TestCanonicalIngredient:
    def test_elfroot(self):
        assert canonical_ingredient("Elfroot") == "Elfroot"

    def test_elfroot_disambig(self):
        assert canonical_ingredient("Elfroot (Dragon Age II)") == "Elfroot"

    def test_deep_mushroom_disambig(self):
        assert canonical_ingredient("Deep Mushroom (Dragon Age II)") == "Deep Mushroom"

    def test_lyrium_crafting(self):
        assert canonical_ingredient("Lyrium (crafting resource)") == "Lyrium"

    def test_felandaris_disambig(self):
        assert canonical_ingredient("Felandaris (Dragon Age II)") == "Felandaris"

    def test_dragons_blood(self):
        assert canonical_ingredient("Dragon's Blood") == "Dragon's Blood"

    def test_unknown_returns_none(self):
        assert canonical_ingredient("Unknown Ingredient") is None


# ── TestExtractTemplateBlock ──────────────────────────────────────────────────

class TestExtractTemplateBlock:
    def test_finds_recipe_transformer(self):
        block = extract_template_block(_ELFROOT_RECIPE_WT, "RecipeTransformer")
        assert "ingredient1" in block
        assert "Elfroot" in block

    def test_handles_triple_brace_style(self):
        """The {{{style|}}} inside RecipeTransformer must not terminate the block early."""
        block = extract_template_block(_ELFROOT_RECIPE_WT, "RecipeTransformer")
        # Block must include content AFTER the style= line
        assert "ingredient1" in block
        assert "result" in block

    def test_finds_item_transformer(self):
        block = extract_template_block(_ELFROOT_ITEM_WT, "ItemTransformer")
        assert "effects" in block
        assert "ColorPositiveStat" in block

    def test_missing_template_returns_empty(self):
        block = extract_template_block("no template here", "RecipeTransformer")
        assert block == ""


# ── TestParseRecipeLocations ──────────────────────────────────────────────────

class TestParseRecipeLocations:
    @pytest.fixture(scope="class")
    def records(self):
        return parse_recipe_locations(_CRAFTING_WIKITEXT)

    def test_total_count(self, records):
        assert len(records) == 10

    def test_act_1_single(self, records):
        rec = next(r for r in records if r["name"] == "Elfroot Potion")
        assert json.loads(rec["act"]) == {"acts": [1]}

    def test_act_1_3_range(self, records):
        rec = next(r for r in records if r["name"] == "Restoration Potion")
        assert json.loads(rec["act"]) == {"acts": [1, 2, 3]}

    def test_act_2_3_range(self, records):
        rec = next(r for r in records if r["name"] == "Arcane Poison")
        assert json.loads(rec["act"]) == {"acts": [2, 3]}

    def test_act_3(self, records):
        rec = next(r for r in records if r["name"] == "Rune of Devastation")
        assert json.loads(rec["act"]) == {"acts": [3]}

    def test_location_strips_wiki_links(self, records):
        rec = next(r for r in records if r["name"] == "Elfroot Potion")
        # Should strip [[Lady Elegant]] and [[Lowtown]] to plain text
        assert "[[" not in rec["location"]
        assert "Lady Elegant" in rec["location"]
        assert "Lowtown" in rec["location"]

    def test_location_strips_dlc_annotation(self, records):
        rec = next(r for r in records if r["name"] == "Rune of Fortune")
        assert "(DLC)" not in rec["location"]

    def test_no_trailing_period_in_location(self, records):
        for rec in records:
            assert not rec["location"].endswith(".")

    def test_potions_and_runes_and_poisons_present(self, records):
        names = {r["name"] for r in records}
        assert "Elfroot Potion" in names
        assert "Rune of Protection" in names
        assert "Debilitating Poison" in names

    def test_stops_before_resource_locations_section(self, records):
        # The "== Crafting resource locations ==" section must not be parsed
        names = {r["name"] for r in records}
        # These would appear if we kept reading after the crafting recipes section
        # (no items below that section in our fixture, but count should be 10)
        assert len(records) == 10


# ── TestParseResources ────────────────────────────────────────────────────────

class TestParseResources:
    @pytest.fixture(scope="class")
    def records(self):
        return parse_resources(_SUPPLIER_WIKITEXT)

    def test_total_count(self, records):
        # 5 act1 + 3 act2 + 2 act3 = 10
        assert len(records) == 10

    def test_act_1_rows(self, records):
        act1 = [r for r in records if r["act"] == 1]
        assert len(act1) == 5

    def test_act_2_rows(self, records):
        act2 = [r for r in records if r["act"] == 2]
        assert len(act2) == 3

    def test_act_3_rows(self, records):
        act3 = [r for r in records if r["act"] == 3]
        assert len(act3) == 2

    def test_elfroot_display_name(self, records):
        elfrts = [r for r in records if r["name"] == "Elfroot"]
        assert len(elfrts) == 2  # Act 1 + Act 2

    def test_lyrium_display_name(self, records):
        lyr = [r for r in records if r["name"] == "Lyrium"]
        assert len(lyr) == 1

    def test_empty_quest_is_none(self, records):
        bone_pit_elfroot = next(
            r for r in records if r["name"] == "Elfroot" and r["act"] == 1
        )
        assert bone_pit_elfroot["quest"] is None

    def test_quest_with_link(self, records):
        deep_mush = next(r for r in records if r["name"] == "Deep Mushroom")
        assert deep_mush["quest"] == "The Bone Pit"

    def test_description_plain_text(self, records):
        bone_pit_elfroot = next(
            r for r in records if r["name"] == "Elfroot" and r["act"] == 1
        )
        assert "[[" not in bone_pit_elfroot["description"]
        assert "south east" in bone_pit_elfroot["description"]

    def test_felandaris_act3(self, records):
        fel = next(r for r in records if r["name"] == "Felandaris")
        assert fel["act"] == 3

    def test_dragons_blood_act3(self, records):
        db = next(r for r in records if r["name"] == "Dragon's Blood")
        assert db["act"] == 3


# ── TestParseRecipes ──────────────────────────────────────────────────────────

class TestParseRecipes:
    @pytest.fixture(scope="class")
    def records(self):
        items = _make_items([
            ("Elfroot Potion",    "potions", "Recipe", _ELFROOT_RECIPE_WT,    ""),
            ("Restoration Potion","potions", "Recipe", _RESTORATION_RECIPE_WT,""),
            ("Rune of Devastation","runes",  "Design", _DEVASTATION_RECIPE_WT,""),
            ("Elixir of Heroism", "potions", "Recipe", _HEROISM_RECIPE_WT,    ""),
        ])
        return parse_recipes(items)

    def test_record_count(self, records):
        assert len(records) == 4

    def test_elfroot_potion_ingredients(self, records):
        rec = next(r for r in records if r["name"] == "Elfroot Potion")
        assert rec["Elfroot"] == 1
        assert rec["Spindleweed"] == 0
        assert rec["Lyrium"] == 0

    def test_restoration_two_ingredients(self, records):
        rec = next(r for r in records if r["name"] == "Restoration Potion")
        assert rec["Elfroot"] == 3
        assert rec["Spindleweed"] == 2
        assert rec["Deathroot"] == 0

    def test_devastation_four_ingredients(self, records):
        rec = next(r for r in records if r["name"] == "Rune of Devastation")
        assert rec["Lyrium"] == 3
        assert rec["Silverite"] == 4
        assert rec["Orichalcum"] == 4
        assert rec["Dragon's Blood"] == 1
        assert rec["Elfroot"] == 0

    def test_heroism_ambrosia_and_embrium(self, records):
        rec = next(r for r in records if r["name"] == "Elixir of Heroism")
        assert rec["Elfroot"] == 5
        assert rec["Spindleweed"] == 4
        assert rec["Embrium"] == 4
        assert rec["Ambrosia"] == 1

    def test_elfroot_potion_cost(self, records):
        rec = next(r for r in records if r["name"] == "Elfroot Potion")
        assert rec["Gold"] == 0
        assert rec["Silver"] == 37
        assert rec["Bronze"] == 50

    def test_restoration_cost(self, records):
        rec = next(r for r in records if r["name"] == "Restoration Potion")
        assert rec["Gold"] == 0
        assert rec["Silver"] == 49
        assert rec["Bronze"] == 0

    def test_heroism_cost(self, records):
        rec = next(r for r in records if r["name"] == "Elixir of Heroism")
        assert rec["Gold"] == 8
        assert rec["Silver"] == 0
        assert rec["Bronze"] == 0

    def test_devastation_cost(self, records):
        rec = next(r for r in records if r["name"] == "Rune of Devastation")
        assert rec["Gold"] == 0
        assert rec["Silver"] == 75
        assert rec["Bronze"] == 0

    def test_all_ingredient_columns_present(self, records):
        expected_cols = {
            "name", "Ambrosia", "Deathroot", "Deep Mushroom", "Dragon's Blood",
            "Elfroot", "Embrium", "Felandaris", "Glitterdust",
            "Lyrium", "Orichalcum", "Silverite", "Spindleweed",
            "Gold", "Silver", "Bronze",
        }
        assert set(records[0].keys()) == expected_cols


# ── TestParseItemEffects ──────────────────────────────────────────────────────

class TestParseItemEffects:
    @pytest.fixture(scope="class")
    def records(self):
        items = _make_items([
            ("Elfroot Potion",    "potions", "Recipe", "", _ELFROOT_ITEM_WT),
            ("Rune of Protection","runes",   "Design", "", _RUNE_PROTECTION_ITEM_WT),
            ("Elixir of Heroism", "potions", "Recipe", "", _HEROISM_ITEM_WT),
        ])
        return parse_item_effects(items)

    def test_record_count(self, records):
        assert len(records) == 3

    def test_elfroot_multi_effect(self, records):
        rec = next(r for r in records if r["name"] == "Elfroot Potion")
        assert "Health regeneration: 80%" in rec["effects"]
        assert "Injuries: -1" in rec["effects"]

    def test_elfroot_effects_joined_with_semicolon(self, records):
        rec = next(r for r in records if r["name"] == "Elfroot Potion")
        assert ";" in rec["effects"]

    def test_rune_single_effect(self, records):
        rec = next(r for r in records if r["name"] == "Rune of Protection")
        assert rec["effects"] == "+10% armor"

    def test_heroism_effect(self, records):
        rec = next(r for r in records if r["name"] == "Elixir of Heroism")
        assert "Level: +1 for all party members" in rec["effects"]

    def test_no_colorpositiveStat_markup_in_output(self, records):
        for rec in records:
            assert "ColorPositiveStat" not in rec["effects"]

    def test_no_wiki_braces_in_output(self, records):
        for rec in records:
            assert "{{" not in rec["effects"]


# ── TestEmptyFieldsRegression ─────────────────────────────────────────────────

class TestEmptyFieldsRegression:
    """Regression for the \\s*=\\s* bug: empty-value fields consume a trailing \\n,
    causing (.*?) to start on the NEXT field's name and capture it as the value.

    Fixed by using [ \\t]*=[ \\t]* so newlines are never consumed by the = whitespace."""

    def test_effects_not_captured_as_empty_when_preceded_by_empty_fields(self):
        """Template with |image = \\n|px = \\n|restriction = \\n before |effects =
        must still yield the correct effects value."""
        items = _make_items([
            ("Restoration Potion", "potions", "Recipe", "", _ITEM_WITH_EMPTY_FIELDS_WT),
        ])
        records = parse_item_effects(items)
        assert len(records) == 1
        rec = records[0]
        assert rec["name"] == "Restoration Potion"
        assert "Health regeneration: 80%" in rec["effects"]
        assert "Mana/stamina regeneration: 40%" in rec["effects"]

    def test_effects_field_not_mixed_into_restriction_field(self):
        """Before the fix, 'restriction' captured '|effects = ...' as its value.
        After the fix, restriction must be empty."""
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location(
            "da2_parse_crafting_inner",
            Path(__file__).parent.parent.parent.parent.parent /
            "DA/DA2/crafting/crafting_json/da2_parse_crafting.py"
        )
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
        block = _mod.extract_template_block(_ITEM_WITH_EMPTY_FIELDS_WT, "ItemTransformer")
        fields = _mod.parse_template_fields(block)
        assert fields.get("restriction", "") == ""
        assert "ColorPositiveStat" in fields.get("effects", "")

    def test_no_field_captures_pipe_as_value_prefix(self):
        """No field value should begin with '|' (which would mean the next field
        name was incorrectly swallowed as the previous field's value)."""
        items = _make_items([
            ("Restoration Potion", "potions", "Recipe", "", _ITEM_WITH_EMPTY_FIELDS_WT),
        ])
        records = parse_item_effects(items)
        for rec in records:
            assert not rec["effects"].startswith("|")
