"""Create a clearly labeled public demo from the checked-in digest preview.

Run after refreshing preview-digest.html to keep the landing demo in sync.
No API calls or subscriber data are used.
"""
from pathlib import Path
import re
import os

ROOT = Path(__file__).resolve().parent.parent
variant = os.environ.get("DIGEST_DESIGN", "modern").strip().lower()
if variant not in ("legacy", "modern"):
    raise ValueError("DIGEST_DESIGN must be legacy or modern")
output_dir = ROOT / 'public' / ('legacy' if variant == 'legacy' else '')
html = (output_dir / 'preview-digest.html').read_text()
html = re.sub(r'<title>.*?</title>', '<title>Sample web digest — Tickr Digest</title>', html, count=1)
html = html.replace('</head>', '<meta name="robots" content="noindex">\n</head>')
html = html.replace('<body>', '''<body>
<aside style="padding:16px 24px;background:#a8edca;color:#102c23;text-align:center;font:14px/1.6 system-ui">
<strong>Explore a sample digest.</strong> All prices, news, AI summaries, and earnings below are illustrative, not live data.
<a href="/" style="color:#102c23;font-weight:700;margin-left:12px">Back to Tickr Digest →</a>
</aside>''', 1)
# Fictional preview stories must not be attributed to actual publishers or link to dummy URLs.
html = re.sub(r'<a href="https://example\.com/[^\"]*"[^>]*>(.*?)</a>', r'<span>\1</span>', html)
for source in ('Reuters', 'Bloomberg', 'CNBC', 'Economic Times', 'Mint', 'Moneycontrol'):
    html = html.replace(source, 'Sample source')
html = html.replace('data-prefill-email="investor@example.com"', 'data-prefill-email=""')
html = html.replace('Update your tickers', 'Create your own briefing')
html = html.replace('>Edit</', '>Try these tickers</')
html = html.replace('http://localhost:8765', '')
if variant == 'legacy':
    html = html.replace('href="/"', 'href="/legacy/index.html"')
(output_dir / 'sample-digest.html').write_text(html)
