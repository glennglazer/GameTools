#!/usr/bin/env python3
"""
awakening_scrape_runecrafting.py
Scrapes DAO:A Runecrafting data from the Dragon Age Fandom wiki.

Fetches:
  - Runecrafting main page: tiers section (§1) and tracing acquisition section (§2)
  - Individual armor rune pages: 5 types × 7 levels = 35 pages + 4 hybrid = 39 pages
  - Individual weapon rune pages: 9 types × 7 levels = 63 pages + 4 hybrid = 67 pages
  - Support item pages: Blank Runestone, Etching Agent

Output JSON structure:
  {
    "tiers_wikitext":  "...",
    "tracing_wikitext": "...",
    "armor_runes":     [{"page": "...", "wikitext": "..."}, ...],
    "weapon_runes":    [{"page": "...", "wikitext": "..."}, ...],
    "support_items":   [{"page": "...", "wikitext": "..."}, ...]
  }
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

FANDOM_API = "https://dragonage.fandom.com/api.php"
UA = "GameTools-Scraper/1.0 (https://github.com/glennglazer/GameTools)"
SLEEP = 0.3  # seconds between requests

LEVELS = ["Novice", "Journeyman", "Expert", "Master", "Grandmaster", "Masterpiece", "Paragon"]

# Armor rune types (non-hybrid).  Barrier has rune pages but no tracing acquisition entry.
ARMOR_TYPES = ["Barrier", "Immunity", "Reservoir", "Stout", "Tempest"]
ARMOR_HYBRID = ["Amplification", "Diligence", "Endurance", "Evasion"]

# Weapon rune types (non-hybrid)
WEAPON_TYPES = ["Cold Iron", "Dweomer", "Flame", "Frost", "Hale",
                "Lightning", "Paralyze", "Silverite", "Slow"]
WEAPON_HYBRID = ["Elemental", "Intensifying", "Menacing", "Momentum"]

SUPPORT_PAGES = ["Blank Runestone", "Etching Agent"]


# ── helpers ──────────────────────────────────────────────────────────────────

def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_wikitext_section(page: str, section: int) -> str:
    url = (f"{FANDOM_API}?action=parse"
           f"&page={urllib.parse.quote(page, safe='')}"
           f"&prop=wikitext&section={section}&format=json")
    data = fetch_json(url)
    return data["parse"]["wikitext"]["*"]


def fetch_wikitext(page: str) -> str:
    url = (f"{FANDOM_API}?action=parse"
           f"&page={urllib.parse.quote(page, safe='')}"
           f"&prop=wikitext&format=json")
    data = fetch_json(url)
    return data["parse"]["wikitext"]["*"]


def fetch_rune_pages(rune_types: list, levels_or_none: list,
                     label: str) -> list:
    """Fetch pages for each (level, type) combination and return list of dicts."""
    results = []
    for rune_type in rune_types:
        for level in levels_or_none:
            page = f"{level} {rune_type} Rune" if level else f"{rune_type} Rune"
            print(f"    {page}")
            try:
                wikitext = fetch_wikitext(page)
                results.append({"page": page, "wikitext": wikitext})
            except Exception as exc:
                print(f"  WARNING: failed to fetch '{page}': {exc}",
                      file=sys.stderr)
            time.sleep(SLEEP)
    return results


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape DAO:A Runecrafting data from the Fandom wiki"
    )
    ap.add_argument("output", help="Path for output runecrafting_raw.json")
    args = ap.parse_args()

    output = Path(args.output)

    # ── 1. Main page sections ────────────────────────────────────────────────
    print("Fetching Runecrafting tiers section (§1)...")
    tiers_wikitext = fetch_wikitext_section("Runecrafting", 1)
    time.sleep(SLEEP)

    print("Fetching Runecrafting tracing acquisition section (§2)...")
    tracing_wikitext = fetch_wikitext_section("Runecrafting", 2)
    time.sleep(SLEEP)

    # ── 2. Armor rune pages ──────────────────────────────────────────────────
    total_armor = len(ARMOR_TYPES) * len(LEVELS) + len(ARMOR_HYBRID)
    print(f"Fetching armor rune pages ({total_armor} pages)...")
    armor_runes = fetch_rune_pages(ARMOR_TYPES, LEVELS, "armor non-hybrid")
    armor_runes += fetch_rune_pages(ARMOR_HYBRID, [None], "armor hybrid")

    # ── 3. Weapon rune pages ─────────────────────────────────────────────────
    total_weapon = len(WEAPON_TYPES) * len(LEVELS) + len(WEAPON_HYBRID)
    print(f"Fetching weapon rune pages ({total_weapon} pages)...")
    weapon_runes = fetch_rune_pages(WEAPON_TYPES, LEVELS, "weapon non-hybrid")
    weapon_runes += fetch_rune_pages(WEAPON_HYBRID, [None], "weapon hybrid")

    # ── 4. Support item pages ────────────────────────────────────────────────
    print("Fetching support item pages...")
    support_items = []
    for page in SUPPORT_PAGES:
        print(f"    {page}")
        try:
            wikitext = fetch_wikitext(page)
            support_items.append({"page": page, "wikitext": wikitext})
        except Exception as exc:
            print(f"  WARNING: failed to fetch '{page}': {exc}", file=sys.stderr)
        time.sleep(SLEEP)

    # ── 5. Save ──────────────────────────────────────────────────────────────
    result = {
        "tiers_wikitext": tiers_wikitext,
        "tracing_wikitext": tracing_wikitext,
        "armor_runes": armor_runes,
        "weapon_runes": weapon_runes,
        "support_items": support_items,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(
        f"\nSaved {len(armor_runes)} armor rune pages, "
        f"{len(weapon_runes)} weapon rune pages, "
        f"{len(support_items)} support item pages"
        f"\n→ {output}"
    )


if __name__ == "__main__":
    main()
