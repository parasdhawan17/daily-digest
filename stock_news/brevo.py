"""Brevo Contacts API for subscribe / update tickers."""

import time

import requests

from stock_news.config import BREVO_TICKERS_ATTRIBUTE, SEND_DELAY_SECONDS, SITE_URL
from stock_news.relevance import parse_tickers


class BrevoError(Exception):
    """Brevo API or configuration error."""


def _headers(api_key: str) -> dict[str, str]:
    return {
        "api-key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def format_tickers_attribute(tickers: list[str]) -> str:
    """Serialize tickers for a Brevo text attribute (comma-separated)."""
    return ", ".join(parse_tickers(tickers))


def _get_contact_attribute(attributes: dict | None, name: str):
    if not attributes:
        return ""
    target = name.upper()
    for key, value in attributes.items():
        if str(key).upper() == target:
            return value
    return ""


def get_contact(identifier: str | int, api_key: str) -> dict | None:
    response = requests.get(
        f"https://api.brevo.com/v3/contacts/{identifier}",
        headers=_headers(api_key),
        timeout=30,
    )
    if response.status_code == 404:
        return None
    if not response.ok:
        raise BrevoError(_safe_brevo_message(response))
    return response.json()


def update_contact_tickers(
    email: str,
    tickers: list[str],
    api_key: str,
    attr_name: str = BREVO_TICKERS_ATTRIBUTE,
    *,
    list_id: int | None = None,
) -> None:
    payload: dict = {"attributes": {attr_name: format_tickers_attribute(tickers)}}
    if list_id is not None:
        payload["listIds"] = [list_id]

    response = requests.put(
        f"https://api.brevo.com/v3/contacts/{email}",
        headers=_headers(api_key),
        json=payload,
        timeout=30,
    )
    if not response.ok:
        raise BrevoError(_safe_brevo_message(response))


def create_doi_contact(
    email: str,
    tickers: list[str],
    api_key: str,
    list_id: int,
    template_id: int,
    redirection_url: str,
    attr_name: str = BREVO_TICKERS_ATTRIBUTE,
) -> None:
    response = requests.post(
        "https://api.brevo.com/v3/contacts/doubleOptinConfirmation",
        headers=_headers(api_key),
        json={
            "email": email,
            "includeListIds": [list_id],
            "templateId": template_id,
            "redirectionUrl": redirection_url,
            "attributes": {attr_name: format_tickers_attribute(tickers)},
        },
        timeout=30,
    )
    if not response.ok:
        raise BrevoError(_safe_brevo_message(response))


def subscribe_or_update(
    email: str,
    tickers: list[str],
    api_key: str,
    list_id: int,
    template_id: int,
    *,
    attr_name: str = BREVO_TICKERS_ATTRIBUTE,
    site_url: str | None = None,
) -> dict:
    contact = get_contact(email, api_key)
    redirection_url = f"{(site_url or SITE_URL or '').rstrip('/')}/welcome" or "/welcome"

    if contact and not contact.get("emailBlacklisted"):
        contact_lists = contact.get("listIds") or []
        on_list = list_id in contact_lists
        update_contact_tickers(
            email,
            tickers,
            api_key,
            attr_name,
            list_id=None if on_list else list_id,
        )
        return {
            "ok": True,
            "mode": "update",
            "message": "Your tickers are updated for the next session.",
        }

    create_doi_contact(
        email,
        tickers,
        api_key,
        list_id,
        template_id,
        redirection_url,
        attr_name,
    )
    return {
        "ok": True,
        "mode": "doi",
        "message": "Check your email to confirm your subscription.",
    }


def fetch_subscribers_with_tickers(
    list_id: int,
    api_key: str,
    attr_name: str = BREVO_TICKERS_ATTRIBUTE,
) -> list[dict]:
    subscribers: list[dict] = []
    offset = 0
    limit = 50

    while True:
        response = requests.get(
            "https://api.brevo.com/v3/contacts",
            headers=_headers(api_key),
            params={"limit": limit, "offset": offset, "listIds": [list_id]},
            timeout=30,
        )
        if not response.ok:
            raise BrevoError(_safe_brevo_message(response))
        contacts = response.json().get("contacts", [])
        if not contacts:
            break

        for contact in contacts:
            if contact.get("emailBlacklisted"):
                continue
            email = contact.get("email", "").strip()
            if not email:
                continue
            attributes = contact.get("attributes") or {}
            raw_tickers = _get_contact_attribute(attributes, attr_name)
            tickers = parse_tickers(raw_tickers)
            subscribers.append(
                {"id": contact.get("id"), "email": email, "tickers": tickers}
            )

        if len(contacts) < limit:
            break
        offset += limit

    return subscribers


def send_transactional_email(
    html: str,
    text: str,
    api_key: str,
    sender_email: str,
    recipients: list[str],
    sender_name: str,
    subject: str,
    scheduled_at: str | None = None,
) -> None:
    payload_base = {
        "sender": {"name": sender_name, "email": sender_email},
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }
    if scheduled_at:
        payload_base["scheduledAt"] = scheduled_at

    total = len(recipients)
    for index, recipient_email in enumerate(recipients, start=1):
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers=_headers(api_key),
            json={**payload_base, "to": [{"email": recipient_email}]},
            timeout=30,
        )
        if not response.ok:
            raise BrevoError(_safe_brevo_message(response))
        message_id = response.json().get("messageId", response.text)
        action = "scheduled" if scheduled_at else "sent"
        print(f"Email {action} to {recipient_email} ({index}/{total}): {message_id}")
        if index < total:
            time.sleep(SEND_DELAY_SECONDS)


def _safe_brevo_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        message = payload.get("message") or payload.get("code") or response.text
    except ValueError:
        message = response.text
    return str(message).strip() or "Brevo request failed"
