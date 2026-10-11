"""Bundle a public homepage card; failures never block deployment."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://www.mydailydigest.online'
MARKER = '<script type="application/json" id="home-ai-snapshot">'
CATEGORIES = ('encouraging', 'attention', 'changes', 'catalysts', 'risks', 'watch_next')


def validate(payload, hours, now=None):
    """Accept only complete public cards, preserving the AI's original date."""
    try:
        from math import isfinite
        stock = payload['stock']
        overview = payload['overview']
        data = overview['data']
        generated = datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00'))
        age = ((now or datetime.now(timezone.utc)) - generated).total_seconds()
        if not payload.get('ok') or not overview.get('ok') or not 0 <= age < hours * 3600:
            return None
        if not stock['name'].strip() or not re.fullmatch(r'IN:[A-Z][A-Z0-9.&-]{0,19}', stock['symbol']):
            return None
        for field in ('price', 'percent_change', 'market_cap_crore'):
            if isinstance(stock[field], bool) or not isfinite(float(stock[field])):
                return None
        if float(stock['market_cap_crore']) <= 0:
            return None
        sources = {s['id'] for s in data['sources']}
        def item(value, facts=False):
            return (isinstance(value, dict) and bool(value.get('heading', '').strip())
                    and bool(value.get('text', '').strip())
                    and value.get('tone') in ('positive', 'negative', 'caution', 'neutral')
                    and bool(value.get('evidence_ids'))
                    and all(s in sources for s in value['evidence_ids'])
                    and (not facts or bool(value.get('facts')) and all(
                        f.get('label', '').strip() and f.get('value', '').strip() for f in value['facts'])))
        if not item(data['summary']) or not all(isinstance(data[k], list) for k in CATEGORIES):
            return None
        items = [i for k in CATEGORIES for i in data[k]]
        if not items or not all(item(i, True) for i in items):
            return None
        # Publish the known public envelope only, never configuration or headers.
        return {k: payload[k] for k in ('ok', 'stock', 'core', 'overview')}
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return None


def read_previous(path, timeout, hours):
    try:
        response = requests.get(ORIGIN + path, timeout=timeout)
        response.raise_for_status()
        value = response.json()
        if path.endswith('.json'):
            if value.get('format_version') != 1:
                return None
            value = value.get('payload')
        return validate(value, hours)
    except Exception:
        return None


def generate():
    code = "from stock_news.home_ai_signal import get_home_ai_signal; import os,json; print(json.dumps(get_home_ai_signal(os.environ.get('INDIANAPI_API_KEY','').strip())[0]))"
    try:
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                                capture_output=True, text=True, timeout=120, check=True)
        return validate(json.loads(result.stdout), 24)
    except Exception:
        return None


def prepare():
    if os.environ.get('VERCEL_ENV') != 'production':
        return None, 'example: non-production build'
    payload = read_previous('/api/home-ai-signal?selection=market-cap-v1', 10, 24)
    if payload:
        return payload, 'production API'
    if os.environ.get('INDIANAPI_API_KEY', '').strip() and os.environ.get('OPENROUTER_API_KEY', '').strip():
        payload = generate()
        if payload:
            return payload, 'fresh generation'
    payload = read_previous('/home-ai-snapshot.json', 5, 48)
    return payload, 'previous snapshot' if payload else 'example: preparation unavailable'


def write_artifacts(public, payload):
    envelope = {'format_version': 1, 'payload': payload}
    raw = json.dumps(envelope, ensure_ascii=True, separators=(',', ':'))
    (public / 'home-ai-snapshot.json').write_text(raw + '\n')
    safe = raw.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = public / 'index.html'
    html = page.read_text()
    pattern = re.escape(MARKER) + r'.*?</script>'
    if not re.search(pattern, html, flags=re.S):
        raise ValueError('Homepage snapshot marker is missing')
    page.write_text(re.sub(pattern, lambda _: MARKER + safe + '</script>', html, count=1, flags=re.S))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--public-dir', type=Path, default=ROOT / 'public')
    args = parser.parse_args()
    start = time.monotonic()
    payload, source = prepare()
    write_artifacts(args.public_dir, payload)
    age = None
    if payload:
        generated = datetime.fromisoformat(payload['overview']['data']['generated_at'].replace('Z', '+00:00'))
        age = round((datetime.now(timezone.utc) - generated).total_seconds())
    print(json.dumps({'home_snapshot_source': source, 'age_seconds': age,
                      'preparation_seconds': round(time.monotonic() - start, 2)}))


if __name__ == '__main__':
    main()
