## Read this first

This package turns the WoodBoxRadio/ELAD **TMate 1.0** USB knob into a MIDI
controller on Windows 10 and Windows 11:

- the tuning wheel sends a **relative MIDI CC**;
- the four keys send **notes or CCs**, momentary or toggle;
- a local web page edits, tests and saves every mapping;
- an optional tray icon keeps it running in the background;
- a small monitor tool verifies the wheel and keys without using MIDI.

The TMate is a vendor-specific USB device (`1721:0607`). Windows has no usable
driver for it, so this package uses **WinUSB**, installed with Zadig. MIDI is
routed through **loopMIDI**, because Windows does not provide a built-in virtual
MIDI port.

**Quick checklist**

1. Windows 10 or 11, 64-bit.
2. Python 3.11 or newer, 64-bit, with `py` on `PATH`.
3. TMate bound to WinUSB with Zadig.
4. loopMIDI installed, with a port named `TMate 1.0`.
5. Python packages from `requirements-midi.txt`.
6. Run `py -m tmate1_midi` from the package folder.
7. Open <http://127.0.0.1:8067/> and click the **Test** buttons.

After steps 2-5, double-click **`setup-windows.cmd`** in the package folder. It
checks every item above, installs the Python packages, does one safe test read
from the TMate and confirms the loopMIDI port. See
[Setup and check script](#setup-and-check-script).

Total time is about 10 to 15 minutes on a clean machine. Do not install the
original 2010 driver or run `Tmate.exe` on Windows 10/11; see
[Step 1](#step-1-remove-old-drivers-and-software).

## What this package does

There are two programs:

| Program | Purpose | What it needs |
| --- | --- | --- |
| `tmate1_midi` | MIDI controller, tray icon, web configurator | WinUSB, loopMIDI, Python MIDI packages |
| `tmate1.monitor` | Diagnostic wheel/key monitor | WinUSB, pyusb |

The controller uses the same safe USB access as the monitor. It sends only
endpoint-0 vendor control requests, as described in
[Safety and correct USB use](#safety-and-correct-usb-use).

The package includes the Python source, launchers, documentation, tests, and
the original Windows software/driver archives for reference. The original
archives are not used for the recommended Windows 10/11 setup.

## What you need

| Item | Notes |
| --- | --- |
| Windows 10 or 11, 64-bit | Windows 8.1 may work but is not tested |
| Python 3.11 or newer, 64-bit | 3.12 is a good choice; install from python.org |
| TMate 1.0 and its USB cable | Device ID `1721:0607` |
| Zadig | <https://zadig.akeo.ie/> |
| loopMIDI | <https://www.tobias-erichsen.de/software/loopmidi.html> |
| A DAW or MIDI monitor | Optional, for using the controller |
| Internet access | For Python packages and loopMIDI |

You need administrator rights only for the WinUSB driver installation. The
controller itself runs as your normal user.

## Quick start

If everything is already installed, this is the short version:

```powershell
cd "C:\path\to\TMate-1.0-Windows"
py -m pip install -r requirements-midi.txt
py -m tmate1_midi
```

Then open <http://127.0.0.1:8067/>. The rest of this manual explains each step,
including driver installation, loopMIDI, DAW routing and troubleshooting.

## Setup and check script

`setup-windows.ps1` (double-click `setup-windows.cmd`) prepares and verifies the
installation. It is safe to run as often as you like:

| Check | What it does |
| --- | --- |
| Windows | Confirms Windows 10/11, 64-bit |
| Python | Finds `py`, requires 3.11+ 64-bit; offers `winget` install if missing |
| Packages | Installs `requirements-midi.txt` if needed, retries with prebuilt wheels |
| Driver | Finds USB `1721:0607` and checks that its driver is WinUSB |
| USB read | One ReadValue control request (endpoint 0 only) |
| loopMIDI | Checks it is installed and running; offers to start it |
| MIDI port | Confirms a port named `TMate 1.0` is visible |
| Autostart | Reports, creates or removes the logon shortcut |

It never installs a driver. If the TMate is not on WinUSB, it prints the Zadig
steps and offers to open the Zadig page.

Options (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1 -CheckOnly   # report only
powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1 -Autostart   # also start at logon
powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1 -RemoveAutostart
powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1 -Yes         # no questions
```

The same options work with `setup-windows.cmd`, for example
`setup-windows.cmd -Autostart`. The script exits with code 0 when every check
passes.

## Step 1 - Remove old drivers and software

If this TMate has never been used on this Windows installation, skip to
[Step 2](#step-2-install-python-3).

1. Close `Tmate.exe` and any program that may be using the device.
2. Open **Device Manager** (right-click Start, then Device Manager).
3. Find the TMate under **Universal Serial Bus devices**, **libusb-win32
   devices**, or as an unknown device with a warning icon.
4. Right-click it and choose **Uninstall device**.
5. Tick **Attempt to remove the driver for this device** if Windows offers it.
6. Unplug the TMate and plug it back in.

Do not install `winusbtmate.inf` from the `windows/` folder on Windows 10/11.
That INF has no signed catalog (`CatalogFile` is commented out), uses
`DriverVer=02/07/2008`, and depends on WDK 7 co-installers. Windows blocks it,
and the original `Tmate.exe` is 32-bit.

The `windows/TmateV1_2.zip` and `windows/Tmate_WINUSBdriver.zip` files are kept
for reference and for a Windows 7 virtual machine. They are not part of the
recommended setup and are not needed for this controller.
They are original vendor software: they are included in the Windows ZIP
package, but not in the public Git repository.

### If you want the original Tmate.exe

The original application finds the device through the INF's DeviceInterfaceGUID
`{257BFA68-AAB1-45A1-8747-DE86CFDF9099}`. Zadig does not set that GUID, so
`Tmate.exe` cannot see a Zadig-installed device.

If you specifically need the original application, use a Windows 7 virtual
machine with the old signed-driver workaround. Do not try to share the same
device between `Tmate.exe` and this package. For normal use, ignore
`Tmate.exe` completely.

## Step 2 - Install Python 3

1. Open <https://www.python.org/downloads/windows/>.
2. Download the **64-bit** installer for Python 3.12 (or 3.11 or newer).
3. Run the installer.
4. On the first page, tick **Add python.exe to PATH**.
5. Choose **Install Now**. The `py` launcher is installed by default.
6. When installation finishes, close and reopen PowerShell.

Verify:

```powershell
py --version
py -m pip --version
```

Both commands must print a version. If `py` is not recognised:

- re-run the Python installer, choose **Modify** or **Repair**, and make sure
  **Add python.exe to PATH** is enabled;
- or reinstall Python and tick the PATH option;
- or use `python` instead of `py` if that command works.

**Recommended:** use the python.org installer, not the Microsoft Store build.
The Store build can work, but it sometimes uses a `python` alias that is
confusing in PowerShell.

All commands in this manual assume PowerShell is open in the folder where you
extracted this package:

```powershell
cd "C:\Users\YOURNAME\Downloads\TMate-1.0-Windows"
```

## Step 3 - Bind the TMate to WinUSB with Zadig

1. Plug the TMate directly into a USB port on the computer. Prefer a rear
   USB 2.0 port; avoid unpowered hubs and docking stations while installing.
2. Download Zadig from <https://zadig.akeo.ie/>.
3. Right-click `zadig.exe` and choose **Run as administrator**.
4. In Zadig, open **Options** and enable **List All Devices**.
5. In the device drop-down, select **Tmate 1.0 USB**. The USB ID must show
   `1721 0607`.
6. Set the target driver to **WinUSB**.
7. Click **Replace Driver** and wait for the process to finish.
8. Close Zadig.

If the device is not listed:

- unplug and replug the TMate;
- try another USB port, especially a rear port directly on the motherboard;
- close `Tmate.exe`, the monitor, and any DAW that may have opened the device;
- check **View -> Show hidden devices** in Device Manager;
- make sure you ran Zadig as administrator and enabled **List All Devices**.

Verify in Device Manager: the TMate should appear under **Universal Serial Bus
devices** as **Tmate 1.0 USB** or **WinUSB device**, without a yellow warning
triangle.

Verify with libusb:

```powershell
py -c "import libusb_package; [print(d) for d in libusb_package.find(find_all=True)]"
```

You should see a device with `idVendor=0x1721` and `idProduct=0x0607`. If this
command reports no backend, install the package first:

```powershell
py -m pip install pyusb libusb-package
```

`libusb-package` supplies `libusb-1.0.dll`; you do not need to copy any DLL by
hand.

### One device, one program

Only one process can reliably use the TMate at a time. Close the original
`Tmate.exe`, the diagnostic monitor, and any other USB tool before starting the
MIDI controller. Do not run `tmate1.monitor` and `tmate1_midi` at the same time:
both consume the encoder counter, so each program would miss some wheel steps.

## Step 4 - Install the Python dependencies

In PowerShell, from the package folder:

```powershell
py -m pip install --upgrade pip
py -m pip install -r requirements-midi.txt
```

This installs:

- `pyusb` and `libusb-package` for the TMate;
- `mido` and `python-rtmidi` for MIDI output;
- `pystray` and `Pillow` for the optional tray icon.

Verify the imports:

```powershell
py -c "import usb.core, mido, rtmidi, pystray, PIL; print('dependencies OK')"
```

If all packages import, the result is `dependencies OK`.

If `pip` tries to compile `python-rtmidi` and fails:

```powershell
py -m pip install --only-binary=:all: -r requirements-midi.txt
```

If that still fails, install **Microsoft C++ Build Tools** (the "Desktop
development with C++" workload), or switch to Python 3.12 where prebuilt wheels
are available. Then retry the normal install.

If only the tray packages fail, you can still use the controller in console
mode:

```powershell
py -m pip install pystray Pillow
py -m tmate1_midi --no-tray
```

The tray is optional; the MIDI controller and web configurator work without it.

## Step 5 - Create the MIDI port with loopMIDI

Windows does not create virtual MIDI ports by itself. The controller sends to a
loopMIDI port; your DAW listens to the same port.

1. Download and install loopMIDI from
   <https://www.tobias-erichsen.de/software/loopmidi.html>.
2. Start loopMIDI.
3. In the **New port** field, type exactly:

   ```
   TMate 1.0
   ```

4. Click the **+** button. The port must appear in the list and stay there.
5. Optional: enable **Start with Windows** in loopMIDI so the port is available
   after a reboot.
6. Leave loopMIDI running while you use the controller.

The app opens the loopMIDI port at startup. If loopMIDI is not running, the MIDI
status chip shows an error and the app retries every few seconds. You can start
loopMIDI later and click **Refresh ports** in the configurator, or simply turn
the wheel to trigger a retry.

If you use a different port name, either:

- set the name in the configurator's port selector, or
- start with `--port "Your Port Name"`, or
- edit `midi.port` in the configuration file.

The name is case-sensitive in the configuration. Avoid trailing spaces.

## Step 6 - Run the MIDI controller

From the package folder in PowerShell:

```powershell
py -m tmate1_midi
```

Or use the Windows launcher:

```powershell
bin\tmate1-midi.cmd
```

Both start the tray icon, the MIDI engine and the local configurator. Open:

```
http://127.0.0.1:8067/
```

Use `--open` to open the browser automatically:

```powershell
py -m tmate1_midi --open
```

Run without the tray, for a console window and easy log reading:

```powershell
bin\tmate1-midi.cmd --no-tray
```

With `--no-tray`, press `Ctrl+C` to stop. In tray mode, right-click the tray
icon and choose **Quit**.

A healthy startup log looks like this:

```
TMate MIDI 0.1.0
config: C:\Users\YOU\AppData\Roaming\tmate1-midi\tmate1-midi.json
MIDI engine started
MIDI output: TMate 1.0
opening TMate 1.0
TMate connected
configurator: http://127.0.0.1:8067/
```

If the tray is unavailable, the app falls back to console mode automatically.
If the MIDI port is not open, the app still reads the TMate and the
configurator shows the exact error.

### First test

1. Open <http://127.0.0.1:8067/>.
2. Click a key button in the diagram, then click **Test selected**.
3. The activity table should show a note-on and note-off (or two CC messages).
4. Turn the wheel. The activity table should show CC messages.
5. In your DAW, select the loopMIDI port as a MIDI input and watch its MIDI
   activity indicator.

The default mappings are:

| Control | MIDI message | Notes |
| --- | --- | --- |
| Wheel | CC 1, channel 1 | Relative, 64-centered; clockwise increases |
| Key 1 | Note 60, channel 1, velocity 127 | Momentary, leftmost key |
| Key 2 | Note 61, channel 1, velocity 127 | Momentary |
| Key 3 | Note 62, channel 1, velocity 127 | Momentary |
| Key 4 | Note 63, channel 1, velocity 127 | Momentary, rightmost key |

## Using the configurator

The web page is the main control panel. It is served only on your computer.

- **Status chips** show whether the TMate and MIDI output are connected.
- **Wheel and key diagram** selects the control you want to edit.
- **Test selected** sends a sample message immediately.
- **Port selector** chooses the loopMIDI port; **Refresh ports** rescans.
- **Activity** shows the last messages, including the exact MIDI hex bytes.
- **Reset** restores the defaults. **Reload** reads the file from disk.
- Changes save automatically after about 350 ms. There is no Save button.

### Wheel settings

| Setting | Range | Meaning |
| --- | --- | --- |
| Channel | 1-16 | MIDI channel |
| CC | 0-127 | Controller number |
| Format | offset, twos, increment | Relative encoding |
| Step | 1-16 | Multiplier per hardware step |
| Invert | on/off | Flips the hardware direction |
| Acceleration | on/off | Fast turns move farther |
| Max delta | 1-63 | Splits long turns into several messages |

The TMate reports clockwise as a negative raw value. The default
**Invert: on** makes clockwise increase the MIDI value. Turn it off if your DAW
expects the raw direction.

### Key settings

| Setting | Range | Meaning |
| --- | --- | --- |
| Channel | 1-16 | MIDI channel |
| Type | note, cc | Message type |
| Number | 0-127 | Note number or CC number |
| Velocity | 0-127 | Note-on velocity (notes only) |
| Value | 0-127 | CC value (CCs only) |
| Behavior | momentary, toggle | Release behavior |

**Momentary:** press sends note-on or CC value; release sends note-off or CC 0.

**Toggle:** the first press turns on; release does nothing; the next press turns
off. A latched note or CC is released automatically when the device disconnects
or the app stops.

### Port selector

On Windows the selector lists loopMIDI and hardware MIDI outputs. Pick the port
your DAW listens to. Windows adds a number to every MIDI port name, so the
loopMIDI port `TMate 1.0` is listed as `TMate 1.0 1`. The app matches either
form, so the default `midi.port` of `TMate 1.0` works without changes. The virtual-port option is Linux-only and is not shown on
Windows.

If the loopMIDI port is missing, start loopMIDI, create the port, then click
**Refresh ports**. The status chip shows a MIDI enumeration error if Windows
cannot list the ports at all.

## MIDI mapping and DAW setup

### Relative CC formats

The wheel sends one MIDI CC per detected turn. The meaning of the value depends
on the format:

| Format | Increase | Decrease | No change |
| --- | --- | --- | --- |
| offset | 65 to 127 | 63 to 0 | 64 |
| twos | 1 to 63 | 127 to 65 | 0 |
| increment | 127 per step | 1 per step | 0 |

Use **offset** for most "relative" or "bin offset" mappings. Use **twos** for
two's-complement relative modes. Use **increment** for 1/127 or Mackie-style
relative modes.

If the control moves the wrong way, either turn **Invert** off/on or choose the
opposite relative mode in the DAW. If one click moves two steps, set **Step** to
1 or lower the DAW sensitivity.

### DAW checklist

1. Start loopMIDI and keep the **TMate 1.0** port alive.
2. Start `tmate1_midi`.
3. In the DAW, enable **TMate 1.0** as a MIDI input.
4. Create a MIDI mapping, MIDI learn, generic remote or MIDI remote entry.
5. For a knob, choose the DAW's relative mode that matches the format above.
6. For a key, map the note number (60-63 by default) to the desired action.
7. Turn the wheel slowly and watch the activity table in the configurator.

Common uses:

- wheel to volume, pan, filter cutoff, tempo or jog/scrub;
- key 1/2 to previous/next or transport start/stop;
- key 3/4 to record, metronome, mute or solo;
- keys as CC toggles for track arm, monitor or effects.

The app does not include a MIDI learn function. Set the CC or note number here,
then use the DAW's own learn function if it has one. You can also map the
default notes 60-63 directly.

Some DAWs label note 60 as C4 and others as C3; the MIDI number is always 60.
Use the number, not the note name, when in doubt.

## Configuration file

The app uses the first available path:

1. `%TMATE1_MIDI_CONFIG%`
2. `tmate1-midi.json` in the current folder, if it already exists
3. `%APPDATA%\tmate1-midi\tmate1-midi.json`

The default on Windows is:

```
C:\Users\YOURNAME\AppData\Roaming\tmate1-midi\tmate1-midi.json
```

A missing file is created with defaults. Changes in the configurator are saved
there automatically. If you edit the file by hand while the app is running,
click **Reload** or restart the app; otherwise the next auto-save can overwrite
your edit.

The full default configuration is in
[Appendix A](#appendix-a-default-configuration).

Important fields:

- `midi.port`: the loopMIDI or hardware output name.
- `midi.virtual`: `"auto"`, `true` or `false`. On Windows, `"auto"` resolves to
  `false` and the app connects to the loopMIDI port instead of creating one.
- `wheel.format`: `offset`, `twos` or `increment`.
- `wheel.invert`: flips the wheel direction.
- `keys.key1` to `keys.key4`: note/CC number, velocity/value and behavior.
- `web.host` and `web.port`: the local configurator address.
- `device.hz`: polling rate, default 100.

Do not expose the configurator to a network by changing `web.host` to
`0.0.0.0` without adding authentication. The default `127.0.0.1` is local-only.

## Command-line reference

| Option | Meaning |
| --- | --- |
| `--config PATH` | Use a specific configuration file |
| `--port NAME` | Override the MIDI output port name |
| `--list-ports` | List MIDI outputs and exit |
| `--web-port N` | Configurator port, default 8067 |
| `--no-web` | Do not start the web configurator |
| `--no-tray` | Console mode; Ctrl+C to stop |
| `--open` | Open the configurator in the browser |
| `--dry-run` | Read the TMate, log MIDI, open no output |
| `--duration SECONDS` | Stop after this many seconds |
| `--hz N` | Poll rate, 20-500, default 100 |
| `--verbose` | Log every MIDI message |
| `--version` | Print the version and exit |

Examples:

```powershell
py -m tmate1_midi --list-ports
py -m tmate1_midi --port "TMate 1.0"
py -m tmate1_midi --web-port 9000 --open
py -m tmate1_midi --no-tray --verbose
py -m tmate1_midi --dry-run --duration 5 --no-web --no-tray
```

The launcher accepts the same options:

```powershell
bin\tmate1-midi.cmd --port "TMate 1.0"
```

## Diagnostic monitor

The monitor prints wheel movement and key presses without MIDI. Use it to
verify the WinUSB driver and the device before setting up loopMIDI.

```powershell
py -m tmate1.monitor --duration 30
```

or `bin\tmate1-monitor.cmd --duration 30`, which works from any folder.

Useful options:

| Option | Meaning |
| --- | --- |
| `--hz N` | Poll rate, default 100 |
| `--interval S` | Wheel display aggregation, default 0.2 s |
| `--wait-key` | Wait for a key press before starting |
| `--wait-motion` | Wait for wheel movement before starting |
| `--raw` | Print the raw 8-byte frame on every read |
| `--verbose` | Print every wheel delta |
| `--no-led` | Skip the LED handshake |

Examples:

```powershell
py -m tmate1.monitor --duration 10 --verbose
py -m tmate1.monitor --wait-motion --duration 10
py -m tmate1.monitor --duration 10 --raw
```

Expected behavior: clockwise movement shows negative step counts, and the keys
show `key1` to `key4`. The monitor and the MIDI controller cannot run at the
same time.

## Autostart

### Recommended: setup script

```powershell
setup-windows.cmd -Autostart
```

This creates `TMate 1.0 MIDI.lnk` in your Startup folder. The shortcut runs
`bin\tmate1-midi-hidden.vbs`, which starts the controller without a console
window (the tray icon is still shown). Remove it with
`setup-windows.cmd -RemoveAutostart`.

### Simple: Startup folder shortcut

1. Create a shortcut to `bin\tmate1-midi.cmd`.
2. Press `Win+R`, type `shell:startup`, and press Enter.
3. Move the shortcut into the Startup folder.

A console window remains visible. This is the simplest and most reliable
option.

### Hidden console with the VBS wrapper

The package includes `bin\tmate1-midi-hidden.vbs`. It finds the package folder
by itself, so no path needs editing. Put a shortcut to it in the Startup folder
(this is what `-Autostart` does). The tray icon is still available. If the app fails to
start, run `bin\tmate1-midi.cmd` directly once to see the error.

### Task Scheduler

Use **Create Task**, trigger **At log on**, action **Start a program**:

- Program: `C:\Windows\System32\cmd.exe`
- Arguments: `/c ""C:\path\to\TMate-1.0-Windows\bin\tmate1-midi.cmd""`
- Start in: `C:\path\to\TMate-1.0-Windows`

The task must run in your interactive user session so it can see the USB device
and the MIDI port. Do not choose "Run whether user is logged on or not".

Also enable **Start with Windows** in loopMIDI. If loopMIDI starts a few seconds
after the controller, the controller retries and connects automatically.

## Troubleshooting

Start every troubleshooting session with a console run:

```powershell
bin\tmate1-midi.cmd --no-tray --verbose
```

The console shows the config path, the MIDI port, the device state and every
message. `Ctrl+C` stops it.

### `py` is not recognised

- Close and reopen PowerShell after installing Python.
- Re-run the installer and enable **Add python.exe to PATH**.
- Check `where py` and `py --version`.
- If you only have `python`, replace `py` with `python` in the commands.

### `pip` cannot reach the internet

- Check the proxy or VPN settings.
- Try `py -m pip install --upgrade pip`.
- As a last resort behind a corporate proxy, use your organisation's package
  mirror or the proxy variables `HTTP_PROXY` and `HTTPS_PROXY`.
- Avoid copying random wheel files from the internet.

### The TMate is not found

- Confirm the USB ID with `lsusb`-style tools is not available on Windows; use
  Device Manager and the libusb check in [Step 3](#step-3-bind-the-tmate-to-winusb-with-zadig).
- Re-run Zadig as administrator and replace the driver with WinUSB.
- Try a different USB port, directly on the computer.
- Close `Tmate.exe`, the monitor, DAWs and any other USB tool.
- Unplug and replug the TMate.
- Run:

  ```powershell
  py -c "import libusb_package; [print(d) for d in libusb_package.find(find_all=True)]"
  ```

- If you see `No backend`, install `pyusb` and `libusb-package`.
- If you see `Access denied`, another process has the device open.

### Access denied or device busy

Only one program can use the TMate. Close:

- `Tmate.exe`;
- `py -m tmate1.monitor`;
- another copy of `tmate1_midi`;
- any generic USB or MIDI tool that opened the device.

Then unplug/replug and start again.

### `TMate 1.0` MIDI port does not open

- Start loopMIDI.
- Create a port named exactly `TMate 1.0`.
- Check for trailing spaces in the name.
- Click **Refresh ports** in the configurator.
- Try `py -m tmate1_midi --list-ports` to see the names Windows reports.
- If you renamed the port, use `--port "Your Name"` or edit `midi.port`.
- The app retries every few seconds; starting loopMIDI later is fine.

### No response in the DAW

- Select **TMate 1.0** as a MIDI input in the DAW.
- Arm the track and enable input monitoring for notes.
- Check the MIDI channel: the default is channel 1.
- Check the activity table: if messages appear there, the app is sending.
- For the wheel, select a relative mode in the DAW; absolute mode will jump.
- For keys, map note numbers 60-63 or switch the key type to CC.
- Make sure the DAW is listening to the loopMIDI port, not to a hardware port.
- Close the configurator's Test button loop and turn the physical wheel.

### Wheel turns the wrong way

Toggle **Invert** in the configurator. The default is on because the hardware
reports clockwise as negative.

### Wheel moves too fast, too slow, or jumps

- Set **Step** to 1.
- Disable **Acceleration**.
- Lower **Max delta** if you want smaller chunks.
- Keep `device.hz` at 100; very low rates can miss short turns.
- If a fast spin jumps, it may be sending several chunked messages; the DAW
  should still accumulate them.

### Keys trigger twice or stay on

- Use **Momentary** for a normal press/release.
- Use **Toggle** for a latching switch.
- Check whether the DAW maps both note-on and note-off to the same action.
- If a note is stuck after unplugging, stop and restart the app; it releases
  active notes on disconnect and shutdown.

### Tray icon is missing

- Install the optional packages:

  ```powershell
  py -m pip install pystray Pillow
  ```

- Check the Windows notification area overflow (the `^` arrow).
- Use `--no-tray` to confirm the rest of the app works.
- On a locked-down machine, the tray may be blocked by policy; console mode is
  fully supported.

### The configurator does not load

- Use <http://127.0.0.1:8067/> exactly; do not use `https`.
- Check whether another program uses port 8067:
  `netstat -ano | findstr :8067`.
- Start with a different port: `py -m tmate1_midi --web-port 9000`.
- Allow Python through Windows Firewall for private networks if prompted.
- Keep `web.host` at `127.0.0.1` unless you really need remote access.

### The app exits immediately

- Run `bin\tmate1-midi.cmd --no-tray --verbose` in PowerShell to see the error.
- Check that all dependencies import:

  ```powershell
  py -c "import usb.core, mido, rtmidi; print('ok')"
  ```

- Check that the config file is valid JSON. Rename it and restart to create a
  fresh one:

  ```powershell
  ren "$env:APPDATA\tmate1-midi\tmate1-midi.json" "tmate1-midi.json.bak"
  ```

### USB instability

- Use a direct rear USB port.
- Avoid unpowered hubs, extension cables and docking stations.
- Unplug/replug the TMate.
- Reboot if the USB controller becomes unresponsive.
- Do not use tools that call `set_configuration()` or read endpoint `0x81`.

### Complete reset

1. Quit the app from the tray or press `Ctrl+C`.
2. Rename or delete
   `%APPDATA%\tmate1-midi\tmate1-midi.json`.
3. Start `py -m tmate1_midi` again.
4. The app creates a fresh default configuration and opens the configurator.

## Safety and correct USB use

The TMate 1.0 has malformed USB descriptors: an 8-byte endpoint with
`bmAttributes=0`, and a broken endpoint `0x81`. The controller avoids the
dangerous paths:

- it never calls `set_configuration()`;
- it never reads endpoint `0x81`;
- it uses only endpoint-0 vendor control transfers.

Do not use generic USB/HID tools, firmware updaters or the original driver
installer on Windows 10/11. Do not run two programs that open the TMate at the
same time. In testing on Linux, `set_configuration()` and endpoint `0x81` reads
crashed an xHCI controller (`xHCI host not responding`, `HC died; cleaning up`).
The same firmware is present on Windows, so treat those operations as unsafe
there too.

If the USB controller misbehaves, unplug the device, reboot, and use another
port. If a machine's USB subsystem stops responding, a reboot is the safest
recovery.

The diagnostic monitor is safe because it uses the same endpoint-0 requests. It
still must not run at the same time as the MIDI controller.

## Uninstall and rollback

To stop using the package:

1. Quit `tmate1_midi` from the tray or console.
2. Remove any Startup shortcut or scheduled task.
3. Quit loopMIDI and remove the **TMate 1.0** port.
4. Optionally uninstall loopMIDI.
5. Optionally uninstall the Python packages:

   ```powershell
   py -m pip uninstall pyusb libusb-package mido python-rtmidi pystray Pillow
   ```

6. Delete the package folder.
7. To remove the WinUSB driver: open Device Manager, right-click the TMate,
   choose **Uninstall device**, tick **Attempt to remove the driver**, unplug
   and replug.

Windows may reinstall WinUSB automatically when the device is replugged. That
is fine for this package. To restore the original `Tmate.exe`, use a Windows 7
virtual machine; the old unsigned driver is not supported on Windows 10/11.

## What's in the package

| Path | Contents |
| --- | --- |
| `TMate-1.0-Windows-Manual.pdf` | This manual |
| `WINDOWS-QUICKSTART.txt` | One-page checklist |
| `README.md` | Project overview and Linux notes |
| `LICENSE` | GNU GPL v3 |
| `requirements.txt` | pyusb only (monitor) |
| `requirements-midi.txt` | Full MIDI controller dependencies |
| `setup-windows.cmd` | Double-click setup and check |
| `setup-windows.ps1` | Setup and check script (PowerShell) |
| `bin\tmate1-midi.cmd` | Windows launcher |
| `bin\tmate1-midi-hidden.vbs` | Hidden-console launcher, used for autostart |
| `bin\tmate1-monitor.cmd` | Windows monitor launcher |
| `bin\tmate1-midi` | POSIX launcher |
| `bin\tmate1-monitor` | POSIX monitor launcher |
| `tmate1\` | Safe USB transport and monitor |
| `tmate1_midi\` | MIDI controller, web configurator, tray |
| `docs\windows.md` | Source of this manual |
| `docs\midi.md` | MIDI controller reference |
| `docs\protocol.md` | Recovered USB protocol |
| `tests\` | Unit tests (Linux/macOS; optional on Windows) |
| `windows\` | Original 2010 software/driver archives, for reference |

The `windows\` archives are not part of the recommended Windows 10/11 setup.
Use them only in a Windows 7 virtual machine or for historical reference.

## Appendix A - Default configuration

```json
{
  "midi": {
    "port": "TMate 1.0",
    "virtual": "auto"
  },
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
    "key1": {
      "channel": 1,
      "type": "note",
      "number": 60,
      "velocity": 127,
      "value": 127,
      "behavior": "momentary"
    },
    "key2": {
      "channel": 1,
      "type": "note",
      "number": 61,
      "velocity": 127,
      "value": 127,
      "behavior": "momentary"
    },
    "key3": {
      "channel": 1,
      "type": "note",
      "number": 62,
      "velocity": 127,
      "value": 127,
      "behavior": "momentary"
    },
    "key4": {
      "channel": 1,
      "type": "note",
      "number": 63,
      "velocity": 127,
      "value": 127,
      "behavior": "momentary"
    }
  },
  "web": {
    "host": "127.0.0.1",
    "port": 8067,
    "open": false
  },
  "device": {
    "hz": 100
  }
}
```

## Appendix B - MIDI message examples

The default configuration sends:

| Action | MIDI bytes | Meaning |
| --- | --- | --- |
| Wheel clockwise | `B0 01 41` | CC 1, channel 1, value 65 |
| Wheel counter-clockwise | `B0 01 3F` | CC 1, channel 1, value 63 |
| Key 1 press | `90 3C 7F` | Note on, note 60, velocity 127 |
| Key 1 release | `80 3C 00` | Note off, note 60, velocity 0 |
| Key 2 press | `90 3D 7F` | Note on, note 61 |
| Key 4 press | `90 3F 7F` | Note on, note 63 |

`B0` is control change on channel 1, `90` is note-on on channel 1, and `80` is
note-off on channel 1. The configurator's activity table shows the same bytes
for every message.

## Appendix C - Protocol summary

The TMate exposes two vendor control requests on endpoint 0:

| Operation | Request |
| --- | --- |
| ReadValue | `bmRequestType=0xC2`, `bRequest=0x0E`, `wValue=0`, `wIndex=0`, `wLength=255` |
| SetLed | `bmRequestType=0xC2`, `bRequest=0x01`, `wValue=0`, `wIndex=led`, `wLength=1` |

ReadValue returns an 8-byte frame:

```
00 01 XX 01 YY 00 KK EE
```

- Bytes 2 and 4 jitter and are ignored.
- Byte 6 is the active-low key byte: idle `0x3F`; bits 0-3 are `key1` to
  `key4`; a cleared bit means pressed.
- Byte 7 is the encoder: `0x80 + signed steps since the previous read`.
  Clockwise is negative, counter-clockwise is positive.
- The first read may contain backlog. The app discards the first frame.

See `docs\protocol.md` for the full recovered protocol.

## Appendix D - Verification checklist

`setup-windows.cmd -CheckOnly` runs most of these checks automatically. To run
them by hand:

```powershell
py --version
py -m pip show pyusb mido python-rtmidi pystray Pillow libusb-package
py -c "import usb.core, mido, rtmidi, pystray, PIL; print('dependencies OK')"
py -m tmate1_midi --list-ports
py -m tmate1.monitor --duration 5
py -m tmate1_midi --dry-run --duration 5 --no-web --no-tray --verbose
```

Then:

1. Start loopMIDI and confirm the **TMate 1.0** port.
2. Start `py -m tmate1_midi`.
3. Open <http://127.0.0.1:8067/>.
4. Confirm the **TMate** status chip is green.
5. Confirm the **MIDI** status chip is green.
6. Click **Test selected** for a key and watch the activity table.
7. Turn the wheel and watch the activity table.
8. Select **TMate 1.0** as a MIDI input in the DAW.
9. Map a knob in relative mode and a note/CC key.
10. Reboot and confirm loopMIDI and the controller start as expected.
