"""
Unit tests for awakening_parse_runecrafting.py

Covers:
  - parse_wiki_cell
  - strip_wiki_markup
  - extract_sources
  - parse_item_transformer
  - parse_effects
  - value_to_currency
  - parse_rune_page_name
  - parse_daotable_rows
  - parse_tiers
  - parse_tracing
  - parse_rune_entries
  - parse_costs
"""

import json
import pytest
from conftest import REPO_ROOT, load_module

mod = load_module(
    "DA/Awakening/runecrafting/runecrafting_json/awakening_parse_runecrafting.py",
    "awakening_parse_runecrafting",
)

parse_wiki_cell      = mod.parse_wiki_cell
strip_wiki_markup    = mod.strip_wiki_markup
extract_sources      = mod.extract_sources
parse_item_transformer = mod.parse_item_transformer
parse_effects        = mod.parse_effects
value_to_currency    = mod.value_to_currency
parse_rune_page_name = mod.parse_rune_page_name
parse_daotable_rows  = mod.parse_daotable_rows
parse_tiers          = mod.parse_tiers
parse_tracing        = mod.parse_tracing
parse_rune_entries   = mod.parse_rune_entries
parse_costs          = mod.parse_costs


# ── fixtures ─────────────────────────────────────────────────────────────────

_TIERS_WIKITEXT = """\
== Tiers ==
{| class="daotable"
|- style="background: #333333"
! colspan=4 style="background-color:#523F35" | Skill Tiers
|-
! Skill Level || Character Level || Rune Levels || Description
|-
|[[File:Runecrafting.png|Runecrafting|left]]'''Runecrafting'''
| 20
| Journeyman, Expert
| Basic runecrafting.
|-
|[[File:Improved_Runecrafting.png|Improved Runecrafting|left]]'''Improved Runecrafting'''
| 22
| Master
| Intermediate runecrafting.
|-
|[[File:Expert_Runecrafting.png|Expert Runecrafting|left]]'''Expert Runecrafting'''
| 24
| Grandmaster, Masterpiece
| Advanced runecrafting.
|-
|[[File:Master_Runecrafting.png|Master Runecrafting|left]]'''Master Runecrafting'''
| 26
| Paragon
| Master runecrafting.
|-
|}
"""

_TRACING_WIKITEXT = """\
== Tracing acquisition ==
{| class="daotable"
|- style="background: #333333"
! colspan=8 style="background-color:#523F35" | Rune Tracing Acquisition
|-
! Tracing || Type || Journeyman || Expert || Master || Grandmaster || Masterpiece || Paragon
|-
| class="title" | Flame
| Weapon
| Initial
| [[Cera]]
| [[Cera]]
| [[Cera]]
| [[Kal'Hirol - Trade Quarter]]
| [[Kal'Hirol - Trade Quarter]]
|-
| class="title" | Dweomer
| Weapon
| [[Cera]], [[Octham]]
| [[Octham]]
| [[Octham]]
| [[Yuriah|Yuriah (+1 upgrade)]]
| [[Yuriah|Yuriah (+2 upgrades)]]
| [[Yuriah|Yuriah (+3 upgrades)]]
|-
| class="title" | Reservoir
| Armor
| [[Cera]], [[Glassric]]
| [[Glassric]]
| [[Cera]], [[Glassric]]
| [[Yuriah|Yuriah (+1 upgrade)]]
| [[Yuriah|Yuriah (+2 upgrades)]]
| [[Yuriah|Yuriah (+2 upgrades)]]
|}
<references />

{| class="daotable"
|- style="background: #333333"
! colspan=3 style="background-color:#523F35" | Hybrid Rune Tracing Acquisition
|-
! Tracing || Type || Location
|-
| class="title" | [[Intensifying Rune|Intensifying]]
| Weapon
| [[Bartender (Awakening)|Bartender at The Crown and Lion.]]
|-
| class="title" | [[Endurance Rune|Endurance]]
| Armor
| [[Yuriah|Yuriah (+1 upgrade)]]
|-
| class="title" | [[Diligence Rune|Diligence]]
| Armor
| [[Blackmarsh]]
|}
"""

