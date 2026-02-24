"""linkedin-cli — Main Typer application and entry point."""

from __future__ import annotations

from typing import Optional

import typer

from . import __version__
from .config import Settings, load_settings
from .output import set_json_mode

app = typer.Typer(
    name="linkedin",
    help="LinkedIn CLI — post, manage content, and view profile from the command line.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# ── Shared state ──────────────────────────────────────────────────────
_settings: Settings | None = None
_json_flag: bool = False


def get_settings() -> Settings:
    """Return the current Settings (initialised lazily on first access)."""
    global _settings
    if _settings is None:
        _settings = load_settings(json_output=_json_flag)
    return _settings


# ── Top-level options (--json, --version) ─────────────────────────────

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"linkedin-cli {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Emit JSON output (agent-friendly)."),
    version: Optional[bool] = typer.Option(None, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version and exit."),
) -> None:
    """Top-level options applied before any subcommand."""
    global _json_flag
    _json_flag = json_output
    set_json_mode(json_output)
    # Settings are loaded lazily by get_settings() so --help works without credentials.


# ── Register subcommand groups ────────────────────────────────────────
from .commands.auth import app as auth_app  # noqa: E402
from .commands.posts import app as posts_app  # noqa: E402
from .commands.profile import app as profile_app  # noqa: E402

app.add_typer(auth_app, name="auth")
app.add_typer(posts_app, name="post")
app.add_typer(profile_app, name="profile")


if __name__ == "__main__":
    app()
