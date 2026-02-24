"""Output helpers — consistent human + JSON output."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

# Global flag toggled by the top-level --json callback
_json_mode = False


def set_json_mode(enabled: bool) -> None:
    global _json_mode
    _json_mode = enabled


def is_json_mode() -> bool:
    return _json_mode


def output(data: Any, *, human: str | None = None) -> None:
    """
    Print *data* as JSON when --json is active, otherwise print *human*.
    If *human* is None, pretty-print the data as a Rich table/dict.
    """
    if _json_mode:
        json.dump(data, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        if human is not None:
            console.print(human)
        elif isinstance(data, list):
            _print_list(data)
        elif isinstance(data, dict):
            _print_dict(data)
        else:
            console.print(str(data))


def output_error(message: str, *, code: int = 1) -> None:
    if _json_mode:
        json.dump({"error": message}, sys.stdout)
        sys.stdout.write("\n")
    else:
        err_console.print(f"[bold red]Error:[/bold red] {message}")
    raise SystemExit(code)


def _print_dict(d: dict) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    for k, v in d.items():
        table.add_row(str(k), str(v))
    console.print(table)


def _print_list(items: list[dict]) -> None:
    if not items:
        console.print("[dim]No results.[/dim]")
        return
    # Build table from first item's keys
    table = Table(box=None, padding=(0, 2))
    keys = list(items[0].keys())
    for k in keys:
        table.add_column(k, style="cyan")
    for item in items:
        table.add_row(*(str(item.get(k, "")) for k in keys))
    console.print(table)
