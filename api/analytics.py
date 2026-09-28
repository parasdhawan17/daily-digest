"""Public, non-secret analytics configuration for the browser client."""

import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from api._responses import send_json


DEFAULT_POSTHOG_HOST = "https://us.i.posthog.com"


def _posthog_host() -> str:
    candidate = os.environ.get("POSTHOG_HOST", "").strip().rstrip("/")
    if not candidate:
        return DEFAULT_POSTHOG_HOST
    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return DEFAULT_POSTHOG_HOST
    return candidate


def handle_get(handler: BaseHTTPRequestHandler) -> None:
    project_key = os.environ.get("POSTHOG_PROJECT_KEY", "").strip()
    send_json(
        handler,
        200,
        {
            "ok": True,
            "enabled": bool(project_key),
            "project_key": project_key,
            "host": _posthog_host(),
        },
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=3600"},
    )
