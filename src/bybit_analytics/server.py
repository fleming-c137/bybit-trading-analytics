"""Local dashboard server: static files from public/ plus /api/report.

    python -m bybit_analytics serve        # http://localhost:8000

Same frontend and API as the Vercel deployment, with one extra data source:
the SQLite database on this machine.
"""

from __future__ import annotations

import json
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

from .config import PROJECT_ROOT
from .webapi import handle

PUBLIC_DIR = PROJECT_ROOT / "public"
MAX_BODY = 8_000_000


class DashboardHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter, and never logs request bodies
        if not self.path.startswith("/api/"):
            return
        super().log_message(fmt, *args)

    def _send_json(self, status: int, body: dict, headers: dict) -> None:
        data = json.dumps(body, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/api/report":
            self._send_json(*handle(dict(parse_qsl(url.query)), allow_local=True))
            return
        super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/report":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send_json(413, {"error": "Request too large."}, {})
            return
        try:
            params = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send_json(400, {"error": "Invalid JSON."}, {})
            return
        self._send_json(*handle(params, allow_local=True))


def serve(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    httpd = ThreadingHTTPServer((host, port), partial(DashboardHandler, directory=str(PUBLIC_DIR)))
    url = f"http://{'localhost' if host in {'127.0.0.1', '0.0.0.0'} else host}:{port}"
    print(f"Dashboard running at {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
