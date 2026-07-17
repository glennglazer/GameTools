"""Output hardcoded manor→exclusive exterior mapping as JSON.

Each of the three Hearthfire manors has one exclusive exterior option:
  Lakeview Manor  → Apiary
  Windstad Manor  → Fish Hatchery
  Heljarchen Hall → Grain Mill
"""
import argparse
import json
import sys
from pathlib import Path

RECORDS = [
    {"manor": "Lakeview Manor",  "exclusive_exterior": "Apiary"},
    {"manor": "Windstad Manor",  "exclusive_exterior": "Fish Hatchery"},
    {"manor": "Heljarchen Hall", "exclusive_exterior": "Grain Mill"},
]


def main():
    ap = argparse.ArgumentParser(
        description="Write homestead exclusive exterior JSON")
    ap.add_argument("output_json", help="Absolute path to output JSON file")
    args = ap.parse_args()

    out = Path(args.output_json)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RECORDS, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(RECORDS)} records to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
