# TMate 1.0 USB tuning knob

Userspace reader and MIDI controller for the WoodBoxRadio/ELAD **TMate 1.0**
(USB `1721:0607`): one tuning wheel, four function keys, no kernel driver
needed.

## Confirmed on this unit

| Input | Result |
| --- | --- |
| Wheel clockwise (right) | negative step count |
| Wheel counterclockwise (left) | positive step count |
| Leftmost key | `key1` |
| 2nd key from left | `key2` |
| 3rd key from left | `key3` |
| Rightmost key | `key4` |

The wheel counter is the number of steps since the previous read, so polling
faster gives finer resolution.  At 100 Hz the monitor aggregates wheel
movement for display but keeps an exact running total.

## Install

```sh
sudo apt install python3-usb
```

For the MIDI controller, also install `python3-mido python3-rtmidi` (see the
[MIDI controller](#midi-controller) section below).

Optional, for non-root access and a stable `/dev/tmate1` symlink:

```sh
sudo cp udev/99-tmate1.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

(Replace `plugdev` in the rule if your distribution uses another group.)

## Run

```sh
# 30-second live monitor
bin/tmate1-monitor --duration 30

# Start on first key press (useful for one-key-at-a-time tests)
bin/tmate1-monitor --duration 10 --wait-key

# Start on first wheel movement
bin/tmate1-monitor --duration 10 --wait-motion

# Diagnostic: every wheel delta and every raw 8-byte frame
bin/tmate1-monitor --duration 10 --verbose --raw
```

Useful options:

| Option | Meaning |
| --- | --- |
| `--hz N` | poll rate, default 100 |
| `--interval S` | wheel display aggregation, default 0.2 s |
| `--wait-key` | wait for a key press before starting |
| `--wait-motion` | wait for wheel movement before starting |
| `--no-led` | skip the `SetLed(1)` / `SetLed(0)` handshake |
| `--raw` | print the raw frame each read |

Run it directly from the checkout; no installation is required.  The same
entry point is available as `python3 -m tmate1.monitor`.

## MIDI controller

The checkout also includes `tmate1_midi`, a cross-platform MIDI controller:
wheel to relative CC, four keys to configurable notes or CCs, a local web
configurator, and an optional tray icon. It uses the same safe USB access as
the monitor.

```sh
python3 -m tmate1_midi        # tray + configurator at http://127.0.0.1:8067/
bin/tmate1-midi --no-tray     # console mode
bin/tmate1-midi --dry-run -v  # log MIDI bytes without opening a port
```

Linux creates a virtual ALSA port named `TMate 1.0`; Windows connects to a
loopMIDI port with the same name. Install `requirements-midi.txt` (or the
`python3-usb python3-mido python3-rtmidi` packages on Debian). See
[docs/midi.md](docs/midi.md) for MIDI routing, relative-CC formats, the config
file, and troubleshooting.

## Windows

The original 2010 WinUSB driver is not usable on current Windows: its INF has
no signed catalog (`CatalogFile` is commented out, `DriverVer=02/07/2008`) and
it depends on WDK 7 co-installers. Windows 10/11 blocks it under driver
signature enforcement, and the original `Tmate.exe` is 32-bit.

**Full Windows manual:** [`docs/windows.md`](docs/windows.md), or the printable
`TMate-1.0-Windows-Manual.pdf` in the package root.

After installing Python, Zadig/WinUSB and loopMIDI, double-click
`setup-windows.cmd`: it installs the Python packages and checks the driver,
device and MIDI port. `setup-windows.cmd -Autostart` adds a hidden-console
logon shortcut.

Recommended: bind the device to WinUSB with Zadig and run this Python tool. No
custom or self-signed driver is needed; WinUSB is Microsoft-signed.

1. Remove any old Tmate driver: Device Manager -> Tmate -> Uninstall device,
   tick "Attempt to remove the driver", then replug the cable.
2. Get Zadig from <https://zadig.akeo.ie/> and run it as administrator.
3. `Options -> List All Devices`, select `Tmate 1.0 USB` (USB ID `1721 0607`).
4. Choose `WinUSB` and click `Replace Driver`.
5. Install 64-bit Python 3.11+ from python.org (tick "Add python.exe to PATH").
6. In PowerShell:

   ```powershell
   py -m pip install --upgrade pyusb libusb-package
   ```

7. Copy this folder to Windows and run from it:

   ```powershell
   py -m tmate1.monitor --duration 30
   py -m tmate1.monitor --wait-motion --duration 10
   ```

   `libusb-package` supplies `libusb-1.0.dll`; no manual DLL copy is needed.
   The POSIX `bin/tmate1-monitor` launcher is not used on Windows; use
   `py -m tmate1.monitor` or `bin\tmate1-monitor.cmd` instead.

   For the MIDI controller, install the MIDI requirements, create a loopMIDI
   port named `TMate 1.0`, and run `py -m tmate1_midi`. See
   [docs/windows.md](docs/windows.md) for the complete walkthrough.

8. If the device is not found, list what libusb can see:

   ```powershell
   py -c "import libusb_package; [print(d) for d in libusb_package.find(find_all=True)]"
   ```

   Device Manager should show the Tmate under "Universal Serial Bus devices"
   without a warning. Close `Tmate.exe` if it is running; only one process can
   use the device.

### Original `Tmate.exe` (not supported on Windows 10/11)

The official app finds the device through the INF's DeviceInterfaceGUID
`{257BFA68-AAB1-45A1-8747-DE86CFDF9099}`. Zadig does not set that GUID, so
`Tmate.exe` will not see a Zadig-installed device. It is also 32-bit and uses
an unsigned 2008 driver.

Do not disable driver signature enforcement or install the old INF on Windows
10/11. The original app is only an option in a Windows 7 VM, and it is not
needed for this package. The original zips (`TmateV1_2.zip`,
`Tmate_WINUSBdriver.zip`) are vendor software and are not in this Git
repository; a locally built `TMate-1.0-Windows.zip` includes them in `windows/`
for reference when they are present in the checkout.
You do not need a Windows 7 VM for the recommended WinUSB setup.

### Alternative: WSL2

If you prefer the Linux tool unchanged, install `usbipd-win`, attach the device
to WSL2, then run the tool inside WSL. The device is detached from Windows while
it is attached to WSL.

## Building the Windows package

On Linux, from the checkout:

```sh
tools/build-windows-zip.sh
```

This runs the unit tests, rebuilds `TMate-1.0-Windows-Manual.pdf` from
`docs/windows.md` (needs `python3-reportlab`; otherwise the existing PDF is
shipped), converts the Windows scripts to CRLF, and writes
`dist/TMate-1.0-Windows.zip` plus a `.sha256` file. To rebuild only the manual:
`python3 tools/build_windows_manual.py`.

## Safety note

The TMate 1.0 has malformed USB descriptors (an 8-byte endpoint with
`bmAttributes=0`).  **Do not call `set_configuration()` and do not read
endpoint `0x81`.**  Both have crashed the Raspberry Pi xHCI controller in
testing.  Only endpoint-0 vendor control transfers are used.

If the controller dies (`xHCI host not responding`, `HC died; cleaning up`),
recover it with:

```sh
echo xhci-hcd.1 | sudo tee /sys/bus/platform/drivers/xhci-hcd/unbind
sleep 2
echo xhci-hcd.1 | sudo tee /sys/bus/platform/drivers/xhci-hcd/bind
```

Do not touch `xhci-hcd.0` if that controller has other storage attached.

## Protocol

See [`docs/protocol.md`](docs/protocol.md) for the recovered control requests
and frame layout.
