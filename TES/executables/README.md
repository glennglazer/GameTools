# GameTools — The Elder Scrolls

A standalone crafting assistant for **Morrowind**, **Oblivion**, and **Skyrim**.  
Ask plain-English questions about alchemy, enchanting, smithing, and homestead construction.  
The app uses Claude AI (via the Anthropic API) and a local SQLite database — **no data leaves your machine except your query text sent to Anthropic**.

---

## Downloads

Find the latest release on [GitHub Releases](https://github.com/glennglazer/GameTools/releases).

| Platform | File |
|---|---|
| Windows 10/11 (x64) | `GameTools_TES_<version>_Setup.exe` |
| macOS (Apple Silicon + Intel via Rosetta 2) | `GameTools_TES_<version>_macOS.dmg` |

---

## Installation

### Windows

1. Download `GameTools_TES_<version>_Setup.exe`
2. Double-click to run — Windows may show a SmartScreen warning:
   - Click **More info → Run anyway**
   - *(This occurs because the app is not yet from a registered publisher.)*
3. Follow the installer wizard; the app is registered in **Programs and Features** for clean removal

**First launch:** Right-click the Start Menu shortcut and choose **Run as administrator** is *not* required — the app runs as a normal user.

### macOS (Apple Silicon and Intel)

The single DMG runs natively on Apple Silicon and on Intel Macs via Rosetta 2 — no separate download is needed.

1. Download `GameTools_TES_<version>_macOS.dmg`
2. Open the DMG and drag **GameTools TES** to your **Applications** folder
3. **First launch only:** macOS will block the app because it is not from the Mac App Store:
   - Right-click `GameToolsTES.app` in Applications → **Open**
   - In the dialog that appears, click **Open** again
   - After the first approved launch, future launches work normally
4. Alternatively: **System Settings → Privacy & Security**, scroll to the blocked app, click **Allow Anyway**

> **Why this happens:** The app is signed with an ad-hoc certificate rather than a paid Apple Developer Program certificate. The app itself is safe — this prompt is macOS's standard Gatekeeper warning for unsigned apps.

---

## Local server notice

> ⚠️ **GameTools TES starts a local web server on your machine.**
>
> When you launch the app, it binds to a random port on `127.0.0.1` (localhost only — not accessible from other devices) and opens your default browser to that address. This is how the chat interface is served.
>
> **No additional firewall rules or OS permissions are required** beyond accepting the first-launch security prompt described above.
>
> The server stops automatically when you close the app.

### Platform-specific: allowing the local server

| Platform | What to expect |
|---|---|
| Windows | Windows Defender Firewall may prompt "Allow access" — choose **Private networks** (not Public). The app only listens on localhost, but Windows sometimes prompts anyway. |
| macOS | No firewall prompt expected; localhost connections are always allowed. |
| Linux | No prompt expected. If your distro has a strict outbound firewall, allow connections to `api.anthropic.com:443`. |

---

## First-time setup

1. Launch the app — your browser opens automatically
2. You'll see a notice: **No Anthropic API key configured**
3. Click ⚙ **Settings** in the top-right corner
4. Paste your API key (from [console.anthropic.com](https://console.anthropic.com))
5. Click **Save** — the key is stored in your OS credential store:
   - **Windows**: Windows Credential Manager
   - **macOS**: Keychain
   - **Linux**: Secret Service / gnome-keyring
6. The key is **never** written to a file or included in this application

---

## Using the app

- **Game context**: Set the dropdown in the header to your current game (Morrowind / Oblivion / Skyrim) for focused answers. Leave on "All Games" for cross-game questions. The app will warn you if your query doesn't match the active context.
- **Typing**: Press **Enter** to send, **Shift+Enter** for a newline in your message.
- **Tool calls**: Each answer shows a collapsible "N tool calls used" disclosure — expand it to see exactly what database queries were made.
- **Export**: Click ⬇ **Export** to download the conversation as a Markdown file.

---

## Sample queries

### Skyrim — Alchemy
> **"Which ingredients share both Fortify Smithing and Fortify Two-Handed?"**

Expected: A list of ingredient pairs with the shared effects, suitable for making a smithing + combat potion.

---

### Oblivion — Enchanting
> **"What's the strongest soul I can trap without a black soul gem, and what sigil stones give a Damage Health + Shield combination?"**

Expected: The highest non-humanoid soul size available (800 — various creatures), plus a list of sigil stones with Damage Health weapon effect and a Shield armor effect, with magnitudes at each level.

---

### Morrowind — Enchanting
> **"I want to put a Constant Effect Restore Health enchantment on a ring. What soul do I need and how many enchantment points does the ring need?"**

Expected: Identifies souls ≥ 400 required for CE enchantments, gives the formula for CE cost (magnitude × 0.05 × base_cost × duration = CE points), finds rings with sufficient capacity, and confirms which soul gems can hold the required soul.

---

## DIY build from source

See [DIY Build Instructions](DIY_BUILD.md) for step-by-step instructions to:
- Clone the repo
- Create an empty SQLite database
- Run all pipeline stages to populate it
- Launch the app in development mode (no compilation needed)

---

## Uninstalling

**Windows**: Programs and Features → "GameTools — The Elder Scrolls" → Uninstall  
**macOS**: Drag `GameToolsTES.app` from Applications to Trash; to remove the stored API key, open Keychain Access and delete the "GameTools-TES" entry.  
**API key (all platforms)**: Open the app → ⚙ Settings → **Clear key**

---

## Privacy

- Conversation text is sent to Anthropic's API to generate answers
- Database queries run **locally** on your machine
- Your API key is stored **only** in your OS credential store
- No telemetry, no account creation, no external services beyond Anthropic
