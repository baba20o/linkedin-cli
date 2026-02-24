"""Token persistence — save / load / clear OAuth tokens."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .config import Settings


def token_path(settings: Settings) -> Path:
    return Path(settings.token_file)


def load_token(settings: Settings) -> dict | None:
    """Return the saved token dict if it exists and hasn't expired, else None."""
    path = token_path(settings)
    if not path.is_file():
        return None

    with open(path, "r") as f:
        data: dict = json.load(f)

    expires_at = data.get("expires_at", 0)
    if expires_at <= time.time():
        return None  # expired

    return data


def load_token_raw(settings: Settings) -> dict | None:
    """Return the saved token dict regardless of expiry (for refresh flow)."""
    path = token_path(settings)
    if not path.is_file():
        return None

    with open(path, "r") as f:
        return json.load(f)


def is_token_expired(data: dict) -> bool:
    """Check if the access token has expired."""
    return data.get("expires_at", 0) <= time.time()


def save_token(data: dict, settings: Settings) -> None:
    """Persist token dict to disk, computing expires_at from expires_in."""
    data["expires_at"] = time.time() + data.get("expires_in", 0)
    with open(token_path(settings), "w") as f:
        json.dump(data, f, indent=2)


def clear_token(settings: Settings) -> bool:
    """Delete the stored token file. Returns True if a file was removed."""
    path = token_path(settings)
    if path.is_file():
        path.unlink()
        return True
    return False


def token_expiry_str(data: dict) -> str:
    """Human-readable expiry timestamp."""
    ts = data.get("expires_at", 0)
    if ts:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    return "unknown"
