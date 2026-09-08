"""Unit tests for awakening_parse_herbalism.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from conftest import REPO_ROOT, load_module

parser = load_module(
    "DA/Awakening/herbalism/herbalism_json/awakening_parse_herbalism.py",
    "awakening_parse_herbalism",
)

parse_recipe = parser.parse_recipe
classify_effect = parser.classify_effect
parse_crafted_item_effects = parser.parse_crafted_item_effects


# ─── parse_recipe ─────────────────────────────────────────────────────────────

_MASTER_HEALTH_WIKITEXT = """\
<onlyinclude>{{RecipeTransformer
|name        = [[Master Health Poultice Recipe]]
|ingredient1 = [[Elfroot (Origins)|Elfroot]]
|quantity1   = 8
|ingredient2 = [[Flask]]
|quantity2   = 1
|ingredient3 = [[Distillation Agent]]
|quantity3   = 8
|ingredient4 = [[Concentrator Agent]]
|quantity4   = 8
|result      = [[Master Health Poultice]]
|requires    = [[Herbalism#Tiers|Herbalism: Rank 4]]
|item_id     = gxa_im_cft_hrb_405
}}</onlyinclude>
"""

_LESSER_STAMINA_WIKITEXT = """\
<onlyinclude>{{RecipeTransformer
|name        = [[Lesser Stamina Draught Recipe]]
|ingredient1 = [[Deep Mushroom (Origins)|Deep Mushroom]]
|quantity1   = 1
|ingredient2 = [[Flask]]
|quantity2   = 1
|result      = [[Lesser Stamina Draught]]
|requires    = [[Herbalism#Tiers|Herbalism: Rank 4]]
|item_id     = gxa_im_cft_hrb_101
}}</onlyinclude>
"""

_STAMINA_DRAUGHT_WIKITEXT = """\
<onlyinclude>{{RecipeTransformer
|name        = [[Stamina Draught Recipe]]
|ingredient1 = [[Deep Mushroom (Origins)|Deep Mushroom]]
|quantity1   = 2
|ingredient2 = [[Flask]]
|quantity2   = 1
|ingredient3 = [[Distillation Agent]]
|quantity3   = 1
|result      = [[Stamina Draught (Awakening)|Stamina Draught]]
|requires    = [[Herbalism#Tiers|Herbalism: Rank 4]]
|item_id     = gxa_im_cft_hrb_201
}}</onlyinclude>
"""


class TestParseRecipeName:
    def test_name_stripped(self):
        rec = parse_recipe("Master Health Poultice Recipe", _MASTER_HEALTH_WIKITEXT)
        assert rec["name"] == "Master Health Poultice Recipe"

    def test_result_stripped(self):
        rec = parse_recipe("Master Health Poultice Recipe", _MASTER_HEALTH_WIKITEXT)
        assert rec["result"] == "Master Health Poultice"

    def test_piped_link_result(self):
        # "[[Stamina Draught (Awakening)|Stamina Draught]]" → "Stamina Draught"
        rec = parse_recipe("Stamina Draught Recipe", _STAMINA_DRAUGHT_WIKITEXT)
        assert rec["result"] == "Stamina Draught"

    def test_item_id(self):
        rec = parse_recipe("Master Health Poultice Recipe", _MASTER_HEALTH_WIKITEXT)
        assert rec["item_id"] == "gxa_im_cft_hrb_405"

    def test_gxa_prefix(self):
        # All Awakening item IDs use the gxa_ prefix
        rec = parse_recipe("Lesser Stamina Draught Recipe", _LESSER_STAMINA_WIKITEXT)
        assert rec["item_id"].startswith("gxa_")


class TestParseRecipeTier:
    def test_all_tier_4(self):
        for wt, title in [
            (_MASTER_HEALTH_WIKITEXT, "Master Health Poultice Recipe"),
            (_LESSER_STAMINA_WIKITEXT, "Lesser Stamina Draught Recipe"),
        ]:
            rec = parse_recipe(title, wt)
            assert rec["tier"] == 4


class TestParseRecipeIngredients:
    def test_four_ingredient_recipe(self):
        rec = parse_recipe("Master Health Poultice Recipe", _MASTER_HEALTH_WIKITEXT)
        assert rec["ingredient1"] == "Elfroot"
        assert rec["ingredient2"] == "Flask"
        assert rec["ingredient3"] == "Distillation Agent"
        assert rec["ingredient4"] == "Concentrator Agent"

    def test_quantities(self):
        rec = parse_recipe("Master Health Poultice Recipe", _MASTER_HEALTH_WIKITEXT)
        assert rec["quantity1"] == 8
        assert rec["quantity2"] == 1
        assert rec["quantity3"] == 8
        assert rec["quantity4"] == 8

    def test_two_ingredient_recipe(self):
        rec = parse_recipe("Lesser Stamina Draught Recipe", _LESSER_STAMINA_WIKITEXT)
        assert rec["ingredient1"] == "Deep Mushroom"
        assert rec["ingredient2"] == "Flask"
        assert rec["ingredient3"] is None
        assert rec["ingredient4"] is None

    def test_three_ingredient_recipe(self):
        rec = parse_recipe("Stamina Draught Recipe", _STAMINA_DRAUGHT_WIKITEXT)
        assert rec["ingredient1"] == "Deep Mushroom"
        assert rec["ingredient2"] == "Flask"
        assert rec["ingredient3"] == "Distillation Agent"
        assert rec["ingredient4"] is None

    def test_piped_ingredient_link(self):
        # "[[Elfroot (Origins)|Elfroot]]" → "Elfroot"
        rec = parse_recipe("Master Health Poultice Recipe", _MASTER_HEALTH_WIKITEXT)
        assert rec["ingredient1"] == "Elfroot"


# ─── classify_effect ─────────────────────────────────────────────────────────

class TestClassifyEffect:
    # Health
    def test_superb_health(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 5 health")
        assert t == "Health"
        assert p == 250.0

    def test_master_health(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 6 health")
        assert t == "Health"
        assert p == 300.0

    # Mana
    def test_superb_mana(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 5 mana")
        assert t == "Mana"
        assert p == 250.0

    def test_master_mana(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 6 mana")
        assert t == "Mana"
        assert p == 300.0

    # Stamina (new in Awakening)
    def test_lesser_stamina_no_multiplier(self):
        t, p = classify_effect("Instantly restores (50 + SP) stamina")
        assert t == "Stamina"
        assert p == 50.0

    def test_stamina_multiplier_2(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 2 stamina")
        assert t == "Stamina"
        assert p == 100.0

    def test_stamina_multiplier_3(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 3 stamina")
        assert t == "Stamina"
        assert p == 150.0

    def test_stamina_multiplier_4(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 4 stamina")
        assert t == "Stamina"
        assert p == 200.0

    def test_stamina_multiplier_5(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 5 stamina")
        assert t == "Stamina"
        assert p == 250.0

    def test_stamina_multiplier_6(self):
        t, p = classify_effect("Instantly restores (50 + SP) * 6 stamina")
        assert t == "Stamina"
        assert p == 300.0

    def test_unknown_returns_none_none(self):
        t, p = classify_effect("Grants +10 to all attributes")
        assert t is None
        assert p is None


# ─── parse_crafted_item_effects ───────────────────────────────────────────────

_EFFECTS_WIKITEXT = """\
=== Dragon Age: Origins - Awakening ===
All recipes that are new in Awakening are Tier Four.

{| class="daotable"
|-
! width="25%" | Name
! width="25%" | Effect
|-
| [[Superb Health Poultice]] || Instantly restores (50 + SP) * 5 health
|-
| [[Master Health Poultice]] || Instantly restores (50 + SP) * 6 health
|-
| [[Superb Lyrium Potion]] || Instantly restores (50 + SP) * 5 mana
|-
| [[Master Lyrium Potion]] || Instantly restores (50 + SP) * 6 mana
|-
| [[Lesser Stamina Draught]] || Instantly restores (50 + SP) stamina
|-
| [[Stamina Draught]] || Instantly restores (50 + SP) * 2 stamina
|-
| [[Greater Stamina Draught]] || Instantly restores (50 + SP) * 3 stamina
|-
| [[Potent Stamina Draught]] || Instantly restores (50 + SP) * 4 stamina
|-
| [[Superb Stamina Draught]] || Instantly restores (50 + SP) * 5 stamina
|-
| [[Master Stamina Draught]] || Instantly restores (50 + SP) * 6 stamina
|}
"""


class TestParseCraftedItemEffects:
    def setup_method(self):
        self.records = parse_crafted_item_effects(_EFFECTS_WIKITEXT)

    def test_total_count(self):
        assert len(self.records) == 10

    def test_health_type(self):
        r = next(r for r in self.records if r["name"] == "Master Health Poultice")
        assert r["type"] == "Health"
        assert r["power"] == 300.0

    def test_mana_type(self):
        r = next(r for r in self.records if r["name"] == "Superb Lyrium Potion")
        assert r["type"] == "Mana"
        assert r["power"] == 250.0

    def test_stamina_type_no_multiplier(self):
        r = next(r for r in self.records if r["name"] == "Lesser Stamina Draught")
        assert r["type"] == "Stamina"
        assert r["power"] == 50.0

    def test_stamina_type_with_multiplier(self):
        r = next(r for r in self.records if r["name"] == "Greater Stamina Draught")
        assert r["type"] == "Stamina"
        assert r["power"] == 150.0

    def test_all_have_effects_text(self):
        for r in self.records:
            assert r["effects"] is not None
            assert "restores" in r["effects"].lower()

    def test_six_stamina_items(self):
        stamina = [r for r in self.records if r["type"] == "Stamina"]
        assert len(stamina) == 6

    def test_two_health_items(self):
        health = [r for r in self.records if r["type"] == "Health"]
        assert len(health) == 2

    def test_two_mana_items(self):
        mana = [r for r in self.records if r["type"] == "Mana"]
        assert len(mana) == 2
