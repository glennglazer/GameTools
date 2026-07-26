# Purpose and Action

Parses the raw UESP sigil stone HTML into three JSON record files, one per database table.

## Script

### `oblivion_parse_sigil_stone.py`

Reads `oblivion_sigil_stone_raw.json` and parses the Effects and Magnitudes wikitable into 150 records per file (30 stone groups × 5 levels: Descendent, Subjacent, Latent, Ascendent, Transcendent).

**Outputs:**
- `sigil_stone_records.json` — Form ID, weapon effect, armor effect (feeds `oblivion_sigil_stone`)
- `sigil_stone_weapon_magnitudes.json` — Form ID + 10 nullable int columns: magnitude and charges for each of the 5 levels (feeds `oblivion_sigil_stone_weapon_magnitudes`)
- `sigil_stone_armor_magnitudes.json` — Form ID + 5 nullable int columns: magnitude for each of the 5 levels (feeds `oblivion_sigil_stone_armor_magnitudes`)

Each Form ID appears in exactly one level column per row; the other four level columns are NULL. This allows a direct JOIN on Form ID to retrieve the magnitude for whatever level stone was actually found.

### Parsing rules

- **Weapon magnitudes**: integer before `pts` or `secs` in the cell text. For Demoralize and Turn Undead (listed as `level N (=X pts)`), the level number is stored, not the pts value.
- **Charges**: the final `=N` result from the `charge/cost=uses` formula in the `<small>` tag.
- **Armor magnitudes**: integer before `pts` in the cell text.
- **Dash values (`-`)**: stored as NULL (e.g., Night-Eye and Water Walking have no armor magnitude).
- **Effect names**: extracted from the anchor link text, stripping duration suffixes (`, 30 secs`) and footnote markers (`**`).
- **Form IDs**: extracted from `.idref` span, uppercased (e.g., `00041FB1`).
- **Repeated header rows**: skipped.

## Usage

```bash
python3 TES/Oblivion/enchanting/sigil_stone_json/oblivion_parse_sigil_stone.py
```
