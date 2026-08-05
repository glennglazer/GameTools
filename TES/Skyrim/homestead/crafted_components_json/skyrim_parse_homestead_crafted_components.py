"""Generate skyrim_homestead_crafted_components records JSON.

Crafted components are items forged at a blacksmith's forge before they can
be used in homestead construction.  This script produces a fixed set of
records with no raw input — the recipes are hardcoded from the wiki.

Output schema (matches skyrim_homestead_crafted_components table):
  name TEXT (lowercase, e.g. "nails")
  batch_size INT — number of units produced per forge recipe
  iron_ingot, corundum_ingot, ... — integer material quantities (0 if unused)
"""
import argparse
import json
import sys
from pathlib import Path

# All material columns that a crafted component recipe can reference.
# Subset of skyrim_homestead_build MATERIAL_COLS; only iron and corundum are
# used by any current recipe.
MATERIAL_COLS = [
    "iron_ingot",
    "corundum_ingot",
]

# Hardcoded recipes (name must be lowercase to match build table references).
# batch_size = number of units produced per forge action.
CRAFTED_COMPONENTS = [
    {"name": "nails",         "batch_size": 10, "iron_ingot": 1, "corundum_ingot": 0},
    {"name": "hinge",         "batch_size":  2, "iron_ingot": 1, "corundum_ingot": 0},
    {"name": "iron fittings", "batch_size":  1, "iron_ingot": 1, "corundum_ingot": 0},
    {"name": "lock",          "batch_size":  1, "iron_ingot": 1, "corundum_ingot": 1},
]


def main():
    ap = argparse.ArgumentParser(
        description="Generate crafted components records JSON")
    ap.add_argument("output_json", help="Path to output JSON file")
    args = ap.parse_args()

    out = Path(args.output_json)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(CRAFTED_COMPONENTS, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(CRAFTED_COMPONENTS)} crafted component records to {out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
