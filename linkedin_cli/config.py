"""Configuration loading from .env file and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _find_env_file() -> Path | None:
    """Walk up from cwd to find a .env file."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


@dataclass(frozen=True)
class Settings:
    """All configuration values used by linkedin-cli."""

    client_id: str
    client_secret: str
    redirect_uri: str = "https://greenmountaincomputing.com/"
    scopes: str = "w_member_social openid profile"
    api_version: str = "202506"
    token_file: str = "linkedin_token.json"

    # Output behaviour
    json_output: bool = False


def load_settings(*, json_output: bool = False) -> Settings:
    """
    Build a Settings object from environment variables.

    Env vars (all prefixed ``LINKEDIN_``):
        LINKEDIN_CLIENT_ID
        LINKEDIN_CLIENT_SECRET
        LINKEDIN_REDIRECT_URI
        LINKEDIN_SCOPES
        LINKEDIN_API_VERSION
        LINKEDIN_TOKEN_FILE
    """
    env_file = _find_env_file()
    if env_file:
        load_dotenv(env_file)

    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise SystemExit(
            "Missing LINKEDIN_CLIENT_ID and/or LINKEDIN_CLIENT_SECRET.\n"
            "Set them in a .env file or as environment variables."
        )

    return Settings(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=os.getenv("LINKEDIN_REDIRECT_URI", Settings.redirect_uri),
        scopes=os.getenv("LINKEDIN_SCOPES", Settings.scopes),
        api_version=os.getenv("LINKEDIN_API_VERSION", Settings.api_version),
        token_file=os.getenv("LINKEDIN_TOKEN_FILE", Settings.token_file),
        json_output=json_output,
    )
