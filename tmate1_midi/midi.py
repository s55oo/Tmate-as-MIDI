"""MIDI output with a clear Windows/Linux virtual-port strategy."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any


class MidiUnavailable(RuntimeError):
    pass


def _mido():
    try:
        import mido
    except Exception as exc:
        raise MidiUnavailable(
            "MIDI support is not installed; run: "
            "python -m pip install -r requirements-midi.txt"
        ) from exc
    return mido


def message_hex(message: Any) -> str:
    try:
        return " ".join(f"{byte:02X}" for byte in message.bin())
    except Exception:
        return ""


def message_text(message: Any) -> str:
    if message.type == "control_change":
        return (
            f"CC ch{message.channel + 1} #{message.control} = {message.value}"
        )
    if message.type == "note_on":
        return (
            f"Note on ch{message.channel + 1} #{message.note} "
            f"vel {message.velocity}"
        )
    if message.type == "note_off":
        return (
            f"Note off ch{message.channel + 1} #{message.note} "
            f"vel {message.velocity}"
        )
    return message.type


def resolve_port_name(wanted: str, names: list[str]) -> str | None:
    """Return the real output name that matches ``wanted``.

    On Windows, RtMidi's WinMM backend appends the device index to every
    port name, so a loopMIDI port created as ``TMate 1.0`` is listed as
    ``TMate 1.0 1``.  Prefer an exact match, then ``wanted`` followed by a
    space and a number, then a case-insensitive match of either form.
    """
    if not wanted:
        return None
    if wanted in names:
        return wanted
    target = wanted.strip()
    for fold in (False, True):
        for name in names:
            a, b = (name.casefold(), target.casefold()) if fold else (name, target)
            if a == b:
                return name
            if a.startswith(b + " ") and a[len(b) + 1 :].isdigit():
                return name
    return None


class MidiOut:
    def __init__(self, port: str, virtual: str | bool = "auto"):
        self.port = port or "TMate 1.0"
        self.virtual = virtual
        self._mido = _mido()
        self._out = None
        self._error: str | None = None
        self._ports_error: str | None = None
        self._ports_cache: list[str] | None = None
        self._ports_at = 0.0
        self._last_attempt = 0.0
        self._closed = False
        self._lock = threading.RLock()

    @staticmethod
    def virtual_supported() -> bool:
        return sys.platform.startswith(("linux", "darwin"))

    def _virtual_flag(self) -> bool:
        if isinstance(self.virtual, str) and self.virtual.strip().lower() == "auto":
            return self.virtual_supported()
        return bool(self.virtual)

    def ports(self, refresh: bool = False) -> list[str]:
        with self._lock:
            now = time.monotonic()
            if (
                not refresh
                and self._ports_cache is not None
                and now - self._ports_at < 2.0
            ):
                return list(self._ports_cache)
            try:
                names = list(self._mido.get_output_names())
                self._ports_error = None
            except Exception as exc:
                names = []
                self._ports_error = str(exc)
            if self._virtual_flag():
                names = [name for name in names if name != self.port]
            self._ports_cache = names
            self._ports_at = now
            return list(names)

    def ensure_open(self, force: bool = False) -> bool:
        with self._lock:
            if self._closed:
                return False
            if self._out is not None:
                return True
            now = time.monotonic()
            if not force and now - self._last_attempt < 2.0:
                return False
            self._last_attempt = now
            try:
                virtual = self._virtual_flag()
                name = self.port
                if not virtual:
                    try:
                        names = list(self._mido.get_output_names())
                    except Exception:
                        names = []
                    name = resolve_port_name(self.port, names) or self.port
                self._out = self._mido.open_output(name, virtual=virtual)
                self._error = None
                return True
            except Exception as exc:
                self._error = str(exc)
                self._out = None
                return False

    def send(self, message: Any) -> bool:
        with self._lock:
            if not self.ensure_open():
                return False
            try:
                self._out.send(message)
                return True
            except Exception as exc:
                self._error = str(exc)
                try:
                    self._out.close()
                except Exception:
                    pass
                self._out = None
                return False

    def configure(self, port: str, virtual: str | bool) -> None:
        with self._lock:
            new_port = port or "TMate 1.0"
            changed = self.port != new_port
            previous_virtual = self._virtual_flag()
            self.port = new_port
            self.virtual = virtual
            changed = changed or previous_virtual != self._virtual_flag()
            if not changed:
                return
            if self._out is not None:
                try:
                    self._out.close()
                except Exception:
                    pass
            self._out = None
            self._error = None
            self._ports_cache = None
            self._ports_at = 0.0
            self._last_attempt = 0.0
            self._closed = False

    def reopen(self) -> None:
        with self._lock:
            if self._out is not None:
                try:
                    self._out.close()
                except Exception:
                    pass
            self._out = None
            self._error = None
            self._last_attempt = 0.0
            self._closed = False

    def close(self) -> None:
        with self._lock:
            self._closed = True
            if self._out is not None:
                try:
                    self._out.close()
                except Exception:
                    pass
                self._out = None

    def status(self, refresh_ports: bool = False) -> dict[str, Any]:
        with self._lock:
            names = self.ports(refresh=refresh_ports)
            return {
                "connected": self._out is not None,
                "port": self.port,
                "virtual": self._virtual_flag(),
                "virtual_supported": self.virtual_supported(),
                "error": self._error,
                "ports": names,
                "ports_error": self._ports_error,
                "resolved": resolve_port_name(self.port, names),
            }

    def message(self, kind: str, **kwargs: Any) -> Any:
        return self._mido.Message(kind, **kwargs)


class NullMidiOut:
    def __init__(self, port: str = "dry-run", virtual: bool = False):
        self.port = port
        self.virtual = virtual
        self._mido = _mido()
        self.sent: list[Any] = []
        self._lock = threading.RLock()

    @staticmethod
    def virtual_supported() -> bool:
        return False

    def ports(self, refresh: bool = False) -> list[str]:
        return []

    def ensure_open(self, force: bool = False) -> bool:
        return True

    def send(self, message: Any) -> bool:
        with self._lock:
            self.sent.append(message)
            return True

    def configure(self, port: str, virtual: str | bool) -> None:
        with self._lock:
            self.port = port or "TMate 1.0"
            self.virtual = virtual

    def reopen(self) -> None:
        return

    def close(self) -> None:
        return

    def status(self, refresh_ports: bool = False) -> dict[str, Any]:
        with self._lock:
            return {
                "connected": False,
                "port": self.port,
                "virtual": False,
                "virtual_supported": False,
                "error": "dry run: no MIDI output is opened",
                "ports": [],
                "ports_error": None,
                "resolved": None,
            }

    def message(self, kind: str, **kwargs: Any) -> Any:
        return self._mido.Message(kind, **kwargs)
