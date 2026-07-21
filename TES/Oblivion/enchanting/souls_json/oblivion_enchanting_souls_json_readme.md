# Purpose and Action

Parses Oblivion creature souls from UESP raw HTML into JSON records for `oblivion_enchant_souls`.

## Script

### `oblivion_parse_souls.py`

Reads `oblivion_souls_raw.json` and outputs `oblivion_souls_records.json` with 51 records.

**Parsing strategy:**

1. Parse the Soul Strengths table (section 3) to build the name→integer mapping:
   Petty=150, Lesser=300, Common=800, Greater=1200, Grand=1600, Black=1600
2. Parse all four wikitables in section 1 (standard A-N, standard N-Z/NPCs, location-specific, quest creatures)
3. Keep only entries whose soul level is exactly one of the six fixed labels; all leveled entries (containing `L:`, `/`, or `leveled`) are skipped
4. Join creature name with the mapped integer value

**Black souls included:** Dremora, NPC(any race), and Vampire are stored with soul_size=1600.

**JSON record format:**
```json
{"name": "Deer", "soul_size": 150}
```

## Usage

```bash
python3 TES/Oblivion/enchanting/souls_json/oblivion_parse_souls.py
```
