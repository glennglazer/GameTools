"""Load skyrim_homestead_build records from JSON into SQLite."""
import argparse
import json
import pandas as pd
import sqlite3
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent.parent  # build_sql→homestead→Skyrim→TES→repo root

TABLE_NAME = "skyrim_homestead_build"

MATERIAL_COLS = [
    "sawn_log", "quarried_stone", "nails", "clay", "iron_fittings", "lock", "hinge",
    "iron_ingot", "steel_ingot", "glass", "quicksilver_ingot", "refined_moonstone",
    "filled_grand_soul_gem", "gold_ingot", "leather_strips", "straw", "goat_horns",
    "vampire_dust", "deer_hide", "large_antlers", "small_antlers", "goat_hide",
    "horker_tusk", "mudcrab_chitin", "slaughterfish_scales", "wolf_pelt",
    "sabre_cat_tooth", "sabre_cat_snow_pelt", "bear_pelt", "amulet_of_akatosh",
    "amulet_of_arkay", "amulet_of_dibella", "amulet_of_julianos", "amulet_of_kynareth",
    "amulet_of_mara", "amulet_of_stendarr", "amulet_of_talos", "amulet_of_zenithar",
    "flawless_amethyst", "flawless_sapphire", "corundum_ingot", "orichalcum_ingot",
    "silver_ingot", "ebony_ingot", "refined_malachite", "dragon_bone", "dragon_scales",
]

ALL_COLS = ["section", "location", "stage", "batch_size"] + MATERIAL_COLS


def main():
    ap = argparse.ArgumentParser(
        description=f"Load {TABLE_NAME} into SQLite")
    ap.add_argument("input_json", help="Path to build_records.json")
    ap.add_argument("db",         help="Path to gametools.sqlite3")
    args = ap.parse_args()

    src = Path(args.input_json)
    db_path = Path(args.db)
    for p, label in ((src, "input JSON"), (db_path.parent, "database directory")):
        if not p.exists():
            print(f"ERROR: {label} not found: {p}", file=sys.stderr)
            sys.exit(1)

    with open(src, encoding="utf-8") as f:
        records = json.load(f)

    df = pd.DataFrame(records, columns=ALL_COLS)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    exists = cur.execute(
        f"SELECT name FROM sqlite_master WHERE name='{TABLE_NAME}'"
    ).fetchone()

    if exists is not None:
        # Migration: add batch_size column if an older version of the table lacks it.
        existing_cols = [r[1] for r in cur.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()]
        if "batch_size" not in existing_cols:
            cur.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN batch_size INTEGER")
            conn.commit()
        cur.execute(f"DELETE FROM {TABLE_NAME}")
        conn.commit()

    df.to_sql(TABLE_NAME, conn, if_exists="append", method="multi", index=False)

    if exists is None:
        cur.execute(
            f"CREATE UNIQUE INDEX idx_{TABLE_NAME} "
            f"ON {TABLE_NAME}(section, location)"
        )
        conn.commit()

    conn.close()
    action = "updated" if exists else "created"
    print(f"{action} {TABLE_NAME}: {len(df)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
