from __future__ import annotations

import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath
from urllib.parse import urlsplit


TARGET_HOST = "target"
TARGET_PORT = 8080
ALLOWED_HEADERS = {"accept", "content-type", "x-lab-key", "x-user-id"}
MAX_BODY_BYTES = 16_384
MAX_RESPONSE_BYTES = 20_000


def is_safe_path(path: str) -> bool:
    parsed = urlsplit(path)
    return (
        path.startswith("/")
        and not parsed.scheme
        and not parsed.netloc
        and ".." not in PurePosixPath(parsed.path).parts
    )


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "LocalLLMLabProxy/1.0"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, method: str) -> None:
        if not is_safe_path(self.path):
            self._send(400, "application/json", b'{"error":"invalid path"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, "application/json", b'{"error":"invalid content length"}')
            return
        if length > MAX_BODY_BYTES:
            self._send(413, "application/json", b'{"error":"request too large"}')
            return
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.casefold() in ALLOWED_HEADERS
        }
        connection = http.client.HTTPConnection(TARGET_HOST, TARGET_PORT, timeout=5)
        try:
            connection.request(method, self.path, body=body, headers=headers)
            response = connection.getresponse()
            content = response.read(MAX_RESPONSE_BYTES)
            self._send(response.status, response.getheader("Content-Type", "application/octet-stream"), content)
        except (OSError, http.client.HTTPException) as exc:
            content = json.dumps({"error": f"isolated target unavailable: {exc}"}).encode("utf-8")
            self._send(502, "application/json", content)
        finally:
            connection.close()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._proxy("GET")

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._proxy("POST")


def main() -> None:
    ThreadingHTTPServer(("0.0.0.0", 8080), ProxyHandler).serve_forever()


if __name__ == "__main__":
    main()
