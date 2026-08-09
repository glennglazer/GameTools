# GameTools TES — Windows

## Files in this directory

| File | Description |
|---|---|
| `GameToolsTES.exe` | Standalone executable (no installation required) |
| `GameTools_TES_<version>_Setup.exe` | Full installer with Start Menu entry and Programs & Features registration |

## Installation

Run `GameTools_TES_<version>_Setup.exe`. If Windows SmartScreen appears:
- Click **More info → Run anyway**

## Usage

Launch from the Start Menu or Desktop shortcut.  
The app starts a local server and opens your browser automatically.

**First run**: Click ⚙ Settings and enter your Anthropic API key.

## Uninstalling

Programs and Features (Control Panel) → "GameTools — The Elder Scrolls" → Uninstall  
This removes the executable, shortcuts, and registry entries.

## Firewall prompt

Windows Defender Firewall may ask "Allow access?" — choose **Private networks**.  
The app only listens on `127.0.0.1` (localhost), so this is safe.
