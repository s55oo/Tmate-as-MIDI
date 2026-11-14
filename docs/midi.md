# TMate 1.0 MIDI controller

`tmate1_midi` turns the TMate into a small MIDI controller:

- the wheel sends a **relative MIDI CC** (one message per detected step);
- the four keys send **notes or CCs**, momentary or toggle;
- a local web page edits and tests every mapping, and saves as you type;
- a tray icon starts/stops the app on a desktop;
- a console mode runs on headless systems.

It uses the safe EP0 control transfers described in [protocol.md](protocol.md) and
never sets the USB configuration or reads the broken `0x81` endpoint.

## Install

Linux (Raspberry Pi OS / Debian):

```sh
sudo apt install python3-usb python3-mido python3-rtmidi
```

Windows: install Python 3, then the TMate WinUSB driver with Zadig as described
in the main [README](../README.md#windows), and install the Python packages:

```powershell
py -m pip install -r requirements-midi.txt
```

If `python-rtmidi` fails to build on Linux, install the headers and retry:

```sh
sudo apt install libasound2-dev libusb-1.0-0-dev
python3 -m pip install -r requirements-midi.txt
```

The tray is optional. `pystray` and `Pillow` are needed for it; on a headless
system always use `--no-tray`.

## Run

From the checkout:

```sh
python3 -m tmate1_midi
# or
bin/tmate1-midi
```

On Windows use `bin\tmate1-midi.cmd` or `py -3 -m tmate1_midi`.

The configurator opens at <http://127.0.0.1:8067/>. The app keeps running when
the browser is closed. Use `--open` to launch the browser automatically.

Common options:

```sh
python3 -m tmate1_midi --no-tray          # console mode, Ctrl+C to stop
python3 -m tmate1_midi --list-ports       # list MIDI outputs and exit
python3 -m tmate1_midi --dry-run -v       # log MIDI messages, send nothing
python3 -m tmate1_midi --duration 10      # stop after 10 seconds
python3 -m tmate1_midi --port "LoopMIDI"  # override the output port
python3 -m tmate1_midi --web-port 9000    # different configurator port
```

Do not run the monitor (`tmate1-monitor`) and the MIDI app at the same time:
the encoder queue is consumed per read, so they would steal steps from each
other.

## MIDI output

### Linux

The app creates a virtual ALSA MIDI port named **TMate 1.0**. It appears only
while the app is running. Connect it to your synth or DAW with `aconnect`, or
select it directly inside the application.

```sh
aconnect -l                 # find client IDs and ports
aconnect 128:0 129:0        # example: connect TMate to another client
```

To watch what is being sent:

```sh
aseqdump -l                 # list ports; note the client of "TMate 1.0"
aseqdump -p 128:0           # replace 128 with that client number
```

If no other MIDI client exists, `Midi Through` may be the only destination;
that is normal. Start your synth/DAW first, then reconnect.

### Windows

Use [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html):

1. Start loopMIDI.
2. Create a port named **TMate 1.0** (or use another name and set it in the
   configurator or with `--port`).
3. Start `tmate1-midi`. It opens the loopMIDI port as its MIDI output.
4. In your DAW, select the same loopMIDI port as a MIDI input.

The TMate itself must be bound to WinUSB with Zadig (see the main README). The
MIDI port and the USB driver are independent: loopMIDI carries MIDI, WinUSB
lets Python read the knob.

## Configurator

<http://127.0.0.1:8067/>

- **Wheel**: channel, CC, relative format, step, invert, acceleration.
- **Keys**: channel, note/CC number, velocity/value, momentary/toggle.
- **Test** buttons send a sample message immediately.
- **Activity** shows the last messages with their raw hex.
- **Port** lists real MIDI outputs and lets you enable/disable the virtual port.
- The page saves automatically after each change. There is no Save button.
- **Reset** restores defaults; **Reload** reads the file from disk.

The configurator is bound to `127.0.0.1` by default. Do not expose it to a
network without adding authentication.

## Config file

The app uses the first available path:

1. `$TMATE1_MIDI_CONFIG`
2. `./tmate1-midi.json` if it already exists
3. Linux: `~/.config/tmate1-midi/tmate1-midi.json`
4. Windows: `%APPDATA%\tmate1-midi\tmate1-midi.json`

A missing file is created with defaults. The full default:

```json
{
  "midi": { "port": "TMate 1.0", "virtual": "auto" },
  "wheel": {
    "channel": 1,
    "cc": 1,
    "format": "offset",
    "step": 1,
    "invert": true,
    "acceleration": false,
    "max_delta": 63
  },
  "keys": {
    "key1": { "channel": 1, "type": "note", "number": 60, "velocity": 127, "value": 127, "behavior": "momentary" },
    "key2": { "channel": 1, "type": "note", "number": 61, "velocity": 127, "value": 127, "behavior": "momentary" },
    "key3": { "channel": 1, "type": "note", "number": 62, "velocity": 127, "value": 127, "behavior": "momentary" },
    "key4": { "channel": 1, "type": "note", "number": 63, "velocity": 127, "value": 127, "behavior": "momentary" }
  },
  "web": { "host": "127.0.0.1", "port": 8067, "open": false },
  "device": { "hz": 100 }
}
```

`virtual` is `"auto"` (virtual port on Linux only), `true`, or `false`. On
Windows `"auto"` resolves to `false`; the app connects to the loopMIDI port
instead of creating one.

### Relative CC formats

The TMate reports **clockwise as negative** and counter-clockwise as positive.
The default `"invert": true` flips that so clockwise increases the CC. Set it to
`false` if your DAW expects the raw direction.

| `format`    | Increase      | Decrease      | No change |
| ----------- | ------------- | ------------- | --------- |
| `offset`    | 65 … 127      | 63 … 0        | 64        |
| `twos`      | 1 … 63        | 127 … 65      | 0         |
| `increment` | 127 per step  | 1 per step    | 0         |

- `step` multiplies each hardware step (1-16).
- `acceleration` makes fast turns move farther (×0.5 per extra step).
- `max_delta` caps one MIDI message at 1-63 steps; longer turns are split into
  several messages so a fast spin is not lost.

## Testing

```sh
python3 -m py_compile tmate1_midi/*.py
python3 -m unittest discover -s tests -v
python3 -m tmate1_midi --dry-run --duration 5 --no-web --no-tray --verbose
```

`--dry-run` still reads the device and logs the exact MIDI bytes, but does not
open an output port. The web API can also send a test message:

```sh
curl -s http://127.0.0.1:8067/api/state
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"control":"key1"}' http://127.0.0.1:8067/api/test
```

## Troubleshooting

**`TMate 1.0 not found`** - check `lsusb` for `1721:0607`, install
`udev/99-tmate1.rules`, and replug the device. On Windows, confirm Zadig bound
it to WinUSB.

**MIDI port does not open** - on Linux install `python3-rtmidi`; on Windows start
loopMIDI and make sure the port name matches `midi.port`. The status panel shows
the exact error.

**Nothing in the DAW** - on Linux the virtual port must be connected with
`aconnect` or selected in the DAW; on Windows the DAW input must be the loopMIDI
port. Check the activity table: if messages appear there, the app is sending.

**Wheel turns the wrong way** - toggle `invert` in the configurator.

**Tray icon does not appear** - install `pystray` and `Pillow`, and run inside a
desktop session. Use `--no-tray` on headless systems.

**Two key presses produce one note** - keys are sampled by polling; very short
taps can be missed at low `device.hz`. Keep the default 100 Hz or raise it.

**Device stops responding / USB errors** - unplug and replug the TMate. Do not
run tools that call `set_configuration()` or read endpoint `0x81`.
