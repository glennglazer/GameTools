"""Secure API key management using OS-native credential storage.

Windows  → Windows Credential Manager
macOS    → Keychain
Linux    → Secret Service (gnome-keyring / kwallet) or fallback to ~/.netrc
"""
import sys

import keyring

_SERVICE = "GameTools-TES"
_USERNAME = "anthropic-api-key"


def get_api_key() -> str | None:
    """Return the stored Anthropic API key, or None if not yet configured."""
    try:
        return keyring.get_password(_SERVICE, _USERNAME)
    except Exception:
        return None


def set_api_key(key: str) -> None:
    """Store the Anthropic API key in the OS credential store."""
    keyring.set_password(_SERVICE, _USERNAME, key)


def delete_api_key() -> None:
    """Remove the stored API key."""
    try:
        keyring.delete_password(_SERVICE, _USERNAME)
    except keyring.errors.PasswordDeleteError:
        pass


def is_configured() -> bool:
    return bool(get_api_key())
