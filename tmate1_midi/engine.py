"""TMate polling and MIDI event generation."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

import usb.core

from tmate1.device import Tmate1, TmateNotFound

from .config import KEY_NAMES
from .mapping import keys_from_mask, wheel_values
from .midi import message_hex, message_text

log = logging.getLogger(__name__)


@dataclass
class Activity:
    ts: float
    source: str
    control: str
    message: str
    hex: str
    sent: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MidiEngine:
    def __init__(self, config: dict[str, Any], midi: Any, activity_limit: int = 100):
        self.config = config
        self.midi = midi
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._device: Tmate1 | None = None
        self._primed = False
        self._keys = {name: False for name in KEY_NAMES}
        self._active: dict[str, tuple[str, int, int, bool]] = {}
        self._toggle = {name: False for name in KEY_NAMES}
        self._activity: deque[Activity] = deque(maxlen=activity_limit)
        self._connected = False
        self._error: str | None = None
        self._last_frame: str | None = None
        self._last_error_log = 0.0

    def _msg_cc(self, channel: int, control: int, value: int) -> Any:
        return self.midi.message(
            "control_change",
            channel=max(0, min(15, int(channel) - 1)),
            control=max(0, min(127, int(control))),
            value=max(0, min(127, int(value))),
        )

    def _msg_note_on(self, channel: int, note: int, velocity: int) -> Any:
        return self.midi.message(
            "note_on",
            channel=max(0, min(15, int(channel) - 1)),
            note=max(0, min(127, int(note))),
            velocity=max(0, min(127, int(velocity))),
        )

    def _msg_note_off(self, channel: int, note: int) -> Any:
        return self.midi.message(
            "note_off",
            channel=max(0, min(15, int(channel) - 1)),
            note=max(0, min(127, int(note))),
            velocity=0,
        )

    def _press(self, name: str, config: dict[str, Any]) -> list[tuple[str, Any]]:
        key = config["keys"][name]
        channel = int(key["channel"])
        number = int(key["number"])
        kind = key["type"]
        behavior = key["behavior"]

        if behavior == "toggle":
            turn_on = not self._toggle.get(name, False)
            self._toggle[name] = turn_on
            if turn_on:
                self._active[name] = (kind, channel, number, True)
                if kind == "note":
                    return [
                        (
                            name,
                            self._msg_note_on(channel, number, key["velocity"]),
                        )
                    ]
                return [(name, self._msg_cc(channel, number, key["value"]))]
            active = self._active.pop(name, None)
            if active is None:
                active = (kind, channel, number, True)
            if active[0] == "note":
                return [(name, self._msg_note_off(active[1], active[2]))]
            return [(name, self._msg_cc(active[1], active[2], 0))]

        self._active[name] = (kind, channel, number, False)
        if kind == "note":
            return [
                (name, self._msg_note_on(channel, number, key["velocity"]))
            ]
        return [(name, self._msg_cc(channel, number, key["value"]))]

    def _release(self, name: str, config: dict[str, Any]) -> list[tuple[str, Any]]:
        key = config["keys"][name]
        active = self._active.pop(name, None)
        if active is not None:
            kind, channel, number, latched = active
            if latched:
                return []
            if kind == "note":
                return [(name, self._msg_note_off(channel, number))]
            return [(name, self._msg_cc(channel, number, 0))]

        if key["behavior"] == "toggle":
            return []
        kind = key["type"]
        channel = int(key["channel"])
        number = int(key["number"])
        if kind == "note":
            return [(name, self._msg_note_off(channel, number))]
        return [(name, self._msg_cc(channel, number, 0))]

    def _wheel(self, steps: int, config: dict[str, Any]) -> list[tuple[str, Any]]:
        wheel = config["wheel"]
        channel = int(wheel["channel"])
        control = int(wheel["cc"])
        return [
            ("wheel", self._msg_cc(channel, control, value))
            for value in wheel_values(steps, wheel)
        ]

    def _send(self, control: str, message: Any) -> None:
        sent = self.midi.send(message)
        entry = Activity(
            ts=time.time(),
            source="wheel" if control == "wheel" else "key",
            control=control,
            message=message_text(message),
            hex=message_hex(message),
            sent=sent,
        )
        with self._lock:
            self._activity.append(entry)
        if sent:
            log.debug("%s %s [%s]", control, entry.message, entry.hex)
        else:
            log.debug(
                "%s send failed: %s",
                control,
                self.midi.status().get("error"),
            )

    def process_sample(self, steps: int, keys: int) -> None:
        with self._lock:
            if not self._primed:
                self._primed = True
                self._keys = keys_from_mask(keys)
                return

            current = keys_from_mask(keys)
            previous = self._keys
            self._keys = current
            config = self.config

            messages: list[tuple[str, Any]] = []
            for name in KEY_NAMES:
                if current[name] == previous[name]:
                    continue
                if current[name]:
                    log.info("%s down", name)
                    messages.extend(self._press(name, config))
                else:
                    log.info("%s up", name)
                    messages.extend(self._release(name, config))

            if steps:
                messages.extend(self._wheel(steps, config))

        for control, message in messages:
            self._send(control, message)

    def _release_all(self) -> None:
        with self._lock:
            active = list(self._active.items())
            self._active.clear()
            self._toggle = {name: False for name in KEY_NAMES}
            self._keys = {name: False for name in KEY_NAMES}

        messages: list[tuple[str, Any]] = []
        for name, (kind, channel, number, _latched) in active:
            if kind == "note":
                messages.append((name, self._msg_note_off(channel, number)))
            else:
                messages.append((name, self._msg_cc(channel, number, 0)))
        for control, message in messages:
            self._send(control, message)

    def test_control(self, control: str, direction: int = -1) -> list[str]:
        if control == "wheel":
            messages = [
                message
                for _control, message in self._wheel(int(direction), self.config)
            ]
        elif control in KEY_NAMES:
            key = self.config["keys"][control]
            channel = int(key["channel"])
            number = int(key["number"])
            if key["type"] == "note":
                messages = [
                    self._msg_note_on(channel, number, key["velocity"]),
                    self._msg_note_off(channel, number),
                ]
            else:
                messages = [
                    self._msg_cc(channel, number, key["value"]),
                    self._msg_cc(channel, number, 0),
                ]
        else:
            raise ValueError(f"unknown control: {control}")

        result = []
        for message in messages:
            self._send(control, message)
            result.append(message_hex(message))
        return result

    def clear_activity(self) -> None:
        with self._lock:
            self._activity.clear()

    def _close_device(self) -> None:
        device = self._device
        self._device = None
        if device is not None:
            try:
                device.close()
            except Exception:
                pass

    def _ensure_device(self) -> Tmate1:
        if self._device is None:
            log.info("opening TMate 1.0")
            self._device = Tmate1()
        return self._device

    def _mark_disconnected(self, error: str) -> None:
        with self._lock:
            was_connected = self._connected
            previous_error = self._error
            self._connected = False
            self._error = error
            self._primed = False
        now = time.monotonic()
        if (was_connected or previous_error != error) and now - self._last_error_log >= 2.0:
            log.warning("TMate: %s", error)
            self._last_error_log = now
        self._release_all()

    def run(self) -> None:
        log.info("MIDI engine started")
        if not self.midi.ensure_open():
            log.warning(
                "MIDI output not open: %s", self.midi.status().get("error")
            )
        else:
            log.info("MIDI output: %s", self.midi.status().get("port"))
        try:
            while not self._stop.is_set():
                started = time.monotonic()
                try:
                    device = self._ensure_device()
                    steps, keys, frame = device.read(timeout=250)
                    if not self._connected:
                        log.info("TMate connected")
                    self._connected = True
                    self._error = None
                    self._last_frame = frame.hex()
                    self.process_sample(steps, keys)
                    self.midi.ensure_open()
                except TmateNotFound as exc:
                    self._mark_disconnected(str(exc))
                    self._close_device()
                    self._stop.wait(1.0)
                except (usb.core.USBError, OSError) as exc:
                    self._mark_disconnected(f"USB error: {exc}")
                    self._close_device()
                    self._stop.wait(0.5)
                except Exception as exc:
                    log.exception("engine error")
                    self._mark_disconnected(str(exc))
                    self._close_device()
                    self._stop.wait(0.5)

                period = 1.0 / max(20, int(self.config["device"]["hz"]))
                elapsed = time.monotonic() - started
                if elapsed < period:
                    self._stop.wait(period - elapsed)
        finally:
            self._release_all()
            self._close_device()
            log.info("MIDI engine stopped")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self.run, name="tmate1-midi-engine", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def set_config(self, config: dict[str, Any]) -> None:
        with self._lock:
            self.config = config

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "connected": self._connected,
                "error": self._error,
                "last_frame": self._last_frame,
                "keys": dict(self._keys),
                "activity": [entry.as_dict() for entry in reversed(self._activity)],
            }
