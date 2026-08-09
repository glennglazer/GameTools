# Homebrew Cask for GameTools TES
#
# This file lives in a personal tap repo, e.g.:
#   github.com/glennglazer/homebrew-gametools
#
# To install:
#   brew tap glennglazer/gametools
#   brew install --cask gametools-tes
#
# To update: bump version + sha256 after each GitHub Release.
#   shasum -a 256 GameTools_TES_<version>_macOS.dmg
#
# The DMG is built on Apple Silicon (arm64) and runs on Intel Macs via Rosetta 2.

cask "gametools-tes" do
  version "1.0.0"

  url "https://github.com/glennglazer/GameTools/releases/download/tes-v#{version}/GameTools_TES_#{version}_macOS.dmg"
  sha256 "PLACEHOLDER_SHA256"

  name "GameTools — The Elder Scrolls"
  desc "Crafting assistant for Morrowind, Oblivion, and Skyrim"
  homepage "https://github.com/glennglazer/GameTools"

  app "GameTools TES.app"

  zap trash: [
    "~/Library/Application Support/GameTools TES",
    "~/Library/Preferences/com.gametools.tes.plist",
    "~/Library/Caches/GameTools TES",
  ]
end
