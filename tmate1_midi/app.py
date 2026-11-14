"""Application state and the CLI/tray/web lifecycle."""

from __future__ import annotations

import copy
import logging
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from . import __version__
from .config import (
    default_config,
    load_config,
    save_config,
    validate_config,
)
from .engine import MidiEngine
from .midi import MidiOut, NullMidiOut
from .web import WebServer

log = logging.getLogger(__name__)


class AppState:
    def __init__(
        self,
        config: dict[str, Any],
        config_path: Path,
        midi: Any,
        engine: MidiEngine,
    ):
        self.config = config
        self.config_path = Path(config_path)
        self.midi = midi
        self.engine = engine
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._saved_at: float | None = None

    @property
    def stop_requested(self) -> bool:
        return self._stop.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._stop.wait(timeout)

    def request_stop(self) -> None:
        self._stop.set()
        self.engine.stop()

    def shutdown(self) -> None:
        self.engine.stop()
        self.engine.join(2.0)
        self.midi.close()

    def snapshot(self, refresh_ports: bool = False) -> dict[str, Any]:
        with self._lock:
            config = copy.deepcopy(self.config)
            saved_at = self._saved_at
        return {
            "version": __version__,
            "config": config,
            "config_path": str(self.config_path),
            "saved_at": saved_at,
            "midi": self.midi.status(refresh_ports=refresh_ports),
            "device": self.engine.status(),
        }

    def _apply(self, config: Any) -> dict[str, Any]:
        config = validate_config(config)
        save_config(self.config_path, config)
        with self._lock:
            self.config = config
            self._saved_at = time.time()
            saved_at = self._saved_at
        self.engine.set_config(config)
        self.midi.configure(config["midi"]["port"], config["midi"]["virtual"])
        self.midi.ensure_open(force=True)
        return {
            "config": config,
            "saved_at": saved_at,
            "midi": self.midi.status(),
            "device": self.engine.status(),
        }

    def apply_config(self, config: Any) -> dict[str, Any]:
        return self._apply(config)

    def reset_config(self) -> dict[str, Any]:
        return self._apply(default_config())

    def reload_config(self) -> dict[str, Any]:
        return self._apply(load_config(self.config_path, create=True))

    def test_control(self, control: str, direction: int = -1) -> list[str]:
        return self.engine.test_control(control, direction)

    def clear_activity(self) -> None:
        self.engine.clear_activity()


def _open_browser_later(url: str) -> None:
    def run() -> None:
        time.sleep(0.6)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=run, name="tmate1-midi-browser", daemon=True).start()


def run_app(
    config: dict[str, Any],
    config_path: Path | str,
    *,
    dry_run: bool = False,
    enable_web: bool = True,
    enable_tray: bool = True,
    open_browser: bool = False,
    duration: float | None = None,
) -> None:
    config_path = Path(config_path)
    log.info("TMate MIDI %s", __version__)
    log.info("config: %s", config_path)
    if dry_run:
        log.info("dry run: MIDI messages are logged, not sent")

    if dry_run:
        midi: Any = NullMidiOut()
    else:
        midi = MidiOut(config["midi"]["port"], config["midi"]["virtual"])

    engine = MidiEngine(config, midi)
    state = AppState(config, config_path, midi, engine)
    engine.start()

    server: WebServer | None = None
    url: str | None = None
    if enable_web:
        static_dir = Path(__file__).resolve().parent / "static"
        try:
            server = WebServer(
                state,
                config["web"]["host"],
                int(config["web"]["port"]),
                static_dir,
            )
            server.start()
            host = config["web"]["host"]
            if host in ("0.0.0.0", "::"):
                host = "127.0.0.1"
            url = f"http://{host}:{config['web']['port']}/"
            log.info("configurator: %s", url)
        except OSError as exc:
            log.error("cannot start web configurator: %s", exc)
            server = None

    if open_browser and url is not None:
        _open_browser_later(url)

    try:
        tray_ran = False
        if enable_tray and duration is None:
            try:
                from .tray import run_tray

                run_tray(state, url)
                tray_ran = True
            except ImportError as exc:
                log.warning("tray unavailable: %s", exc)
            except Exception as exc:
                log.warning("tray failed: %s", exc)

        if not tray_ran:
            log.info("running without tray; press Ctrl+C to stop")
            deadline = time.monotonic() + duration if duration else None
            try:
                while not state.stop_requested:
                    if deadline is not None and time.monotonic() >= deadline:
                        break
                    state.wait(0.25)
            except KeyboardInterrupt:
                log.info("interrupted")
    finally:
        state.shutdown()
        if server is not None:
            server.stop()
        log.info("stopped")