_BARRIER_NOVICE_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Novice Barrier Rune]]
|description = The [[Tevinter Imperium|Tevinter]] symbol for protection.
|type        = [[Runes (Origins)|Rune]] - [[Armor runes (Awakening)|Armor rune]]
|value       = 6500
|icon        = Ru evasion.png
|effects     = {{ColorPositiveStat|+1 armor}}
|locations   = [[Vigil's Keep - Basement]]
|item_id     = gxa_im_upg_run_ar1_arm
|appearances = [[Dragon Age: Origins - Awakening]]
}}</onlyinclude>
"""

_INTENSIFYING_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Intensifying Rune]]
|description = No word precisely captures this rune, but it is something like "bigger".
|type        = [[Runes (Origins)|Rune]] - [[Weapon runes (Origins)|Weapon rune]]
|value       = 150000
|icon        = Momentum_rune.png
|effects     = {{ColorPositiveStat|5% ranged critical chance <br> 5% melee critical chance <br> 20% critical/backstab damage}}
|item_id     = gxa_im_upg_run_wn_int
|appearances = [[Dragon Age: Origins - Awakening]]
}}</onlyinclude>
"""

_BLANK_RUNESTONE_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Blank Runestone]]
|description = This stone is incredibly thin, yet not brittle at all.
|type        = [[Ingredients|Ingredient]]
|value       = 50
|icon        = blank_runestone.png
|item_id     = gxa_im_cft_reg_blankrune
|appearances = [[Dragon Age: Origins - Awakening]]
}}</onlyinclude>
"""

_ETCHING_AGENT_WT = """\
<onlyinclude>{{ItemTransformer
|style        = {{{style|}}}
|name         = [[Etching Agent]]
|description  = A caustic substance.
|type         = [[Ingredients|Ingredient]]
|value        = 800
|icon         = etching_agent.png
|item_id      = gxa_im_cft_reg_reduction
|appearances  = [[Dragon Age: Origins - Awakening]]
}}</onlyinclude>
"""

_FLAME_NOVICE_WT = """\
<onlyinclude>{{ItemTransformer
|style       = {{{style|}}}
|name        = [[Novice Flame Rune]]
|description = Ancient Tevinter symbol for Toth, god of fire.
|type        = [[Runes (Origins)|Rune]] - [[Weapon runes (Origins)|Weapon rune]]
|value       = 6000
|icon        = ru_flame_novice.png
|effects     = {{ColorPositiveStat|+1 Fire Damage}}
|item_id     = gxa_im_upg_run_wn_fl1
|appearances = [[Dragon Age: Origins - Awakening]]
}}</onlyinclude>
"""


# ── TestParseWikiCell ─────────────────────────────────────────────────────────

class TestParseWikiCell:
    def test_plain_cell(self):
        assert parse_wiki_cell("| Weapon") == "Weapon"

    def test_class_title_cell(self):
        assert parse_wiki_cell('| class="title" | Flame') == "Flame"

    def test_link_cell(self):
        result = parse_wiki_cell("| [[Cera]]")
        assert result == "[[Cera]]"

    def test_non_cell_returns_none(self):
        assert parse_wiki_cell("! Header") is None

    def test_link_with_display(self):
        result = parse_wiki_cell("| [[Yuriah|Yuriah (+1 upgrade)]]")
        assert result == "[[Yuriah|Yuriah (+1 upgrade)]]"


# ── TestStripWikiMarkup ───────────────────────────────────────────────────────

class TestStripWikiMarkup:
    def test_file_link_removed(self):
        text = "[[File:Runecrafting.png|Runecrafting|left]]'''Runecrafting'''"
        assert strip_wiki_markup(text) == "Runecrafting"

    def test_page_link_replaced_with_display(self):
        text = "[[Tevinter Imperium|Tevinter]] symbol"
        assert strip_wiki_markup(text) == "Tevinter symbol"

    def test_plain_link(self):
        assert strip_wiki_markup("[[Cera]]") == "Cera"

    def test_bold_stripped(self):
        assert strip_wiki_markup("'''Improved Runecrafting'''") == "Improved Runecrafting"

    def test_plain_text_unchanged(self):
        assert strip_wiki_markup("Initial") == "Initial"


# ── TestExtractSources ────────────────────────────────────────────────────────

class TestExtractSources:
    def test_initial(self):
        assert extract_sources("Initial") == ["Initial"]

    def test_single_link(self):
        assert extract_sources("[[Cera]]") == ["Cera"]

    def test_multiple_links(self):
        assert extract_sources("[[Cera]], [[Octham]]") == ["Cera", "Octham"]

    def test_yuriah_with_upgrade(self):
        result = extract_sources("[[Yuriah|Yuriah (+1 upgrade)]]")
        assert result == ["Yuriah (+1 upgrade)"]

    def test_yuriah_three_upgrades(self):
        result = extract_sources("[[Yuriah|Yuriah (+3 upgrades)]]")
        assert result == ["Yuriah (+3 upgrades)"]

    def test_bartender_display(self):
        result = extract_sources(
            "[[Bartender (Awakening)|Bartender at The Crown and Lion.]]"
        )
        assert result == ["Bartender at The Crown and Lion."]

    def test_location_and_yuriah(self):
        result = extract_sources("[[Vigil's Keep - Throne Room]], [[Yuriah]]")
        assert result == ["Vigil's Keep - Throne Room", "Yuriah"]


# ── TestParseItemTransformer ──────────────────────────────────────────────────

class TestParseItemTransformer:
    def test_name_extracted(self):
        fields = parse_item_transformer(_BARRIER_NOVICE_WT)
        assert "Novice Barrier Rune" in fields.get("name", "")

    def test_value_extracted(self):
        fields = parse_item_transformer(_BARRIER_NOVICE_WT)
        assert fields.get("value") == "6500"

    def test_effects_extracted(self):
        fields = parse_item_transformer(_BARRIER_NOVICE_WT)
        assert "+1 armor" in fields.get("effects", "")

    def test_description_extracted(self):
        fields = parse_item_transformer(_BARRIER_NOVICE_WT)
        assert "protection" in fields.get("description", "")

    def test_no_template_returns_empty(self):
        assert parse_item_transformer("plain text") == {}


# ── TestParseEffects ──────────────────────────────────────────────────────────

class TestParseEffects:
    def test_single_effect(self):
        raw = "{{ColorPositiveStat|+1 armor}}"
        assert parse_effects(raw) == ["+1 armor"]

    def test_multi_effect_br(self):
        raw = ("{{ColorPositiveStat|5% ranged critical chance "
               "<br> 5% melee critical chance <br> 20% critical/backstab damage}}")
        result = parse_effects(raw)
        assert len(result) == 3
        assert result[0] == "5% ranged critical chance"
        assert result[2] == "20% critical/backstab damage"

    def test_single_effect_weapon(self):
        raw = "{{ColorPositiveStat|+1 Fire Damage}}"
        assert parse_effects(raw) == ["+1 Fire Damage"]

    def test_br_slash_variant(self):
        raw = "{{ColorPositiveStat|A<br/>B}}"
        result = parse_effects(raw)
        assert result == ["A", "B"]

    def test_empty_string(self):
        assert parse_effects("") == []


# ── TestValueToCurrency ───────────────────────────────────────────────────────

class TestValueToCurrency:
    def test_bronze_only(self):
        assert value_to_currency("50") == (0, 0, 50)

    def test_silver_only(self):
        assert value_to_currency("800") == (0, 8, 0)

    def test_silver_and_bronze(self):
        assert value_to_currency("6500") == (0, 65, 0)

    def test_large_value(self):
        # 125000 bronze = 12 gold, 50 silver, 0 bronze
        assert value_to_currency("125000") == (12, 50, 0)

    def test_flame_novice(self):
        assert value_to_currency("6000") == (0, 60, 0)

    def test_mixed_all_denominations(self):
        # 12345 = 1 gold, 23 silver, 45 bronze
        assert value_to_currency("12345") == (1, 23, 45)


# ── TestParseRunePageName ─────────────────────────────────────────────────────

class TestParseRunePageName:
    def test_novice_barrier(self):
        assert parse_rune_page_name("Novice Barrier Rune") == ("Barrier", "Novice")

    def test_paragon_cold_iron(self):
        assert parse_rune_page_name("Paragon Cold Iron Rune") == ("Cold Iron", "Paragon")

    def test_grandmaster_stout(self):
        assert parse_rune_page_name("Grandmaster Stout Rune") == ("Stout", "Grandmaster")

    def test_hybrid_evasion(self):
        name, level = parse_rune_page_name("Evasion Rune")
        assert name == "Evasion"
        assert level is None

    def test_hybrid_intensifying(self):
        name, level = parse_rune_page_name("Intensifying Rune")
        assert name == "Intensifying"
        assert level is None

    def test_masterpiece_dweomer(self):
        assert parse_rune_page_name("Masterpiece Dweomer Rune") == ("Dweomer", "Masterpiece")


# ── TestParseTiers ────────────────────────────────────────────────────────────

class TestParseTiers:
    def setup_method(self):
        self.records = parse_tiers(_TIERS_WIKITEXT)

    def test_returns_four_rows(self):
        assert len(self.records) == 4

    def test_first_skill_level(self):
        assert self.records[0]["level"] == "Runecrafting"

    def test_character_level_int(self):
        assert self.records[0]["character_level"] == 20
        assert self.records[1]["character_level"] == 22

    def test_rune_levels_json_valid(self):
        rl = json.loads(self.records[0]["rune_levels"])
        assert "rune_levels" in rl
        assert rl["rune_levels"] == ["Journeyman", "Expert"]

    def test_single_rune_level(self):
        rl = json.loads(self.records[1]["rune_levels"])
        assert rl["rune_levels"] == ["Master"]

    def test_two_rune_levels_second_skill(self):
        rl = json.loads(self.records[2]["rune_levels"])
        assert rl["rune_levels"] == ["Grandmaster", "Masterpiece"]

    def test_paragon_level(self):
        rl = json.loads(self.records[3]["rune_levels"])
        assert rl["rune_levels"] == ["Paragon"]


# ── TestParseTracing ──────────────────────────────────────────────────────────

class TestParseTracing:
    def setup_method(self):
        self.non_hybrid, self.hybrid = parse_tracing(_TRACING_WIKITEXT)

    def test_non_hybrid_count(self):
        assert len(self.non_hybrid) == 3

    def test_flame_tracing(self):
        flame = next(r for r in self.non_hybrid if r["tracing"] == "Flame")
        assert flame["type"] == "Weapon"

    def test_initial_source_stored(self):
        flame = next(r for r in self.non_hybrid if r["tracing"] == "Flame")
        j = json.loads(flame["journeyman"])
        assert j["sources"] == ["Initial"]

    def test_single_source(self):
        flame = next(r for r in self.non_hybrid if r["tracing"] == "Flame")
        ex = json.loads(flame["expert"])
        assert ex["sources"] == ["Cera"]

    def test_multiple_sources(self):
        res = next(r for r in self.non_hybrid if r["tracing"] == "Reservoir")
        j = json.loads(res["journeyman"])
        assert set(j["sources"]) == {"Cera", "Glassric"}

    def test_yuriah_upgrade_preserved(self):
        dw = next(r for r in self.non_hybrid if r["tracing"] == "Dweomer")
        gm = json.loads(dw["grandmaster"])
        assert gm["sources"] == ["Yuriah (+1 upgrade)"]

    def test_yuriah_three_upgrades(self):
        dw = next(r for r in self.non_hybrid if r["tracing"] == "Dweomer")
        pg = json.loads(dw["paragon"])
        assert pg["sources"] == ["Yuriah (+3 upgrades)"]

    def test_hybrid_count(self):
        assert len(self.hybrid) == 3

    def test_hybrid_intensifying(self):
        h = next(r for r in self.hybrid if r["tracing"] == "Intensifying")
        assert h["type"] == "Weapon"
        assert "Crown and Lion" in h["location"]

    def test_hybrid_endurance_yuriah(self):
        h = next(r for r in self.hybrid if r["tracing"] == "Endurance")
        assert "Yuriah" in h["location"]
        assert "+1 upgrade" in h["location"]

    def test_hybrid_diligence_location(self):
        h = next(r for r in self.hybrid if r["tracing"] == "Diligence")
        assert h["location"] == "Blackmarsh"


# ── TestParseRuneEntries ──────────────────────────────────────────────────────

class TestParseRuneEntries:
    def test_non_hybrid_level_set(self):
        pages = [{"page": "Novice Barrier Rune", "wikitext": _BARRIER_NOVICE_WT}]
        records = parse_rune_entries(pages)
        assert len(records) == 1
        assert records[0]["level"] == "Novice"
        assert records[0]["name"] == "Barrier"

    def test_hybrid_level_null(self):
        pages = [{"page": "Intensifying Rune", "wikitext": _INTENSIFYING_WT}]
        records = parse_rune_entries(pages)
        assert records[0]["level"] is None
        assert records[0]["name"] == "Intensifying"

    def test_effect_json_single(self):
        pages = [{"page": "Novice Barrier Rune", "wikitext": _BARRIER_NOVICE_WT}]
        records = parse_rune_entries(pages)
        ef = json.loads(records[0]["effect"])
        assert ef["effects"] == ["+1 armor"]

    def test_effect_json_multi(self):
        pages = [{"page": "Intensifying Rune", "wikitext": _INTENSIFYING_WT}]
        records = parse_rune_entries(pages)
        ef = json.loads(records[0]["effect"])
        assert len(ef["effects"]) == 3
        assert "ranged critical chance" in ef["effects"][0]

    def test_description_cleaned(self):
        pages = [{"page": "Novice Barrier Rune", "wikitext": _BARRIER_NOVICE_WT}]
        records = parse_rune_entries(pages)
        desc = records[0]["description"]
        assert "[[" not in desc
        assert "protection" in desc


# ── TestParseCosts ────────────────────────────────────────────────────────────

class TestParseCosts:
    def setup_method(self):
        armor_pages = [{"page": "Novice Barrier Rune", "wikitext": _BARRIER_NOVICE_WT}]
        weapon_pages = [{"page": "Novice Flame Rune",   "wikitext": _FLAME_NOVICE_WT}]
        support = [
            {"page": "Blank Runestone", "wikitext": _BLANK_RUNESTONE_WT},
            {"page": "Etching Agent",   "wikitext": _ETCHING_AGENT_WT},
        ]
        self.records = parse_costs(armor_pages, weapon_pages, support)

    def test_returns_four_rows(self):
        # 1 armor novice + 1 weapon novice + 2 support items
        assert len(self.records) == 4

    def test_blank_runestone_cost(self):
        r = next(x for x in self.records if x["name"] == "Blank Runestone")
        assert r["gold"] == 0
        assert r["silver"] == 0
        assert r["bronze"] == 50

    def test_etching_agent_cost(self):
        r = next(x for x in self.records if x["name"] == "Etching Agent")
        assert r["gold"] == 0
        assert r["silver"] == 8
        assert r["bronze"] == 0

    def test_barrier_novice_cost(self):
        r = next(x for x in self.records if x["name"] == "Novice Barrier Rune")
        assert r["gold"] == 0
        assert r["silver"] == 65
        assert r["bronze"] == 0

    def test_flame_novice_cost(self):
        r = next(x for x in self.records if x["name"] == "Novice Flame Rune")
        assert r["gold"] == 0
        assert r["silver"] == 60
        assert r["bronze"] == 0

    def test_only_novice_runes_included(self):
        # Higher-level runes should NOT appear in costs
        names = {r["name"] for r in self.records}
        assert "Journeyman Barrier Rune" not in names
        assert "Paragon Flame Rune" not in names
