"""Local web configurator."""

from __future__ import annotations

import json
import logging
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import ConfigError

log = logging.getLogger(__name__)


def _make_handler(state: Any, static_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "tmate1-midi/0.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            log.debug("web: " + fmt, *args)

        def _send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
            try:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _send_json(self, payload: Any, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self._send_bytes(body, "application/json; charset=utf-8", status)

        def _send_file(self, path: Path, content_type: str) -> None:
            try:
                body = path.read_bytes()
            except OSError:
                self._send_json({"ok": False, "error": "not found"}, 404)
                return
            self._send_bytes(body, content_type)

        def _read_json(self) -> Any:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if length == 0:
                return {}
            if length < 0 or length > 1_000_000:
                raise ValueError("invalid request body")
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid JSON: {exc}") from exc

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path in ("/", "/index.html"):
                self._send_file(
                    static_dir / "index.html", "text/html; charset=utf-8"
                )
            elif path == "/api/state":
                query = urllib.parse.parse_qs(parsed.query)
                refresh_ports = query.get("ports", ["0"])[0].lower() in (
                    "1",
                    "true",
                    "yes",
                )
                self._send_json(self.state.snapshot(refresh_ports=refresh_ports))
            elif path == "/favicon.ico":
                self._send_bytes(b"", "image/x-icon", 204)
            else:
                self._send_json({"ok": False, "error": "not found"}, 404)

        @property
        def state(self) -> Any:
            return state

        def do_POST(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            try:
                body = self._read_json()
                if path == "/api/config":
                    if not isinstance(body, dict) or not body:
                        raise ValueError("config body is empty")
                    config = body.get("config", body)
                    result = self.state.apply_config(config)
                    self._send_json({"ok": True, **result})
                elif path == "/api/test":
                    if not isinstance(body, dict):
                        raise ValueError("request body must be an object")
                    control = body.get("control")
                    if not isinstance(control, str):
                        raise ValueError("control must be a string")
                    direction = int(body.get("direction", -1))
                    if direction not in (-1, 0, 1):
                        raise ValueError("direction must be -1, 0 or 1")
                    messages = self.state.test_control(control, direction)
                    self._send_json({"ok": True, "messages": messages})
                elif path == "/api/reset":
                    result = self.state.reset_config()
                    self._send_json({"ok": True, **result})
                elif path == "/api/reload":
                    result = self.state.reload_config()
                    self._send_json({"ok": True, **result})
                elif path == "/api/clear-activity":
                    self.state.clear_activity()
                    self._send_json({"ok": True})
                elif path == "/api/quit":
                    self.state.request_stop()
                    self._send_json({"ok": True})
                else:
                    self._send_json({"ok": False, "error": "not found"}, 404)
            except ConfigError as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            except (ValueError, TypeError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            except Exception as exc:
                log.exception("web request failed")
                self._send_json({"ok": False, "error": str(exc)}, 500)

    return Handler


class WebServer:
    def __init__(self, state: Any, host: str, port: int, static_dir: Path):
        self.state = state
        self.host = host
        self.port = port
        self.static_dir = Path(static_dir)
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.httpd is not None:
            return
        handler = _make_handler(self.state, self.static_dir)
        self.httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self.thread = threading.Thread(
            target=self.httpd.serve_forever,
            name="tmate1-midi-web",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        if self.httpd is None:
            return
        self.httpd.shutdown()
        self.httpd.server_close()
        self.httpd = None
        if self.thread is not None:
            self.thread.join(2.0)
            self.thread = None
