# Homebrew Cask for GameTools TES
#
# This file lives in a personal tap repo, e.g.:
#   github.com/glennglazer/homebrew-gametools
#
# To install:
#   brew tap glennglazer/gametools
#   brew install --cask gametools-tes
#
# To update: bump version + sha256 values after each GitHub Release.
#
# The sha256 values come from:
#   shasum -a 256 GameTools_TES_<version>_ARM.dmg
#   shasum -a 256 GameTools_TES_<version>_Intel.dmg

cask "gametools-tes" do
  version "1.0.0"

  on_arm do
    url "https://github.com/glennglazer/GameTools/releases/download/tes-v#{version}/GameTools_TES_#{version}_ARM.dmg"
    sha256 "PLACEHOLDER_ARM_SHA256"
  end

  on_intel do
    url "https://github.com/glennglazer/GameTools/releases/download/tes-v#{version}/GameTools_TES_#{version}_Intel.dmg"
    sha256 "PLACEHOLDER_INTEL_SHA256"
  end

  name "GameTools — The Elder Scrolls"
  desc "Crafting assistant for Morrowind, Oblivion, and Skyrim"
  homepage "https://github.com/glennglazer/GameTools"

  app "GameToolsTES.app"

  zap trash: [
    "~/Library/Application Support/GameTools TES",
    "~/Library/Preferences/com.gametools.tes.plist",
    "~/Library/Caches/GameTools TES",
  ]
end
