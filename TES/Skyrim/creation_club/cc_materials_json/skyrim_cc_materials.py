"""Generate CC tempering materials upsert JSON.

Hardcoded new smithing categories added by Creation Club armor/weapons sets.
Run once to produce the upsert file; the SQL loader (skyrim_tempering_materials)
then applies it.

Output: cc_tempering_materials.upsert.json (placed alongside the main
skyrim_smithing_materials.json in materials_json/ via --out-dir)
"""
import argparse
import json
import sys
from pathlib import Path

# New CC smithing categories and their tempering material
CC_TEMPERING = [
    {"smithing_category": "Amber",       "crafting_material": "Refined Amber"},
    {"smithing_category": "Dark",        "crafting_material": "Quicksilver Ingot"},
    {"smithing_category": "Golden",      "crafting_material": "Gold Ingot"},
    {"smithing_category": "Madness",     "crafting_material": "Madness Ingot"},
    {"smithing_category": "Silver",      "crafting_material": "Silver Ingot"},
    {"smithing_category": "Chitin",      "crafting_material": "Chitin Plate"},
    {"smithing_category": "Vigil",       "crafting_material": "Steel Ingot"},
]


def main():
    ap = argparse.ArgumentParser(
        description="Write CC tempering materials as upsert JSON")
    ap.add_argument("out_file", help="Output JSON file (cc_tempering_materials.json)")
    args = ap.parse_args()

    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(CC_TEMPERING, f, ensure_ascii=False, indent=2)

    print(f"{len(CC_TEMPERING)} CC tempering records → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
