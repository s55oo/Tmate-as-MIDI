"""Pure mappings between TMate samples and MIDI values."""

from __future__ import annotations

import math
from typing import Any

ENCODER_CENTER = 0x80

KEY_BITS = {"key1": 0, "key2": 1, "key3": 2, "key4": 3}


def signed_delta(byte: int) -> int:
    return int(byte) - ENCODER_CENTER


def keys_from_byte(byte: int) -> dict[str, bool]:
    value = int(byte)
    return {name: not bool(value & (1 << bit)) for name, bit in KEY_BITS.items()}


def keys_from_mask(mask: int) -> dict[str, bool]:
    value = int(mask)
    return {name: bool(value & (1 << bit)) for name, bit in KEY_BITS.items()}


def encode_relative(delta: int, fmt: str) -> int:
    if fmt == "offset":
        return max(0, min(127, 64 + int(delta)))
    if fmt == "twos":
        return int(delta) & 0x7F
    if fmt == "increment":
        if delta > 0:
            return 127
        if delta < 0:
            return 1
        return 0
    raise ValueError(f"unknown relative format: {fmt}")


def _round_half_away(value: float) -> int:
    sign = 1 if value >= 0 else -1
    return sign * math.floor(abs(value) + 0.5)


def effective_delta(delta: int, wheel: dict[str, Any]) -> int:
    if not delta:
        return 0
    if wheel.get("invert"):
        delta = -delta
    step = int(wheel.get("step", 1))
    if wheel.get("acceleration"):
        factor = min(4.0, 1.0 + max(0, abs(delta) - 1) * 0.5)
    else:
        factor = 1.0
    return _round_half_away(delta * step * factor)


def wheel_values(delta: int, wheel: dict[str, Any]) -> list[int]:
    delta = effective_delta(delta, wheel)
    if not delta:
        return []

    fmt = wheel.get("format", "offset")
    if fmt == "increment":
        return [127 if delta > 0 else 1] * min(abs(delta), 64)

    max_delta = max(1, min(63, int(wheel.get("max_delta", 63))))
    values: list[int] = []
    remaining = delta
    while remaining:
        chunk = max(-max_delta, min(max_delta, remaining))
        values.append(encode_relative(chunk, fmt))
        remaining -= chunk
    return values


def midi_hex(status: int, data1: int, data2: int) -> str:
    return f"{status:02X} {data1:02X} {data2:02X}"
