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


def get_contact(email: str, api_key: str) -> dict | None:
    response = requests.get(
        f"https://api.brevo.com/v3/contacts/{email}",
        headers=_headers(api_key),
        timeout=30,
    )
    if response.status_code == 404:
        return None
    if not response.ok:
        raise BrevoError(_safe_brevo_message(response))
    return response.json()


def get_ticker_catalog_options(api_key: str, attr_name: str = BREVO_TICKERS_ATTRIBUTE) -> list[str]:
    response = requests.get(
        "https://api.brevo.com/v3/contacts/attributes",
        headers=_headers(api_key),
        timeout=30,
    )
    if not response.ok:
        raise BrevoError(_safe_brevo_message(response))
    for attribute in response.json().get("attributes", []):
        if attribute.get("name", "").upper() == attr_name.upper():
            return [str(opt).strip().upper() for opt in (attribute.get("multiCategoryOptions") or [])]
    return []


def ensure_ticker_catalog_options(
    tickers: list[str],
    api_key: str,
    attr_name: str = BREVO_TICKERS_ATTRIBUTE,
) -> None:
    existing = set(get_ticker_catalog_options(api_key, attr_name))
    if all(ticker in existing for ticker in tickers):
        return
    merged = sorted(existing | set(tickers))
    response = requests.put(
        f"https://api.brevo.com/v3/contacts/attributes/normal/{attr_name}",
        headers=_headers(api_key),
        json={"multiCategoryOptions": merged},
        timeout=30,
    )
    if not response.ok:
        raise BrevoError(_safe_brevo_message(response))


def update_contact_tickers(
    email: str,
    tickers: list[str],
    api_key: str,
    attr_name: str = BREVO_TICKERS_ATTRIBUTE,
) -> None:
    response = requests.put(
        f"https://api.brevo.com/v3/contacts/{email}",
        headers=_headers(api_key),
        json={"attributes": {attr_name: tickers}},
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
            "attributes": {attr_name: tickers},
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
    ensure_ticker_catalog_options(tickers, api_key, attr_name)
    contact = get_contact(email, api_key)
    redirection_url = f"{(site_url or SITE_URL or '').rstrip('/')}/" or "/"

    if contact and not contact.get("emailBlacklisted"):
        contact_lists = contact.get("listIds") or []
        if list_id in contact_lists:
            update_contact_tickers(email, tickers, api_key, attr_name)
            return {
                "ok": True,
                "mode": "update",
                "message": "Your holdings are updated for the next session.",
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


def fetch_subscribers_with_tickers(list_id: int, api_key: str) -> list[dict]:
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
            raw_tickers = attributes.get(BREVO_TICKERS_ATTRIBUTE, "")
            tickers = parse_tickers(raw_tickers)
            subscribers.append({"email": email, "tickers": tickers})

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
) -> None:
    payload_base = {
        "sender": {"name": sender_name, "email": sender_email},
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }

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
        print(f"Email sent to {recipient_email} ({index}/{total}): {message_id}")
        if index < total:
            time.sleep(SEND_DELAY_SECONDS)


def _safe_brevo_message(response: requests.Response) -> str:
    try:
        payload = response.json()
        message = payload.get("message") or payload.get("code") or response.text
    except ValueError:
        message = response.text
    return str(message).strip() or "Brevo request failed"
