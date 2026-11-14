"""Live monitor for the TMate 1.0 wheel and its four buttons.

The device reports the number of encoder steps since the previous read, so we
add each delta to a running total.  To keep the console readable the wheel is
printed once per aggregation interval; use --verbose to see every delta.
Buttons are reported as key1..key4, where key1 clears the lowest bit of the
idle key byte (0x3F).

Examples:

    python3 -m tmate1.monitor
    python3 -m tmate1.monitor --duration 60 --hz 200 --interval 0.1
    python3 -m tmate1.monitor --verbose --raw
"""

from __future__ import annotations

import argparse
import sys
import time

import usb.core

from .device import Tmate1, TmateNotFound


def _key_name(bit):
    return f"key{bit + 1}"


def run(duration, hz, interval, raw, verbose, use_led, wait_key, wait_motion):
    with Tmate1() as dev:
        if use_led:
            dev.set_led(1)

        # The counter keeps running while nobody reads, so the first frame can
        # contain a large backlog.  Discard it and start from the current state.
        try:
            _, keys, first = dev.read()
        except usb.core.USBError:
            _, keys, first = 0, 0, b""

        period = 1.0 / hz
        total_steps = 0
        pending_steps = 0
        frames = 0
        errors = 0
        presses = [0, 0, 0, 0]

        print(
            f"TMate 1.0 monitor: {duration:g}s at {hz:g} Hz — "
            "turn the wheel and press the four keys (Ctrl-C to stop)",
            flush=True,
        )

        start_keys = 0
        start_steps = 0
        if wait_key or wait_motion:
            if wait_key and wait_motion:
                what = "a key press or wheel movement"
            elif wait_motion:
                what = "wheel movement"
            else:
                what = "a key press"
            print(f"Waiting for {what} to start...", flush=True)
            previous = keys
            while True:
                try:
                    steps, new_keys, _ = dev.read()
                except usb.core.USBError:
                    time.sleep(period)
                    continue
                key_edge = bool(new_keys) and not previous
                if (wait_key and key_edge) or (wait_motion and steps):
                    if key_edge:
                        # Keep this state so the matching UP is reported later.
                        start_keys = new_keys
                    if wait_motion and steps:
                        start_steps = steps
                    keys = new_keys
                    break
                previous = new_keys
                time.sleep(period)

        start = time.monotonic()
        next_at = start
        next_flush = interval

        if raw and first:
            print(f"[{0.0:8.3f}] raw {first.hex()}")

        if start_steps:
            total_steps += start_steps
            pending_steps += start_steps
            if verbose:
                print(
                    f"[{0.0:8.3f}] wheel {start_steps:+d} "
                    f"(total {total_steps:+d})"
                )

        if start_keys:
            for i in range(4):
                if start_keys & (1 << i):
                    presses[i] += 1
                    print(f"[{0.0:8.3f}] {_key_name(i)} DOWN")

        try:
            while True:
                now = time.monotonic()
                if now - start >= duration:
                    break
                if now < next_at:
                    time.sleep(next_at - now)
                next_at += period
                if now - next_at > 0.5:
                    next_at = now + period

                try:
                    steps, new_keys, frame = dev.read()
                    frames += 1
                except usb.core.USBError as exc:
                    errors += 1
                    print(f"[{time.monotonic() - start:8.3f}] USB error: {exc}")
                    if errors >= 10:
                        print("too many USB errors, stopping", file=sys.stderr)
                        break
                    continue
                errors = 0

                stamp = time.monotonic() - start

                if raw:
                    print(f"[{stamp:8.3f}] raw {frame.hex()}")

                if steps:
                    total_steps += steps
                    pending_steps += steps
                    if verbose:
                        print(
                            f"[{stamp:8.3f}] wheel {steps:+d} "
                            f"(total {total_steps:+d})"
                        )

                changed = new_keys ^ keys
                for i in range(4):
                    if changed & (1 << i):
                        if new_keys & (1 << i):
                            presses[i] += 1
                            print(f"[{stamp:8.3f}] {_key_name(i)} DOWN")
                        else:
                            print(f"[{stamp:8.3f}] {_key_name(i)} UP")
                keys = new_keys

                if not verbose and stamp >= next_flush:
                    if pending_steps:
                        print(
                            f"[{stamp:8.3f}] wheel {pending_steps:+d} "
                            f"(total {total_steps:+d})"
                        )
                        pending_steps = 0
                    next_flush = stamp + interval
        except KeyboardInterrupt:
            print("\ninterrupted")

        if not verbose and pending_steps:
            print(
                f"[{time.monotonic() - start:8.3f}] wheel {pending_steps:+d} "
                f"(total {total_steps:+d})"
            )

        if use_led:
            dev.set_led(0)

        elapsed = time.monotonic() - start
        print(
            f"\nsummary: {elapsed:.2f}s, {frames} reads, "
            f"{total_steps:+d} encoder steps, "
            f"presses key1={presses[0]} key2={presses[1]} "
            f"key3={presses[2]} key4={presses[3]}"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read the TMate 1.0 wheel and four buttons"
    )
    parser.add_argument(
        "--duration", type=float, default=30.0, help="seconds to run (default 30)"
    )
    parser.add_argument(
        "--hz", type=float, default=100.0, help="poll rate in Hz (default 100)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.2,
        help="wheel display interval in seconds (default 0.2)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print every non-zero wheel delta instead of aggregating",
    )
    parser.add_argument(
        "--raw", action="store_true", help="print every raw 8-byte frame"
    )
    parser.add_argument(
        "--wait-key",
        action="store_true",
        help="wait for a key press before starting the capture",
    )
    parser.add_argument(
        "--wait-motion",
        action="store_true",
        help="wait for wheel movement before starting the capture",
    )
    parser.add_argument(
        "--no-led",
        action="store_false",
        dest="led",
        help="do not run the SetLed(1)/SetLed(0) handshake",
    )
    args = parser.parse_args(argv)

    if args.hz <= 0 or args.interval <= 0 or args.duration <= 0:
        parser.error("--hz, --interval and --duration must be positive")

    try:
        run(
            args.duration,
            args.hz,
            args.interval,
            args.raw,
            args.verbose,
            args.led,
            args.wait_key,
            args.wait_motion,
        )
    except TmateNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
