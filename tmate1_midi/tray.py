"""Optional system tray front-end."""

from __future__ import annotations

import logging
import threading
import webbrowser
from typing import Any

log = logging.getLogger(__name__)


class TrayUnavailable(RuntimeError):
    pass


def _status_color(state: Any) -> tuple[int, int, int, int]:
    snapshot = state.snapshot()
    device_ok = bool(snapshot["device"]["connected"])
    midi_ok = bool(snapshot["midi"]["connected"])
    if device_ok and midi_ok:
        return (63, 185, 80, 255)
    if device_ok or midi_ok:
        return (210, 153, 34, 255)
    return (248, 81, 73, 255)


def _make_icon(state: Any):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (64, 64), (13, 17, 23, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (2, 2, 62, 62),
        radius=14,
        fill=(22, 27, 34, 255),
        outline=(45, 55, 72, 255),
        width=2,
    )
    draw.ellipse((14, 10, 50, 46), outline=(230, 150, 46, 255), width=4)
    draw.line((32, 28, 32, 15), fill=(255, 184, 92, 255), width=4)
    draw.ellipse(
        (27, 23, 37, 33),
        fill=(28, 35, 48, 255),
        outline=(59, 72, 92, 255),
    )
    color = _status_color(state)
    for x in (20, 32, 44):
        draw.ellipse((x - 3, 52, x + 3, 58), fill=color)
    return image


def _title(state: Any) -> str:
    snapshot = state.snapshot()
    device = snapshot["device"]
    midi = snapshot["midi"]
    device_text = "TMate ok" if device["connected"] else "TMate offline"
    if midi["connected"]:
        midi_text = "MIDI ok: " + midi["port"]
    else:
        midi_text = "MIDI: " + (midi.get("error") or "offline")
    return f"TMate MIDI — {device_text} · {midi_text}"


def run_tray(state: Any, url: str | None) -> None:
    try:
        import pystray
    except Exception as exc:
        raise TrayUnavailable(
            "pystray is not installed; install it with "
            "python -m pip install pystray Pillow, or use --no-tray"
        ) from exc

    def open_configurator(icon: Any, item: Any) -> None:
        if url:
            webbrowser.open(url)

    def reload_config(icon: Any, item: Any) -> None:
        try:
            state.reload_config()
        except Exception as exc:
            log.warning("reload from tray failed: %s", exc)

    def clear_activity(icon: Any, item: Any) -> None:
        state.clear_activity()

    def quit_app(icon: Any, item: Any) -> None:
        state.request_stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(
            "Open configurator",
            open_configurator,
            default=True,
            enabled=url is not None,
        ),
        pystray.MenuItem("Reload config", reload_config),
        pystray.MenuItem("Clear MIDI activity", clear_activity),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("tmate1-midi", _make_icon(state), _title(state), menu)
    stop_updates = threading.Event()

    def update_loop() -> None:
        while not stop_updates.is_set() and not state.stop_requested:
            try:
                icon.icon = _make_icon(state)
                icon.title = _title(state)
            except Exception:
                pass
            stop_updates.wait(2.0)
        try:
            icon.stop()
        except Exception:
            pass

    threading.Thread(
        target=update_loop, name="tmate1-midi-tray", daemon=True
    ).start()
    try:
        icon.run()
    finally:
        stop_updates.set()
