"""Tests for skyrim_scrape_disenchant (scraper) and both JSON parsers."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import load_module, REPO_ROOT

SCRAPER_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/disenchant_parse/skyrim_scrape_disenchant.py')
APPAREL_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/disenchant_apparel_json/skyrim_parse_disenchant_apparel_to_json.py')
WEAPONS_SCRIPT = str(REPO_ROOT / 'TES/Skyrim/enchanting/disenchant_weapons_json/skyrim_parse_disenchant_weapons_to_json.py')

_scraper = load_module(
    'TES/Skyrim/enchanting/disenchant_parse/skyrim_scrape_disenchant.py',
    'sk_disenchant_scraper',
)
_app_parser = load_module(
    'TES/Skyrim/enchanting/disenchant_apparel_json/skyrim_parse_disenchant_apparel_to_json.py',
    'sk_disenchant_apparel_parse',
)
_wpn_parser = load_module(
    'TES/Skyrim/enchanting/disenchant_weapons_json/skyrim_parse_disenchant_weapons_to_json.py',
    'sk_disenchant_weapons_parse',
)


def _li(html: str):
    """Parse a single <li> HTML fragment into a BS4 Tag."""
    return BeautifulSoup(html, 'html.parser').find('li')


def _section(html: str):
    """Wrap HTML in a minimal wikitable structure for section parsers."""
    return BeautifulSoup(
        f'<table class="wikitable"><tr><th><a href="/wiki/Skyrim:Test_Effect">Test</a></th>'
        f'<td><div class="mw-collapsible"><div class="mw-collapsible-content">'
        f'{html}</div></div></td></tr></table>',
        'html.parser',
    )


def run(script, args):
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


# ===========================================================================
# _parse_apparel_li — pattern tests
# ===========================================================================

def test_apparel_generic_link_and_includes():
    """Generic types with link + Includes sub-note → All levels of enchantment."""
    li = _li(
        '<li>All varieties of Bracers/Gauntlets and Helmets '
        '<i><a href="/wiki/Skyrim:X" title="Skyrim:X">of Alchemy</a></i>'
        '<ul><li>Includes the enchantments of [Minor/Peerless] Alchemy</li></ul></li>'
    )
    recs = _scraper._parse_apparel_li('Fortify Alchemy', li)
    items = {r['item'] for r in recs}
    assert items == {'Bracers of Alchemy', 'Gauntlets of Alchemy', 'Helmets of Alchemy'}
    assert all(r['note'] == 'All levels of enchantment' for r in recs)
    assert all(r['effect'] == 'Fortify Alchemy' for r in recs)


def test_apparel_generic_slash_split():
    """Slash-separated types are expanded into individual records."""
    li = _li(
        '<li>All varieties of Boots/Shoes <i>of Sneaking</i></li>'
    )
    recs = _scraper._parse_apparel_li('Fortify Sneak', li)
    assert {r['item'] for r in recs} == {'Boots of Sneaking', 'Shoes of Sneaking'}


def test_apparel_generic_no_subnote_note_is_none():
    """Generic item without Includes sub-note → note is None."""
    li = _li(
        '<li>All varieties of Armor, Necklaces, and Rings '
        '<i><a href="/wiki/Skyrim:X" title="Skyrim:X">of Mending</a></i></li>'
    )
    recs = _scraper._parse_apparel_li('Regenerate Health', li)
    assert len(recs) == 3
    assert all(r['note'] is None for r in recs)


def test_apparel_multiple_italic_keywords():
    """Multiple <i> keywords in one <li> → one record per keyword × item-type."""
    li = _li(
        '<li>All varieties of Necklaces and Shields '
        '<i><a href="/wiki/Skyrim:X" title="Skyrim:X">of Dwindling Magic</a></i>, '
        '<i>of Resist Magic</i></li>'
    )
    recs = _scraper._parse_apparel_li('Resist Magic', li)
    items = {r['item'] for r in recs}
    assert 'Necklaces of Dwindling Magic' in items
    assert 'Shields of Dwindling Magic' in items
    assert 'Necklaces of Resist Magic' in items
    assert 'Shields of Resist Magic' in items
    assert len(recs) == 4


def test_apparel_named_item_no_note():
    """Plain named item → item from link title, note None."""
    li = _li('<li><a href="/wiki/Skyrim:X" title="Skyrim:Muiri\'s Ring">Muiri\'s Ring</a></li>')
    recs = _scraper._parse_apparel_li('Fortify Alchemy', li)
    assert len(recs) == 1
    assert recs[0]['item'] == "Muiri's Ring"
    assert recs[0]['note'] is None


def test_apparel_named_item_with_subnote():
    """Named item with sub-list note → note taken from sub-list text."""
    li = _li(
        '<li><a href="/wiki/Skyrim:X" title="Skyrim:Ring of Pure Mixtures">Ring of Pure Mixtures</a>'
        '<ul><li>This item cannot be disenchanted while the quest is active.</li></ul></li>'
    )
    recs = _scraper._parse_apparel_li('Fortify Alchemy', li)
    assert len(recs) == 1
    assert 'cannot be disenchanted' in recs[0]['note']


def test_apparel_bug_note():
    """Bug sentence → item from embedded link, note = 'This is due to a bug.'"""
    li = _li(
        '<li>Due to a bug, the '
        '<a href="/wiki/Skyrim:X" title="Skyrim:Dwarven Helmet of Eminent Alteration">'
        'Dwarven Helmet of Eminent Alteration</a> also has an alchemy enchantment</li>'
    )
    recs = _scraper._parse_apparel_li('Fortify Alchemy', li)
    assert len(recs) == 1
    assert recs[0]['item'] == 'Dwarven Helmet of Eminent Alteration'
    assert recs[0]['note'] == 'This is due to a bug.'


def test_apparel_cc_item_two_variants():
    """CC item 'Elite and Ascendant X' → two records with 'Creation Club content' note."""
    li = _li(
        '<li>Elite and Ascendant '
        '<i><a href="/wiki/Skyrim:X" title="Skyrim:Necromancer Hood">Necromancer Hoods</a></i>'
        '<sup><a href="/wiki/Skyrim:CC">CC</a></sup></li>'
    )
    recs = _scraper._parse_apparel_li('Dark Moon', li)
    assert len(recs) == 2
    items = {r['item'] for r in recs}
    assert 'Elite Necromancer Hood' in items
    assert 'Ascendant Necromancer Hood' in items
    assert all(r['note'] == 'Creation Club content' for r in recs)


def test_apparel_most_varieties_with_includes():
    """'Most' varieties + Includes sub-note → 'Most varieties; all levels of enchantment'."""
    li = _li(
        '<li><b>Most</b> varieties of Armor and Necklaces '
        '<i><a href="/wiki/Skyrim:X" title="Skyrim:X">of the Knight</a></i>'
        '<ul><li>Includes the enchantments of the [Minor/Peerless] Knight</li></ul></li>'
    )
    recs = _scraper._parse_apparel_li('Fortify Heavy Armor', li)
    assert len(recs) == 2
    assert all(r['note'] == 'Most varieties; all levels of enchantment' for r in recs)


def test_apparel_context_note_passed_to_named_item():
    """Named item without its own note inherits the context_note."""
    li = _li('<li><a href="/wiki/Skyrim:X" title="Skyrim:Shield of Solitude">Shield of Solitude</a></li>')
    recs = _scraper._parse_apparel_li(
        'Resist Magic', li,
        context_note='A second version of the effect is available from one item.',
    )
    assert recs[0]['note'] == 'A second version of the effect is available from one item.'


def test_apparel_single_item_type_no_slash():
    """Single item type (no slash) with keyword."""
    li = _li(
        '<li>All Necklaces <i><a href="/wiki/Skyrim:X" title="Skyrim:X">of Haggling</a></i>'
        '<ul><li>Includes the enchantments of [Minor] Barter</li></ul></li>'
    )
    recs = _scraper._parse_apparel_li('Fortify Barter', li)
    assert len(recs) == 1
    assert recs[0]['item'] == 'Necklaces of Haggling'
    assert recs[0]['note'] == 'All levels of enchantment'


# ===========================================================================
# _parse_weapons_li — pattern tests
# ===========================================================================

def test_weapons_all_weapons_of():
    """'All weapons of X' → item = 'All weapons of X', note = None."""
    li = _li(
        '<li>All weapons '
        '<i><a href="/wiki/Skyrim:X" title="Skyrim:X">of Absorption</a></i></li>'
    )
    recs = _scraper._parse_weapons_li('Absorb Health', li)
    assert len(recs) == 1
    assert recs[0]['item'] == 'All weapons of Absorption'
    assert recs[0]['note'] is None


def test_weapons_all_weapons_no_link():
    """'All weapons of X' with plain italic (no link)."""
    li = _li('<li>All weapons <i>of Consuming</i></li>')
    recs = _scraper._parse_weapons_li('Absorb Health', li)
    assert recs[0]['item'] == 'All weapons of Consuming'


def test_weapons_all_varieties_of_adj():
    """'All varieties of [adj] weapons' → item = '[adj] weapons'."""
    li = _li(
        '<li>All varieties of '
        '<i><a href="/wiki/Skyrim:X" title="Skyrim:X">Blessed</a></i> weapons</li>'
    )
    recs = _scraper._parse_weapons_li('Turn Undead', li)
    assert len(recs) == 1
    assert recs[0]['item'] == 'Blessed weapons'
    assert recs[0]['note'] is None


def test_weapons_named_no_note():
    """Named weapon without note → note = None."""
    li = _li(
        '<li><a href="/wiki/Skyrim:X" title="Skyrim:Blade of Woe">Blade of Woe</a></li>'
    )
    recs = _scraper._parse_weapons_li('Absorb Health', li)
    assert len(recs) == 1
    assert recs[0]['item'] == 'Blade of Woe'
    assert recs[0]['note'] is None


def test_weapons_named_with_hyphen_note():
    """Named weapon with '- note' → note capitalized with period."""
    li = _li(
        '<li><a href="/wiki/Skyrim:X" title="Skyrim:Drainspell Bow">Drainspell Bow</a>'
        ' - has unique version of effect</li>'
    )
    recs = _scraper._parse_weapons_li('Absorb Magicka', li)
    assert len(recs) == 1
    assert recs[0]['item'] == 'Drainspell Bow'
    assert recs[0]['note'] == 'Has unique version of effect.'


def test_weapons_named_with_endash_note():
    """Named weapon with '– note' (en-dash) → note capitalized with period."""
    li = _li(
        '<li><a href="/wiki/Skyrim:X" title="Skyrim:Drainheart Sword">Drainheart Sword</a>'
        ' – has unique version of effect</li>'
    )
    recs = _scraper._parse_weapons_li('Absorb Stamina', li)
    assert recs[0]['note'] == 'Has unique version of effect.'


# ===========================================================================
# parse_apparel_section / parse_weapons_section — integration
# ===========================================================================

APPAREL_HTML = (
    '<table class="wikitable"><tbody>'
    '<tr>'
    '  <th><a href="/wiki/Skyrim:Fortify_Alchemy">Alchemy</a></th>'
    '  <td><div class="mw-collapsible"><div class="mw-collapsible-content">'
    '  <ul>'
    '  <li>All varieties of Bracers and Helmets '
    '      <i><a href="/wiki/Skyrim:X" title="Skyrim:X">of Alchemy</a></i>'
    '      <ul><li>Includes the enchantments of [Minor/Peerless] Alchemy</li></ul>'
    '  </li>'
    '  <li><a href="/wiki/Skyrim:X" title="Skyrim:Muiri\'s Ring">Muiri\'s Ring</a></li>'
    '  </ul>'
    '  </div></div></td>'
    '</tr>'
    '</tbody></table>'
)

WEAPONS_HTML = (
    '<table class="wikitable"><tbody>'
    '<tr>'
    '  <th><a href="/wiki/Skyrim:Absorb_Health">Absorb Health</a></th>'
    '  <td><div class="mw-collapsible"><div class="mw-collapsible-content">'
    '  <ul>'
    '  <li>All weapons <i><a href="/wiki/Skyrim:X" title="Skyrim:X">of Absorption</a></i></li>'
    '  <li><a href="/wiki/Skyrim:X" title="Skyrim:Blade of Woe">Blade of Woe</a></li>'
    '  </ul>'
    '  </div></div></td>'
    '</tr>'
    '</tbody></table>'
)


def test_parse_apparel_section_returns_records():
    soup = BeautifulSoup(APPAREL_HTML, 'html.parser')
    recs = _scraper.parse_apparel_section(soup)
    assert len(recs) == 3  # 2 item-type rows + 1 named item
    effects = {r['effect'] for r in recs}
    assert effects == {'Fortify Alchemy'}


def test_parse_apparel_section_effect_name_from_href():
    soup = BeautifulSoup(APPAREL_HTML, 'html.parser')
    recs = _scraper.parse_apparel_section(soup)
    assert all(r['effect'] == 'Fortify Alchemy' for r in recs)


def test_parse_weapons_section_returns_records():
    soup = BeautifulSoup(WEAPONS_HTML, 'html.parser')
    recs = _scraper.parse_weapons_section(soup)
    assert len(recs) == 2
    items = {r['item'] for r in recs}
    assert 'All weapons of Absorption' in items
    assert 'Blade of Woe' in items


def test_parse_apparel_section_paragraph_context():
    """Paragraph before a ul becomes the context_note for items in that ul."""
    html = (
        '<table class="wikitable"><tbody><tr>'
        '<th><a href="/wiki/Skyrim:Resist_Magic">Resist Magic</a></th>'
        '<td><div class="mw-collapsible"><div class="mw-collapsible-content">'
        '<ul><li>All varieties of Rings <i>of Dwindling Magic</i></li></ul>'
        '<p>A second version is available from one item:</p>'
        '<ul><li><a href="/wiki/Skyrim:X" title="Skyrim:Shield of Solitude">Shield of Solitude</a></li></ul>'
        '</div></div></td></tr></tbody></table>'
    )
    soup = BeautifulSoup(html, 'html.parser')
    recs = _scraper.parse_apparel_section(soup)
    solitude = next(r for r in recs if r['item'] == 'Shield of Solitude')
    assert 'second version' in solitude['note']


def test_parse_apparel_section_strips_effect_suffix():
    """_(effect) suffix is stripped from effect names."""
    html = (
        '<table class="wikitable"><tbody><tr>'
        '<th><a href="/wiki/Skyrim:Muffle_(effect)">Muffle</a></th>'
        '<td><div class="mw-collapsible"><div class="mw-collapsible-content">'
        '<ul><li>All varieties of Boots <i>of Muffling</i></li></ul>'
        '</div></div></td></tr></tbody></table>'
    )
    soup = BeautifulSoup(html, 'html.parser')
    recs = _scraper.parse_apparel_section(soup)
    assert recs[0]['effect'] == 'Muffle'


# ===========================================================================
# helper unit tests
# ===========================================================================

def test_split_item_types_slash():
    assert _scraper._split_item_types('Bracers/Gauntlets') == ['Bracers', 'Gauntlets']


def test_split_item_types_comma_and():
    result = _scraper._split_item_types('Armor, Necklaces and Rings')
    assert result == ['Armor', 'Necklaces', 'Rings']


def test_split_item_types_mixed():
    result = _scraper._split_item_types('Bracers/Gauntlets, Helmets, and Necklaces')
    assert result == ['Bracers', 'Gauntlets', 'Helmets', 'Necklaces']


def test_split_item_types_multi_word():
    result = _scraper._split_item_types('Circlets, and Imperial Helmets')
    assert result == ['Circlets', 'Imperial Helmets']


def test_title_or_text_uses_title():
    soup = BeautifulSoup('<a href="..." title="Skyrim:Muiri\'s Ring">Muiri\'s Ring</a>', 'html.parser')
    link = soup.find('a')
    assert _scraper._title_or_text(link) == "Muiri's Ring"


def test_title_or_text_strips_disambiguation():
    soup = BeautifulSoup('<a title="Skyrim:The Forgemaster\'s Fingers (item)">text</a>', 'html.parser')
    link = soup.find('a')
    assert _scraper._title_or_text(link) == "The Forgemaster's Fingers"


def test_title_or_text_fallback_to_text():
    soup = BeautifulSoup('<a href="...">Blade of Woe</a>', 'html.parser')
    link = soup.find('a')
    assert _scraper._title_or_text(link) == 'Blade of Woe'


# ===========================================================================
# Apparel JSON parser (skyrim_parse_disenchant_apparel_to_json)
# ===========================================================================

APPAREL_SAMPLE = [
    {'effect': 'Fortify Alchemy', 'item': 'Bracers of Alchemy', 'note': 'All levels of enchantment'},
    {'effect': 'Fortify Alchemy', 'item': "Muiri's Ring", 'note': None},
]


def test_app_parser_parse_valid(tmp_path):
    p = tmp_path / 'raw.json'
    p.write_text(json.dumps(APPAREL_SAMPLE))
    result = _app_parser.parse(str(p))
    assert result == APPAREL_SAMPLE


def test_app_parser_parse_missing_key_raises(tmp_path):
    p = tmp_path / 'bad.json'
    p.write_text(json.dumps([{'effect': 'Fortify Alchemy', 'item': 'X'}]))
    with pytest.raises(ValueError, match='note'):
        _app_parser.parse(str(p))


def test_app_parser_parse_empty_effect_raises(tmp_path):
    p = tmp_path / 'bad.json'
    p.write_text(json.dumps([{'effect': '', 'item': 'X', 'note': None}]))
    with pytest.raises(ValueError, match='effect'):
        _app_parser.parse(str(p))


def test_app_parser_parse_not_list_raises(tmp_path):
    p = tmp_path / 'bad.json'
    p.write_text(json.dumps({'effect': 'X'}))
    with pytest.raises(ValueError, match='list'):
        _app_parser.parse(str(p))


def test_app_parser_parse_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        _app_parser.parse(str(tmp_path / 'nonexistent.json'))


def test_app_parser_compute_diff_upsert(tmp_path):
    old = [{'effect': 'A', 'item': 'X', 'note': None}]
    new = [
        {'effect': 'A', 'item': 'X', 'note': 'changed'},
        {'effect': 'A', 'item': 'Y', 'note': None},
    ]
    upsert, delete = _app_parser.compute_diff(old, new)
    assert len(upsert) == 2
    assert len(delete) == 0


def test_app_parser_compute_diff_delete():
    old = [{'effect': 'A', 'item': 'X', 'note': None}]
    new = []
    upsert, delete = _app_parser.compute_diff(old, new)
    assert len(upsert) == 0
    assert len(delete) == 1
    assert delete[0]['item'] == 'X'


def test_app_parser_cli_first_run(tmp_path):
    infile = tmp_path / 'raw.json'
    infile.write_text(json.dumps(APPAREL_SAMPLE))
    outfile = tmp_path / 'out.json'
    result = run(APPAREL_SCRIPT, [str(infile), str(outfile)])
    assert result.returncode == 0, result.stderr
    assert outfile.exists()
    assert (tmp_path / 'out.upsert.json').exists()
    assert (tmp_path / 'out.delete.json').exists()


def test_app_parser_cli_no_change(tmp_path):
    infile = tmp_path / 'raw.json'
    infile.write_text(json.dumps(APPAREL_SAMPLE))
    outfile = tmp_path / 'out.json'
    outfile.write_text(json.dumps(APPAREL_SAMPLE))
    result = run(APPAREL_SCRIPT, [str(infile), str(outfile)])
    assert result.returncode == 0
    assert not (tmp_path / 'out.upsert.json').exists()


def test_app_parser_cli_missing_input(tmp_path):
    result = run(APPAREL_SCRIPT, [str(tmp_path / 'nope.json'), str(tmp_path / 'out.json')])
    assert result.returncode != 0


# ===========================================================================
# Weapons JSON parser (skyrim_parse_disenchant_weapons_to_json)
# ===========================================================================

WEAPONS_SAMPLE = [
    {'effect': 'Absorb Health', 'item': 'All weapons of Absorption', 'note': None},
    {'effect': 'Absorb Health', 'item': 'Blade of Woe', 'note': None},
]


def test_wpn_parser_parse_valid(tmp_path):
    p = tmp_path / 'raw.json'
    p.write_text(json.dumps(WEAPONS_SAMPLE))
    result = _wpn_parser.parse(str(p))
    assert result == WEAPONS_SAMPLE


def test_wpn_parser_compute_diff_upsert():
    old = [{'effect': 'A', 'item': 'X', 'note': None}]
    new = [{'effect': 'A', 'item': 'X', 'note': 'changed'}]
    upsert, delete = _wpn_parser.compute_diff(old, new)
    assert len(upsert) == 1 and upsert[0]['note'] == 'changed'
    assert len(delete) == 0


def test_wpn_parser_cli_first_run(tmp_path):
    infile = tmp_path / 'raw.json'
    infile.write_text(json.dumps(WEAPONS_SAMPLE))
    outfile = tmp_path / 'out.json'
    result = run(WEAPONS_SCRIPT, [str(infile), str(outfile)])
    assert result.returncode == 0, result.stderr
    assert outfile.exists()


def test_wpn_parser_cli_missing_input(tmp_path):
    result = run(WEAPONS_SCRIPT, [str(tmp_path / 'nope.json'), str(tmp_path / 'out.json')])
    assert result.returncode != 0
