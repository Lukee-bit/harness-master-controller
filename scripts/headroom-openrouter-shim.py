#!/usr/bin/env python3
"""Local rewrite shim: Headroom -> OpenRouter /cursor endpoint.

Headroom appends ``/v1/chat/completions`` to whatever ``--openai-api-url`` it is
given, which cannot express OpenRouter's Cursor endpoint
(``https://openrouter.ai/api/v1/cursor/chat/completions``). This shim sits
between Headroom and OpenRouter: Headroom forwards the (already compressed)
request here, the shim rewrites the path to the ``/cursor`` endpoint and injects
the OpenRouter credential that Cursor's single ``Authorization`` slot cannot
carry alongside the gate token.

Reads the key from ``~/.headroom/openrouter_key.env`` (``OPENROUTER_API_KEY=``).
Stdlib only, streaming relay so SSE survives.
"""

from __future__ import annotations

import http.client
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OR_HOST = "openrouter.ai"
OR_CURSOR_PATH = "/api/v1/cursor/chat/completions"
KEY_ENV = Path.home() / ".headroom/openrouter_key.env"
LISTEN_HOST = os.environ.get("HEADROOM_SHIM_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("HEADROOM_SHIM_PORT", "8899"))
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "authorization",
    "content-length",
}


def _load_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key and KEY_ENV.is_file():
        for line in KEY_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip()
    return key


class Shim(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _relay(self) -> None:
        if not self.server.api_key:  # type: ignore[attr-defined]
            self.send_error(500, "OPENROUTER_API_KEY not set")
            return
        length = int(self.headers.get("content-length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        headers = {
            k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP
        }
        headers["Authorization"] = f"Bearer {self.server.api_key}"  # type: ignore[attr-defined]
        headers["Host"] = OR_HOST
        conn = http.client.HTTPSConnection(OR_HOST, timeout=300)
        try:
            conn.request("POST", OR_CURSOR_PATH, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in HOP_BY_HOP:
                    self.send_header(k, v)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(f"{len(chunk):X}\r\n".encode())
                self.wfile.write(chunk + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
        finally:
            conn.close()

    def do_POST(self) -> None:  # noqa: N802
        self._relay()

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("shim " + (fmt % args) + "\n")


def main() -> None:
    key = _load_key()
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Shim)
    server.api_key = key  # type: ignore[attr-defined]
    state = "key loaded" if key else "NO KEY (set OPENROUTER_API_KEY in ~/.headroom/openrouter_key.env)"
    print(f"shim on http://{LISTEN_HOST}:{LISTEN_PORT} -> https://{OR_HOST}{OR_CURSOR_PATH} ({state})")
    server.serve_forever()


if __name__ == "__main__":
    main()
