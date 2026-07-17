# Skyrim Hearthfire Homestead

Data pipeline for Hearthfire house-building: materials required to construct and furnish all three manors (Lakeview Manor, Windstad Manor, Heljarchen Hall).

## Source pages

| Directory | Wiki page |
|-----------|-----------|
| `homestead_parse/` | `Homestead_(Hearthfire)` |
| `main_hall_parse/` | `Main_Hall` |
| `cellar_parse/` | `Cellar` |

## Game rules

**Stage 5 — Wings:** Each manor can have only **one wing**. The three choices are mutually exclusive: Tower, Room with Outdoor Patio, or Downstairs Room. You cannot build more than one.

**Stable — horse costs:** The per-horse-type costs listed under the Stable section are not included. Those are stable-level purchases, not homestead building materials.

**Aquarium exterior:** Not included. The Aquarium is Creation Club content (not part of the base Hearthfire DLC) and will be added when Creation Club items are covered.

**Cellar:** All Cellar furnishings must be built manually by the player. The steward cannot furnish the Cellar, so it is excluded from `skyrim_homestead_steward_cost`.

## Database tables

| Table | Key | Description |
|-------|-----|-------------|
| `skyrim_homestead_build` | `(section, location)` | Wide sparse table: every buildable item across all stages. 47 material columns (0 = not needed). |
| `skyrim_homestead_exclusive_exterior` | `manor` | Maps each manor to its one unique exterior option (Apiary / Fish Hatchery / Grain Mill). |
| `skyrim_homestead_steward_cost` | `room` | Gold cost to have the steward furnish each room (12 rooms). |

## Querying enumerated items

Some items appear as multiple identical rows within the same location (e.g., four Barrels in Cellar_Containers). These are disambiguated by appending `_1`, `_2`, etc. to the section name:

```sql
-- Wrong: exact match returns only one row
SELECT * FROM skyrim_homestead_build WHERE section = 'Barrel';

-- Correct: LIKE matches all four barrels
SELECT * FROM skyrim_homestead_build WHERE section LIKE 'Barrel%' AND location = 'Cellar_Containers';
```

## Update strategy

`skyrim_homestead_build` uses **full-replace** on every pipeline run: all rows are deleted and re-inserted. This differs from the diff-based upsert used by every other table in this project. The SQL loader does not check for or generate `.upsert.json` / `.delete.json` diff files, and the driver does not call `has_diff_files()` before running the homestead SQL loaders.

Reason: the homestead data is static (Hearthfire game content does not change), the table is small (160 rows), and the wide sparse schema makes row-level diffing impractical.
