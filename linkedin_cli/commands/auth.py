"""Auth subcommands — login, status, logout."""

from __future__ import annotations

import typer

from ..api import LinkedInAPI
from ..config import Settings
from ..output import console, output, output_error
from ..token import clear_token, is_token_expired, load_token, load_token_raw, token_expiry_str

app = typer.Typer(help="Authenticate with LinkedIn.")


def _get_deps() -> tuple[Settings, LinkedInAPI]:
    """Lazy import to pick up the settings stored on the parent app."""
    from ..cli import get_settings

    settings = get_settings()
    return settings, LinkedInAPI(settings)


@app.command()
def login(
    code: str = typer.Option(
        "",
        "--code",
        "-c",
        help="Authorization code or redirect URL (skip the browser prompt).",
    ),
) -> None:
    """Run the OAuth2 login flow and save the token."""
    settings, api = _get_deps()

    # Already have a valid token?
    existing = load_token(settings)
    if existing:
        output(
            {"status": "already_authenticated", "expires_at": token_expiry_str(existing)},
            human=f"[green]Already authenticated.[/green] Token expires {token_expiry_str(existing)}.\n"
            "Run [bold]linkedin auth logout[/bold] first to re-authenticate.",
        )
        return

    if not code:
        url = api.open_auth_in_browser()
        console.print(f"[bold]Opening browser for LinkedIn login…[/bold]\n\nAuth URL: {url}\n")
        code = typer.prompt("Paste the redirect URL (or just the code)")

    auth_code = api.extract_code_from_url(code)
    try:
        data = api.exchange_code(auth_code)
    except Exception as exc:
        output_error(f"Token exchange failed: {exc}")

    output(
        {"status": "authenticated", "expires_at": token_expiry_str(data)},
        human=f"[green]Authenticated![/green] Token expires {token_expiry_str(data)}.",
    )


@app.command()
def status() -> None:
    """Show the current token status."""
    settings, _ = _get_deps()

    # First try a valid (non-expired) token
    data = load_token(settings)
    if data:
        has_refresh = bool(data.get("refresh_token"))
        info = {
            "authenticated": True,
            "expires_at": token_expiry_str(data),
            "scopes": data.get("scope", "unknown"),
            "auto_refresh": has_refresh,
        }
        refresh_note = " (auto-refresh enabled)" if has_refresh else ""
        output(info, human=f"[green]Token valid[/green] — expires {info['expires_at']}, scopes: {info['scopes']}{refresh_note}")
        return

    # Token expired — check if we have a refresh token
    raw = load_token_raw(settings)
    if raw and raw.get("refresh_token"):
        info = {
            "authenticated": False,
            "access_token_expired": True,
            "refresh_token_available": True,
            "expires_at": token_expiry_str(raw),
        }
        output(info, human=f"[yellow]Access token expired[/yellow] ({token_expiry_str(raw)}), but a refresh token is available. Next command will auto-refresh.")
    else:
        info = {"authenticated": False}
        output(info, human="[yellow]Not authenticated.[/yellow] Run [bold]linkedin auth login[/bold].")


@app.command()
def logout() -> None:
    """Remove the saved token."""
    settings, _ = _get_deps()
    removed = clear_token(settings)
    if removed:
        output({"status": "logged_out"}, human="[green]Token removed.[/green]")
    else:
        output({"status": "no_token"}, human="[dim]No token file found.[/dim]")
