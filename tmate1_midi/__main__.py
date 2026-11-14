"""Command line entry point for tmate1-midi."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .app import run_app
from .config import (
    ConfigError,
    default_config_path,
    load_config,
    validate_config,
)
from .midi import MidiOut, MidiUnavailable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tmate1-midi",
        description="Use the TMate 1.0 wheel and four keys as a MIDI controller.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="config file (default: user config directory)",
    )
    parser.add_argument(
        "--port",
        default=None,
        help="MIDI output port name (overrides the config)",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="list MIDI output ports and exit",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=None,
        help="port for the local configurator (default: 8067)",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="do not start the local configurator",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="run in the console instead of a system tray icon",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_browser",
        help="open the configurator in the default browser at start",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="read the device and log MIDI messages without opening a port",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="stop after this many seconds (testing)",
    )
    parser.add_argument(
        "--hz",
        type=float,
        default=None,
        help="device poll rate in Hz (20-500, default 100)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="log every MIDI message",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"tmate1-midi {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.duration is not None and args.duration <= 0:
        parser.error("--duration must be positive")
    if args.hz is not None and args.hz <= 0:
        parser.error("--hz must be positive")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    if args.list_ports:
        try:
            midi = MidiOut("", "auto")
            status = midi.status(refresh_ports=True)
        except MidiUnavailable as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if status["ports_error"]:
            print(f"error: {status['ports_error']}", file=sys.stderr)
            return 1
        if not status["ports"]:
            print("no MIDI output ports found")
            return 0
        for name in status["ports"]:
            print(name)
        return 0

    config_path = args.config or default_config_path()
    try:
        config = load_config(config_path, create=True)
        if args.port is not None:
            config["midi"]["port"] = args.port
        if args.web_port is not None:
            config["web"]["port"] = args.web_port
        if args.hz is not None:
            config["device"]["hz"] = int(args.hz)
        config = validate_config(config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    open_browser = args.open_browser or bool(config["web"].get("open"))
    try:
        run_app(
            config,
            config_path,
            dry_run=args.dry_run,
            enable_web=not args.no_web,
            enable_tray=not args.no_tray,
            open_browser=open_browser,
            duration=args.duration,
        )
    except MidiUnavailable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
