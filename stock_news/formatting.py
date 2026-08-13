"""Date, time, and text formatting helpers."""

from datetime import datetime, timezone

from stock_news.config import SUMMARY_EXCERPT_LENGTH


def unix_to_local(unix_ts: int | float) -> datetime:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone()


def local_timezone_label(dt: datetime) -> str:
    return (dt.strftime("%Z") or dt.tzname() or "").strip()


def format_fetched_at_label(dt: datetime) -> str:
    local = dt.astimezone()
    hour = local.hour % 12 or 12
    ampm = "AM" if local.hour < 12 else "PM"
    tz = local_timezone_label(local)
    time_label = f"{hour}:{local.strftime('%M')} {ampm}"
    if tz:
        time_label = f"{time_label} {tz}"
    return f"Fetched on {time_label}"


def format_full_datetime(unix_ts: int | float | None) -> str:
    if not unix_ts:
        return ""
    published = unix_to_local(unix_ts)
    hour = published.hour % 12 or 12
    ampm = "AM" if published.hour < 12 else "PM"
    tz = local_timezone_label(published)
    base = f"{published.day} {published.strftime('%b %Y')}, {hour}:{published.strftime('%M')} {ampm}"
    return f"{base} {tz}".strip() if tz else base


def format_relative_time(unix_ts: int | float | None) -> str:
    if not unix_ts:
        return ""
    published = unix_to_local(unix_ts)
    now = datetime.now().astimezone()
    delta = now - published
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{max(1, minutes)}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return "Yesterday" if days == 1 else f"{days}d ago"


def excerpt_summary(text: str, max_length: int = SUMMARY_EXCERPT_LENGTH) -> str:
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."
