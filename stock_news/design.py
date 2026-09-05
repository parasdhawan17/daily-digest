"""Presentation-only feature flag. This does not enable random experimentation."""
import os
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DESIGNS = ("legacy", "modern")


def resolve_design(override: str | None = None) -> str:
    """Allowlisted request override, then deployment flag; modern by default."""
    if override in DESIGNS:
        return override
    configured = os.environ.get("DIGEST_DESIGN", "modern").strip().lower()
    if configured not in DESIGNS:
        raise ValueError("DIGEST_DESIGN must be legacy or modern")
    return configured


def design_url(url: str | None, design: str) -> str | None:
    """Pin an email's web link to its design without changing the signed token."""
    if not url:
        return url
    if design not in DESIGNS:
        raise ValueError("Unknown design")
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "design"]
    query.append(("design", design))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def design_for_recipient(email: str) -> str:
    """Use a targeted recipient override, otherwise keep the deployment default."""
    path = Path(__file__).resolve().parent.parent / "config" / "design_overrides.json"
    overrides = json.loads(path.read_text()) if path.exists() else {}
    normalized = email.strip().casefold()
    variant = overrides.get(normalized)
    if variant is not None and variant not in DESIGNS:
        raise ValueError("Recipient design override must be legacy or modern")
    return resolve_design(variant)
