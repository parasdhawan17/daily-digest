"""Vercel serverless handler for /digest (rewritten from /api/digest)."""

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        token = (query.get("t") or [None])[0]

        if not token:
            self._respond(400, _stub_html("Missing link", "Open the digest link from your email."))
            return

        # TODO: verify token, collect_digest_data, build_web_digest
        self._respond(
            501,
            _stub_html(
                "Coming soon",
                "Digest API scaffold is in place. Implement stock_news + templates next.",
            ),
        )

    def _respond(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _stub_html(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} · Daily Digest</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; }}
    a {{ color: #1d4ed8; }}
  </style>
</head>
<body>
  <h1>Daily Digest</h1>
  <p>{message}</p>
  <p><a href="/">Back to home</a></p>
</body>
</html>"""
