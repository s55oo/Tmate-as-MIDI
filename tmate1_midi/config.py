"""Configuration loading, validation and atomic saving.

The file is JSON so the same schema can be edited by hand or by the local web
configurator.  Unknown keys are preserved when a config is loaded, which keeps
older/newer versions from destroying each other's settings.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

APP_DIR_NAME = "tmate1-midi"
CONFIG_NAME = "tmate1-midi.json"

KEY_NAMES = ("key1", "key2", "key3", "key4")
RELATIVE_FORMATS = ("offset", "twos", "increment")
KEY_TYPES = ("note", "cc")
BEHAVIORS = ("momentary", "toggle")

DEFAULT_CONFIG: dict[str, Any] = {
    "midi": {
        "port": "TMate 1.0",
        "virtual": "auto",
    },
    "wheel": {
        "channel": 1,
        "cc": 1,
        "format": "offset",
        "step": 1,
        "invert": True,
        "acceleration": False,
        "max_delta": 63,
    },
    "keys": {
        "key1": {
            "channel": 1,
            "type": "note",
            "number": 60,
            "velocity": 127,
            "value": 127,
            "behavior": "momentary",
        },
        "key2": {
            "channel": 1,
            "type": "note",
            "number": 61,
            "velocity": 127,
            "value": 127,
            "behavior": "momentary",
        },
        "key3": {
            "channel": 1,
            "type": "note",
            "number": 62,
            "velocity": 127,
            "value": 127,
            "behavior": "momentary",
        },
        "key4": {
            "channel": 1,
            "type": "note",
            "number": 63,
            "velocity": 127,
            "value": 127,
            "behavior": "momentary",
        },
    },
    "web": {
        "host": "127.0.0.1",
        "port": 8067,
        "open": False,
    },
    "device": {
        "hz": 100,
    },
}


class ConfigError(ValueError):
    pass


def default_config() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_CONFIG)


def default_config_path() -> Path:
    env = os.environ.get("TMATE1_MIDI_CONFIG")
    if env:
        return Path(env).expanduser()
    local = Path.cwd() / CONFIG_NAME
    if local.exists():
        return local
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_DIR_NAME / CONFIG_NAME
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_DIR_NAME / CONFIG_NAME


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _as_int(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if not low <= number <= high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return number


def _as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off"):
            return False
    raise ConfigError(f"{name} must be true or false")


def _as_text(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string")
    return value.strip()


def _as_choice(value: Any, name: str, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be one of: {', '.join(choices)}")
    text = value.strip().lower()
    if text not in choices:
        raise ConfigError(f"{name} must be one of: {', '.join(choices)}")
    return text


def validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ConfigError("config must be a JSON object")

    merged = _merge(DEFAULT_CONFIG, config)

    midi = merged["midi"]
    if not isinstance(midi, dict):
        raise ConfigError("midi must be an object")
    midi["port"] = _as_text(midi.get("port"), "midi.port")
    if not midi["port"]:
        midi["port"] = "TMate 1.0"
    virtual = midi.get("virtual", "auto")
    if isinstance(virtual, str) and virtual.strip().lower() == "auto":
        midi["virtual"] = "auto"
    else:
        midi["virtual"] = _as_bool(virtual, "midi.virtual")

    wheel = merged["wheel"]
    if not isinstance(wheel, dict):
        raise ConfigError("wheel must be an object")
    wheel["channel"] = _as_int(wheel.get("channel"), "wheel.channel", 1, 16)
    wheel["cc"] = _as_int(wheel.get("cc"), "wheel.cc", 0, 127)
    wheel["format"] = _as_choice(
        wheel.get("format"), "wheel.format", RELATIVE_FORMATS
    )
    wheel["step"] = _as_int(wheel.get("step"), "wheel.step", 1, 16)
    wheel["invert"] = _as_bool(wheel.get("invert"), "wheel.invert")
    wheel["acceleration"] = _as_bool(
        wheel.get("acceleration"), "wheel.acceleration"
    )
    wheel["max_delta"] = _as_int(
        wheel.get("max_delta"), "wheel.max_delta", 1, 63
    )

    keys = merged["keys"]
    if not isinstance(keys, dict):
        raise ConfigError("keys must be an object")
    for name in KEY_NAMES:
        key = keys.get(name)
        if not isinstance(key, dict):
            raise ConfigError(f"keys.{name} must be an object")
        key["channel"] = _as_int(key.get("channel"), f"keys.{name}.channel", 1, 16)
        key["type"] = _as_choice(key.get("type"), f"keys.{name}.type", KEY_TYPES)
        key["number"] = _as_int(key.get("number"), f"keys.{name}.number", 0, 127)
        key["velocity"] = _as_int(
            key.get("velocity"), f"keys.{name}.velocity", 0, 127
        )
        key["value"] = _as_int(key.get("value"), f"keys.{name}.value", 0, 127)
        key["behavior"] = _as_choice(
            key.get("behavior"), f"keys.{name}.behavior", BEHAVIORS
        )

    web = merged["web"]
    if not isinstance(web, dict):
        raise ConfigError("web must be an object")
    web["host"] = _as_text(web.get("host"), "web.host")
    if not web["host"]:
        web["host"] = "127.0.0.1"
    web["port"] = _as_int(web.get("port"), "web.port", 1, 65535)
    web["open"] = _as_bool(web.get("open"), "web.open")

    device = merged["device"]
    if not isinstance(device, dict):
        raise ConfigError("device must be an object")
    device["hz"] = _as_int(device.get("hz"), "device.hz", 20, 500)

    return merged


def load_config(path: Path | str, create: bool = True) -> dict[str, Any]:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        config = default_config()
        if create:
            save_config(file_path, config)
        return config

    try:
        with file_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"{file_path}: invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ConfigError(f"{file_path}: {exc}") from exc

    return validate_config(raw)


def save_config(path: Path | str, config: Any) -> Path:
    config = validate_config(config)
    file_path = Path(path).expanduser()
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = file_path.with_name(file_path.name + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
            handle.write("\n")
        os.replace(temp_path, file_path)
    except OSError as exc:
        raise ConfigError(f"{file_path}: {exc}") from exc
    return file_path
