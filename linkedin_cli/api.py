"""LinkedIn REST API client — wraps all HTTP calls to LinkedIn."""

from __future__ import annotations

import base64
import json
import webbrowser
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from .config import Settings
from .token import is_token_expired, load_token, load_token_raw, save_token


class LinkedInAPI:
    """Thin wrapper around the LinkedIn v2 REST API."""

    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_BASE = "https://api.linkedin.com"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None
        self._author_urn: str | None = None

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def build_auth_url(self) -> str:
        return (
            f"{self.AUTH_URL}"
            f"?response_type=code"
            f"&client_id={self.settings.client_id}"
            f"&redirect_uri={self.settings.redirect_uri}"
            f"&scope={self.settings.scopes.replace(' ', '%20')}"
        )

    def open_auth_in_browser(self) -> str:
        """Open the consent page and return the authorization URL."""
        url = self.build_auth_url()
        webbrowser.open(url)
        return url

    @staticmethod
    def extract_code_from_url(raw: str) -> str:
        """Accept a full redirect URL or bare code and return the code."""
        if "code=" in raw:
            parsed = parse_qs(urlparse(raw).query)
            return parsed["code"][0]
        return raw.strip()

    def exchange_code(self, code: str) -> dict:
        """Exchange an authorization code for tokens."""
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.settings.redirect_uri,
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        if "id_token" not in data:
            raise RuntimeError("LinkedIn response missing id_token — check your scopes include 'openid'.")
        save_token(data, self.settings)
        return data

    # ------------------------------------------------------------------
    # Token / identity
    # ------------------------------------------------------------------

    def ensure_token(self) -> str:
        """Return a valid access_token, auto-refreshing if expired."""
        if self._access_token:
            return self._access_token

        # Try loading a non-expired token first
        data = load_token(self.settings)
        if data:
            self._access_token = data["access_token"]
            self._author_urn = self._urn_from_id_token(data["id_token"])
            return self._access_token

        # Token expired — try to auto-refresh
        raw = load_token_raw(self.settings)
        if raw and raw.get("refresh_token"):
            try:
                data = self.refresh_access_token(raw["refresh_token"])
                self._access_token = data["access_token"]
                self._author_urn = self._urn_from_id_token(data["id_token"])
                return self._access_token
            except Exception:
                pass  # refresh failed — fall through to login prompt

        raise SystemExit(
            "No valid token found and refresh failed. Run `linkedin auth login` to re-authenticate."
        )

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Use a refresh_token to obtain a new access_token (+ new refresh_token)."""
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        # Preserve id_token from previous session if LinkedIn doesn't return a new one
        if "id_token" not in data:
            raw = load_token_raw(self.settings)
            if raw and "id_token" in raw:
                data["id_token"] = raw["id_token"]
            else:
                raise RuntimeError("Refresh succeeded but no id_token available.")
        save_token(data, self.settings)
        return data

    def author_urn(self) -> str:
        self.ensure_token()
        assert self._author_urn
        return self._author_urn

    @staticmethod
    def _urn_from_id_token(id_token: str) -> str:
        payload_b64 = id_token.split(".")[1]
        padding = "=" * (-len(payload_b64) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64 + padding)
        return f"urn:li:person:{json.loads(decoded)['sub']}"

    def _headers(self, *, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.ensure_token()}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": self.settings.api_version,
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------

    def create_text_post(self, message: str) -> dict[str, Any]:
        """Create a text-only post. Returns {id, url?}."""
        body = {
            "author": self.author_urn(),
            "commentary": message,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
        }
        r = requests.post(f"{self.API_BASE}/rest/posts", headers=self._headers(), json=body)
        r.raise_for_status()
        post_id = r.headers.get("x-restli-id", "")
        return {"id": post_id, "status": "published"}

    def create_image_post(self, message: str, image_path: str) -> dict[str, Any]:
        """Upload an image and create a post with it."""
        # Step 1: Initialize the upload
        init_body = {
            "initializeUploadRequest": {
                "owner": self.author_urn(),
            }
        }
        init_resp = requests.post(
            f"{self.API_BASE}/rest/images?action=initializeUpload",
            headers=self._headers(),
            json=init_body,
        )
        init_resp.raise_for_status()
        upload_data = init_resp.json()["value"]
        upload_url = upload_data["uploadUrl"]
        image_urn = upload_data["image"]

        # Step 2: Upload the binary image
        with open(image_path, "rb") as img:
            image_bytes = img.read()

        upload_resp = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {self.ensure_token()}",
                "Content-Type": "application/octet-stream",
            },
            data=image_bytes,
        )
        upload_resp.raise_for_status()

        # Step 3: Create the post referencing the image
        body = {
            "author": self.author_urn(),
            "commentary": message,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "content": {
                "media": {
                    "id": image_urn,
                }
            },
        }
        r = requests.post(f"{self.API_BASE}/rest/posts", headers=self._headers(), json=body)
        r.raise_for_status()
        post_id = r.headers.get("x-restli-id", "")
        return {"id": post_id, "image_urn": image_urn, "status": "published"}

    def delete_post(self, post_id: str) -> dict[str, Any]:
        """Delete a post by its URN or restli id."""
        # If it's a bare ID, construct the URN
        if not post_id.startswith("urn:"):
            post_id = f"urn:li:share:{post_id}"

        encoded = requests.utils.quote(post_id, safe="")
        r = requests.delete(
            f"{self.API_BASE}/rest/posts/{encoded}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return {"id": post_id, "status": "deleted"}

    def get_posts(self, count: int = 10) -> list[dict[str, Any]]:
        """Fetch recent posts by the authenticated user."""
        author = requests.utils.quote(self.author_urn(), safe="")
        r = requests.get(
            f"{self.API_BASE}/rest/posts?author={author}&q=author&count={count}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json().get("elements", [])

    # ------------------------------------------------------------------
    # Article / link posts
    # ------------------------------------------------------------------

    def create_article_post(self, message: str, url: str, title: str | None = None) -> dict[str, Any]:
        """Create a post with a link/article attachment."""
        article: dict[str, Any] = {"source": url}
        if title:
            article["title"] = title

        body = {
            "author": self.author_urn(),
            "commentary": message,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "content": {
                "article": article,
            },
        }
        r = requests.post(f"{self.API_BASE}/rest/posts", headers=self._headers(), json=body)
        r.raise_for_status()
        post_id = r.headers.get("x-restli-id", "")
        return {"id": post_id, "status": "published", "url": url}

    # ------------------------------------------------------------------
    # Video posts
    # ------------------------------------------------------------------

    def create_video_post(self, message: str, video_path: str) -> dict[str, Any]:
        """Upload a video and create a post with it."""
        import os

        file_size = os.path.getsize(video_path)

        # Step 1: Initialize the video upload
        init_body = {
            "initializeUploadRequest": {
                "owner": self.author_urn(),
                "fileSizeBytes": file_size,
            }
        }
        init_resp = requests.post(
            f"{self.API_BASE}/rest/videos?action=initializeUpload",
            headers=self._headers(),
            json=init_body,
        )
        init_resp.raise_for_status()
        upload_data = init_resp.json()["value"]
        upload_url = upload_data["uploadInstructions"][0]["uploadUrl"]
        video_urn = upload_data["video"]

        # Step 2: Upload the binary video
        with open(video_path, "rb") as vid:
            video_bytes = vid.read()

        upload_resp = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {self.ensure_token()}",
                "Content-Type": "application/octet-stream",
            },
            data=video_bytes,
        )
        upload_resp.raise_for_status()

        # Step 3: Create the post referencing the video
        body = {
            "author": self.author_urn(),
            "commentary": message,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "content": {
                "media": {
                    "id": video_urn,
                }
            },
        }
        r = requests.post(f"{self.API_BASE}/rest/posts", headers=self._headers(), json=body)
        r.raise_for_status()
        post_id = r.headers.get("x-restli-id", "")
        return {"id": post_id, "video_urn": video_urn, "status": "published"}

    # ------------------------------------------------------------------
    # Poll posts
    # ------------------------------------------------------------------

    def create_poll_post(self, question: str, options: list[str], duration: str = "THREE_DAYS") -> dict[str, Any]:
        """Create a poll post. duration: ONE_DAY, THREE_DAYS, ONE_WEEK, TWO_WEEKS."""
        poll_options = [{"text": opt} for opt in options]

        body = {
            "author": self.author_urn(),
            "commentary": question,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "content": {
                "poll": {
                    "question": question,
                    "options": poll_options,
                    "settings": {
                        "duration": duration,
                    },
                }
            },
        }
        r = requests.post(f"{self.API_BASE}/rest/posts", headers=self._headers(), json=body)
        r.raise_for_status()
        post_id = r.headers.get("x-restli-id", "")
        return {"id": post_id, "status": "published", "options": options, "duration": duration}

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def create_comment(self, post_urn: str, message: str) -> dict[str, Any]:
        """Comment on a post."""
        if not post_urn.startswith("urn:"):
            post_urn = f"urn:li:share:{post_urn}"

        encoded = requests.utils.quote(post_urn, safe="")
        body = {
            "actor": self.author_urn(),
            "message": {"text": message},
        }
        r = requests.post(
            f"{self.API_BASE}/rest/socialActions/{encoded}/comments",
            headers=self._headers(),
            json=body,
        )
        r.raise_for_status()
        comment_data = r.json() if r.text else {}
        comment_id = comment_data.get("id", r.headers.get("x-restli-id", ""))
        return {"post_id": post_urn, "comment_id": comment_id, "status": "commented"}

    # ------------------------------------------------------------------
    # Reactions
    # ------------------------------------------------------------------

    REACTION_TYPES = ("LIKE", "CELEBRATE", "SUPPORT", "LOVE", "INSIGHTFUL", "FUNNY")

    def react_to_post(self, post_urn: str, reaction_type: str = "LIKE") -> dict[str, Any]:
        """React to a post. Types: LIKE, CELEBRATE, SUPPORT, LOVE, INSIGHTFUL, FUNNY."""
        reaction_type = reaction_type.upper()
        if reaction_type not in self.REACTION_TYPES:
            raise ValueError(f"Invalid reaction type '{reaction_type}'. Must be one of: {', '.join(self.REACTION_TYPES)}")

        if not post_urn.startswith("urn:"):
            post_urn = f"urn:li:share:{post_urn}"

        encoded = requests.utils.quote(post_urn, safe="")
        body = {
            "root": post_urn,
            "reactionType": reaction_type,
        }
        r = requests.post(
            f"{self.API_BASE}/rest/reactions",
            headers=self._headers(),
            json=body,
        )
        r.raise_for_status()
        return {"post_id": post_urn, "reaction": reaction_type, "status": "reacted"}

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self) -> dict[str, Any]:
        """Fetch the current user's profile via /rest/me (userinfo)."""
        r = requests.get(
            f"{self.API_BASE}/v2/userinfo",
            headers={
                "Authorization": f"Bearer {self.ensure_token()}",
            },
        )
        r.raise_for_status()
        return r.json()
