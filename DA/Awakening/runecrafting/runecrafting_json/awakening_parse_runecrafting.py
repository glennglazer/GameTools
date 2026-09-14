#!/usr/bin/env python3
"""
awakening_parse_runecrafting.py
Parses runecrafting_raw.json (from the Awakening scraper) into six structured
JSON files:

    awakening_runecrafting_skill.json
    awakening_runecrafting_tracing_acquisition.json
    awakening_runecrafting_hybrid_tracing_acquisition.json
    awakening_runecrafting_armor_runes.json
    awakening_runecrafting_weapon_runes.json
    awakening_runecrafting_costs.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

LEVELS = ["Novice", "Journeyman", "Expert", "Master", "Grandmaster", "Masterpiece", "Paragon"]
LEVEL_COLUMNS = [lvl.lower() for lvl in LEVELS[1:]]  # Journeyman..Paragon (tracing table)


# ── low-level wiki helpers ────────────────────────────────────────────────────

def parse_wiki_cell(raw_line: str) -> str | None:
    """Strip leading '|' and optional 'class=...|' attribute prefix from a table cell line."""
    line = raw_line.strip()
    if not line.startswith("|"):
        return None
    content = line[1:].strip()
    # Cell attribute prefix: "class=..." or "style=..." before the content separator
    if content.startswith("class=") or content.startswith("style="):
        sep = content.index("|")
        content = content[sep + 1:].strip()
    return content


def strip_wiki_markup(text: str) -> str:
    """Remove wiki formatting: File links, [[Page|Display]], '''bold''', etc."""
    # File / image links (may contain nested pipes)
    text = re.sub(r"\[\[File:[^\]]+\]\]", "", text)
    # [[Page|Display]] → Display
    text = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", text)
    # [[Page]] → Page
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # Bold / italic markup
    text = re.sub(r"'{2,3}", "", text)
    # <small>...</small>
    text = re.sub(r"</?small>", "", text)
    # <ref ...>...</ref> or <ref ... />
    text = re.sub(r"<ref[^>]*/?>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref[^/]*/?>", "", text)
    return text.strip()


def extract_sources(cell_text: str) -> list[str]:
    """Return a list of source strings from a tracing-acquisition cell.

    Handles:
      'Initial'                              → ['Initial']
      '[[Cera]]'                             → ['Cera']
      '[[Cera]], [[Octham]]'                 → ['Cera', 'Octham']
      '[[Yuriah|Yuriah (+2 upgrades)]]'     → ['Yuriah (+2 upgrades)']
      '[[Bartender (Awakening)|Bartender at The Crown and Lion.]]'
                                             → ['Bartender at The Crown and Lion.']
    """
    cell_text = cell_text.strip()
    if cell_text == "Initial":
        return ["Initial"]
    links = re.findall(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", cell_text)
    sources = []
    for page, display in links:
        sources.append((display.strip() if display else page.strip()))
    # Fallback: plain text with no links
    if not sources and cell_text:
        sources = [cell_text.strip()]
    return sources


def parse_item_transformer(wikitext: str) -> dict:
    """Extract fields from the {{ItemTransformer ...}} template in a rune page.

    Uses depth-counting to find the matching closing '}}' so that nested
    templates like {{{style|}}} and {{ColorPositiveStat|...}} don't confuse
    a simple non-greedy regex.
    """
    marker = "{{ItemTransformer"
    start = wikitext.find(marker)
    if start < 0:
        return {}
    # scan from just after the opening '{{' to find the balanced closing '}}'
    pos = start + 2
    depth = 1
    length = len(wikitext)
    while pos < length:
        two = wikitext[pos : pos + 2]
        if two == "{{":
            depth += 1
            pos += 2
        elif two == "}}":
            depth -= 1
            if depth == 0:
                break
            pos += 2
        else:
            pos += 1
    if depth != 0:
        return {}

    block = wikitext[start + len(marker) : pos]

    # Each field: |key = value ... until the next |key line or end of block.
    # Use [ \t]* (not \s*) around = so a trailing newline on an empty-value
    # field is NOT consumed, preventing (.*?) from capturing the next field name.
    fields: dict[str, str] = {}
    for fm in re.finditer(
        r"\|[ \t]*(\w+)[ \t]*=[ \t]*(.*?)(?=\n[ \t]*\|[a-zA-Z]|\Z)", block, re.DOTALL
    ):
        key = fm.group(1).strip()
        val = fm.group(2).strip()
        fields[key] = val
    return fields


def parse_effects(effects_raw: str) -> list[str]:
    """Parse {{ColorPositiveStat|effect1 <br> effect2}} into a list of clean strings."""
    if not effects_raw:
        return []
    # Extract the content of ColorPositiveStat (handles nested <br> separators)
    m = re.search(r"\{\{ColorPositiveStat\|(.*?)\}\}", effects_raw, re.DOTALL)
    if not m:
        return [strip_wiki_markup(effects_raw)]
    content = m.group(1)
    parts = re.split(r"\s*<br\s*/?>\s*", content)
    return [p.strip() for p in parts if p.strip()]


def value_to_currency(value_str: str) -> tuple[int, int, int]:
    """Convert bronze integer string → (gold, silver, bronze)."""
    v = int(value_str)
    gold = v // 10000
    silver = (v % 10000) // 100
    bronze = v % 100
    return gold, silver, bronze


def parse_rune_page_name(page: str) -> tuple[str, str | None]:
    """Parse '{Level} {Type} Rune' or '{Type} Rune' → (type_name, level | None)."""
    name = page
    if name.endswith(" Rune"):
        name = name[: -len(" Rune")]
    for level in LEVELS:
        if name.startswith(level + " "):
            return name[len(level) + 1 :], level
    return name, None  # hybrid (no level prefix)


# ── daotable parser ───────────────────────────────────────────────────────────

def parse_daotable_rows(table_text: str) -> list[list[str]]:
    """Parse a daotable block into a list of rows (each row = list of cell strings).

    Skips header rows (lines starting with '!').  Each row begins at '|-'.
    """
    rows: list[list[str]] = []
    current: list[str] | None = None

    for raw_line in table_text.split("\n"):
        stripped = raw_line.strip()
        if stripped.startswith("|-"):
            if current is not None:
                rows.append(current)
            current = []
        elif current is not None and stripped.startswith("|") \
                and not stripped.startswith("|}"):
            cell = parse_wiki_cell(stripped)
            if cell is not None:
                current.append(cell)
        # Lines starting with '!' are headers; ignore
    if current:
        rows.append(current)
    return [r for r in rows if r]  # drop empty rows


def find_tables(wikitext: str) -> list[str]:
    """Return a list of daotable blocks from wikitext (content between {| and |})."""
    tables = []
    depth = 0
    start = -1
    i = 0
    while i < len(wikitext):
        if wikitext[i : i + 2] == "{|":
            if depth == 0:
                start = i
            depth += 1
            i += 2
        elif wikitext[i : i + 2] == "|}":
            depth -= 1
            if depth == 0 and start != -1:
                tables.append(wikitext[start : i + 2])
                start = -1
            i += 2
        else:
            i += 1
    return tables


# ── per-section parsers ───────────────────────────────────────────────────────

def parse_tiers(tiers_wikitext: str) -> list[dict]:
    """Parse the Tiers daotable → list of skill tier dicts."""
    tables = find_tables(tiers_wikitext)
    if not tables:
        raise ValueError("No daotable found in tiers section")
    rows = parse_daotable_rows(tables[0])
    records = []
    for row in rows:
        if len(row) < 3:
            continue
        level_raw, char_level_raw, rune_levels_raw = row[0], row[1], row[2]
        level = strip_wiki_markup(level_raw)
        if not level:
            continue
        try:
            char_level = int(char_level_raw.strip())
        except ValueError:
            continue
        rune_levels = [
            lvl.strip() for lvl in rune_levels_raw.split(",") if lvl.strip()
        ]
        records.append({
            "level": level,
            "character_level": char_level,
            "rune_levels": json.dumps({"rune_levels": rune_levels}),
        })
    return records


def parse_tracing(tracing_wikitext: str) -> tuple[list[dict], list[dict]]:
    """Parse both tracing daotables → (non-hybrid records, hybrid records)."""
    tables = find_tables(tracing_wikitext)
    if len(tables) < 2:
        raise ValueError(
            f"Expected 2 daotables in tracing section, found {len(tables)}"
        )

    # ── non-hybrid table (8 columns: Tracing, Type, J, Ex, Ma, Gm, Mp, Pa) ──
    non_hybrid: list[dict] = []
    for row in parse_daotable_rows(tables[0]):
        if len(row) < 8:
            continue
        tracing = strip_wiki_markup(row[0]).strip()
        rune_type = row[1].strip()
        level_cells = row[2:]  # Journeyman … Paragon
        record: dict = {"tracing": tracing, "type": rune_type}
        for col, cell in zip(LEVEL_COLUMNS, level_cells):
            sources = extract_sources(cell)
            record[col] = json.dumps({"sources": sources})
        non_hybrid.append(record)

    # ── hybrid table (3 columns: Tracing, Type, Location) ───────────────────
    hybrid: list[dict] = []
    for row in parse_daotable_rows(tables[1]):
        if len(row) < 3:
            continue
        tracing = strip_wiki_markup(row[0]).strip()
        rune_type = row[1].strip()
        # Location may be a wiki link
        location_sources = extract_sources(row[2])
        location = location_sources[0] if location_sources else row[2].strip()
        hybrid.append({"tracing": tracing, "type": rune_type, "location": location})

    return non_hybrid, hybrid


def parse_rune_entries(rune_pages: list[dict]) -> list[dict]:
    """Parse a list of rune page dicts → list of rune records.

    Each record: name (type name), level (nullable), effect (JSON), description.
    """
    records: list[dict] = []
    for entry in rune_pages:
        page = entry["page"]
        wikitext = entry["wikitext"]
        type_name, level = parse_rune_page_name(page)
        fields = parse_item_transformer(wikitext)
        effects = parse_effects(fields.get("effects", ""))
        description = strip_wiki_markup(fields.get("description", ""))
        records.append({
            "name": type_name,
            "level": level,  # None for hybrids → NULL in DB
            "effect": json.dumps({"effects": effects}),
            "description": description,
        })
    return records


def parse_costs(
    armor_runes: list[dict],
    weapon_runes: list[dict],
    support_items: list[dict],
) -> list[dict]:
    """Build cost records from Novice rune pages + support item pages.

    Stores the sell-value (the 'value' field from ItemTransformer, in bronze).
    Buy price from merchants = sell_value × 1.1 (documented in RAG).
    """
    records: list[dict] = []
    seen: set[str] = set()

    # Novice rune pages from both armor and weapon lists
    all_rune_pages = armor_runes + weapon_runes
    for entry in all_rune_pages:
        _, level = parse_rune_page_name(entry["page"])
        if level != "Novice":
            continue
        page_name = entry["page"]
        fields = parse_item_transformer(entry["wikitext"])
        value_str = fields.get("value", "")
        if not value_str:
            print(f"  WARNING: no value field for '{page_name}'", file=sys.stderr)
            continue
        gold, silver, bronze = value_to_currency(value_str)
        if page_name not in seen:
            records.append({
                "name": page_name,
                "gold": gold,
                "silver": silver,
                "bronze": bronze,
            })
            seen.add(page_name)

    # Support items (Blank Runestone, Etching Agent)
    for entry in support_items:
        page_name = entry["page"]
        fields = parse_item_transformer(entry["wikitext"])
        value_str = fields.get("value", "")
        if not value_str:
            print(f"  WARNING: no value field for '{page_name}'", file=sys.stderr)
            continue
        gold, silver, bronze = value_to_currency(value_str)
        records.append({
            "name": page_name,
            "gold": gold,
            "silver": silver,
            "bronze": bronze,
        })

    return records


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse runecrafting_raw.json into 6 structured JSON files"
    )
    ap.add_argument("raw_json",        help="Input: runecrafting_raw.json")
    ap.add_argument("skill_json",      help="Output: awakening_runecrafting_skill.json")
    ap.add_argument("tracing_json",    help="Output: awakening_runecrafting_tracing_acquisition.json")
    ap.add_argument("hybrid_json",     help="Output: awakening_runecrafting_hybrid_tracing_acquisition.json")
    ap.add_argument("armor_json",      help="Output: awakening_runecrafting_armor_runes.json")
    ap.add_argument("weapon_json",     help="Output: awakening_runecrafting_weapon_runes.json")
    ap.add_argument("costs_json",      help="Output: awakening_runecrafting_costs.json")
    args = ap.parse_args()

    # Validate inputs
    raw_path = Path(args.raw_json)
    if not raw_path.exists():
        print(f"ERROR: raw JSON not found: {raw_path}", file=sys.stderr)
        sys.exit(1)

    with open(raw_path, encoding="utf-8") as fh:
        raw = json.load(fh)

    # ── Parse ──────────────────────────────────────────────────────────────
    skill_records = parse_tiers(raw["tiers_wikitext"])
    tracing_records, hybrid_records = parse_tracing(raw["tracing_wikitext"])
    armor_records = parse_rune_entries(raw["armor_runes"])
    weapon_records = parse_rune_entries(raw["weapon_runes"])
    cost_records = parse_costs(
        raw["armor_runes"], raw["weapon_runes"], raw["support_items"]
    )

    # ── Write outputs ───────────────────────────────────────────────────────
    outputs = [
        (args.skill_json,   skill_records,   "Skill tiers"),
        (args.tracing_json, tracing_records, "Tracing acquisition"),
        (args.hybrid_json,  hybrid_records,  "Hybrid tracing acquisition"),
        (args.armor_json,   armor_records,   "Armor runes"),
        (args.weapon_json,  weapon_records,  "Weapon runes"),
        (args.costs_json,   cost_records,    "Costs"),
    ]
    for path_str, records, label in outputs:
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        print(f"  {label:30s}: {len(records):3d} → {path}")


if __name__ == "__main__":
    main()
