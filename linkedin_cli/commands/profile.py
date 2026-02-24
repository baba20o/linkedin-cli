"""Profile subcommands — me."""

from __future__ import annotations

import typer

from ..api import LinkedInAPI
from ..output import output, output_error

app = typer.Typer(help="View LinkedIn profile information.")


def _api() -> LinkedInAPI:
    from ..cli import get_settings

    return LinkedInAPI(get_settings())


@app.command("me")
def me() -> None:
    """Show your LinkedIn profile info."""
    api = _api()
    try:
        profile = api.get_profile()
    except Exception as exc:
        output_error(f"Failed to fetch profile: {exc}")

    output(profile)
