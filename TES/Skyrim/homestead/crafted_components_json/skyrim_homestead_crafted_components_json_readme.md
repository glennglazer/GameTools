# skyrim_homestead_crafted_components_json

Generates the hardcoded crafted-component recipe records for the
`skyrim_homestead_crafted_components` table.

Crafted components are items forged at a blacksmith's forge before they can be
used in homestead construction. They are separated from `skyrim_homestead_build`
because they represent a different kind of data — forge recipes, not build-site
material quantities.

## Hardcoded records

| Name | Batch size | Iron Ingot | Corundum Ingot |
|---|---|---|---|
| nails | 10 | 1 | 0 |
| hinge | 2 | 1 | 0 |
| iron fittings | 1 | 1 | 0 |
| lock | 1 | 1 | 1 |

Names are lowercase to match the column names in `skyrim_homestead_build`
(e.g., the `nails` column, `lock` column).

## Output: `crafted_components_records.json`

```json
[
  {"name": "nails", "batch_size": 10, "iron_ingot": 1, "corundum_ingot": 0},
  ...
]
```

## Usage

```bash
python3 TES/Skyrim/homestead/crafted_components_json/skyrim_parse_homestead_crafted_components.py \
  /abs/path/to/crafted_components_records.json
```

## Joining with build table

To resolve a build row's nails requirement to iron ingots:
```sql
SELECT b.section, b.location, b.nails,
       CEIL(CAST(b.nails AS REAL) / c.batch_size) AS nail_batches,
       CEIL(CAST(b.nails AS REAL) / c.batch_size) * c.iron_ingot AS iron_needed
FROM skyrim_homestead_build b
JOIN skyrim_homestead_crafted_components c ON c.name = 'nails'
WHERE b.nails > 0;
```
