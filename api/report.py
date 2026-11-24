"""Vercel serverless function: /api/report (see src/bybit_analytics/webapi.py)."""

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bybit_analytics.webapi import handle  # noqa: E402

MAX_BODY = 4_500_000  # Vercel's request body limit


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict, headers: dict) -> None:
        data = json.dumps(body, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # never log requests: POST bodies can hold API keys
        pass

    def do_GET(self):
        self._send(*handle(dict(parse_qsl(urlsplit(self.path).query)), allow_local=False))

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(413, {"error": "Request too large (4.5 MB limit)."}, {})
            return
        try:
            params = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send(400, {"error": "Invalid JSON."}, {})
            return
        self._send(*handle(params, allow_local=False))
