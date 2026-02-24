"""Post subcommands — text, image, article, video, poll, comment, react, delete, list."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..api import LinkedInAPI
from ..output import output, output_error

app = typer.Typer(help="Create, list, and delete LinkedIn posts.")


def _api() -> LinkedInAPI:
    from ..cli import get_settings

    return LinkedInAPI(get_settings())


@app.command("text")
def text_post(
    message: str = typer.Argument(..., help="The post body text."),
) -> None:
    """Publish a text-only post."""
    api = _api()
    try:
        result = api.create_text_post(message)
    except Exception as exc:
        output_error(f"Failed to create post: {exc}")
    output(result, human=f"[green]Post published![/green]  id: {result['id']}")


@app.command("image")
def image_post(
    message: str = typer.Argument(..., help="The post body text."),
    image: Path = typer.Option(..., "--image", "-i", help="Path to the image file.", exists=True),
) -> None:
    """Publish a post with an image attachment."""
    api = _api()
    try:
        result = api.create_image_post(message, str(image))
    except Exception as exc:
        output_error(f"Failed to create image post: {exc}")
    output(result, human=f"[green]Image post published![/green]  id: {result['id']}")


@app.command("article")
def article_post(
    message: str = typer.Argument(..., help="The post body text / commentary."),
    url: str = typer.Option(..., "--url", "-u", help="The article/link URL."),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Optional article title."),
) -> None:
    """Publish a post with a link/article preview."""
    api = _api()
    try:
        result = api.create_article_post(message, url, title=title)
    except Exception as exc:
        output_error(f"Failed to create article post: {exc}")
    output(result, human=f"[green]Article post published![/green]  id: {result['id']}")


@app.command("video")
def video_post(
    message: str = typer.Argument(..., help="The post body text."),
    video: Path = typer.Option(..., "--video", "-v", help="Path to the video file.", exists=True),
) -> None:
    """Publish a post with a video attachment."""
    api = _api()
    try:
        result = api.create_video_post(message, str(video))
    except Exception as exc:
        output_error(f"Failed to create video post: {exc}")
    output(result, human=f"[green]Video post published![/green]  id: {result['id']}")


@app.command("poll")
def poll_post(
    question: str = typer.Argument(..., help="The poll question."),
    option: list[str] = typer.Option(..., "--option", "-o", help="Poll option (use multiple times, 2-4 options)."),
    duration: str = typer.Option(
        "THREE_DAYS",
        "--duration",
        "-d",
        help="Poll duration: ONE_DAY, THREE_DAYS, ONE_WEEK, TWO_WEEKS.",
    ),
) -> None:
    """Publish a poll post."""
    if len(option) < 2:
        output_error("A poll requires at least 2 options.")
    if len(option) > 4:
        output_error("A poll supports at most 4 options.")

    api = _api()
    try:
        result = api.create_poll_post(question, option, duration=duration)
    except Exception as exc:
        output_error(f"Failed to create poll: {exc}")
    output(result, human=f"[green]Poll published![/green]  id: {result['id']}")


@app.command("comment")
def comment(
    post_id: str = typer.Argument(..., help="The post URN or ID to comment on."),
    message: str = typer.Argument(..., help="The comment text."),
) -> None:
    """Comment on a post."""
    api = _api()
    try:
        result = api.create_comment(post_id, message)
    except Exception as exc:
        output_error(f"Failed to comment: {exc}")
    output(result, human=f"[green]Comment posted![/green]  on: {result['post_id']}")


@app.command("react")
def react(
    post_id: str = typer.Argument(..., help="The post URN or ID to react to."),
    reaction: str = typer.Option(
        "LIKE",
        "--type",
        "-t",
        help="Reaction type: LIKE, CELEBRATE, SUPPORT, LOVE, INSIGHTFUL, FUNNY.",
    ),
) -> None:
    """React to a post (like, celebrate, etc.)."""
    api = _api()
    try:
        result = api.react_to_post(post_id, reaction)
    except Exception as exc:
        output_error(f"Failed to react: {exc}")
    output(result, human=f"[green]{result['reaction']}![/green]  on: {result['post_id']}")


@app.command("delete")
def delete_post(
    post_id: str = typer.Argument(..., help="The post URN or restli ID to delete."),
) -> None:
    """Delete a post by its ID."""
    api = _api()
    try:
        result = api.delete_post(post_id)
    except Exception as exc:
        output_error(f"Failed to delete post: {exc}")
    output(result, human=f"[green]Post deleted.[/green]  id: {result['id']}")


@app.command("list")
def list_posts(
    count: int = typer.Option(10, "--count", "-n", help="Number of posts to fetch."),
) -> None:
    """List your recent posts."""
    api = _api()
    try:
        posts = api.get_posts(count=count)
    except Exception as exc:
        output_error(f"Failed to fetch posts: {exc}")

    # Slim down for display
    rows = []
    for p in posts:
        rows.append(
            {
                "id": p.get("id", ""),
                "commentary": (p.get("commentary", "") or "")[:80],
                "visibility": p.get("visibility", ""),
                "created": p.get("createdAt", ""),
            }
        )
    output(rows)
