"""Low-level transport for the WoodBoxRadio/ELAD TMate 1.0 USB knob.

The TMate 1.0 is a vendor-specific low-speed USB device (VID 1721, PID 0607).
It has no kernel driver and no usable HID report descriptor; the official
Windows software talks to it through WinUSB with two vendor control requests
on endpoint 0:

    ReadValue:  bmRequestType=0xC2  bRequest=0x0E  wValue=0  wIndex=0  wLength=255
    SetLed:     bmRequestType=0xC2  bRequest=0x01  wValue=0  wIndex=led  wLength=1

ReadValue returns an 8-byte frame.  Byte 6 is the active-low key byte and
byte 7 is 0x80 + signed encoder steps since the previous read.
"""

from __future__ import annotations

import usb.core
import usb.util

VID = 0x1721
PID = 0x0607

REQUEST_READ_VALUE = 0x0E
REQUEST_SET_LED = 0x01
REQUEST_TYPE = 0xC2

KEY_IDLE = 0x3F
KEY_MASK = 0x0F
ENCODER_CENTER = 0x80


class TmateNotFound(RuntimeError):
    pass


def _get_backend():
    """Use the libusb bundled by ``libusb-package`` when it is installed.

    PyUSB needs libusb-1.0.dll on Windows, which is not on PATH by default.
    The ``libusb-package`` wheel ships it and exposes its path, so this keeps
    the same code working on Windows without manual DLL copying.
    """
    try:
        import libusb_package
    except Exception:
        return None
    try:
        return libusb_package.get_libusb1_backend()
    except Exception:
        return None


class Tmate1:
    """A connected TMate 1.0."""

    def __init__(self, device=None):
        if device is None:
            try:
                device = usb.core.find(
                    idVendor=VID, idProduct=PID, backend=_get_backend()
                )
            except usb.core.NoBackendError as exc:
                raise TmateNotFound(
                    "no libusb backend found; install pyusb and, on Windows, "
                    "libusb-package, then bind the device to WinUSB with Zadig"
                ) from exc
        self._dev = device
        if self._dev is None:
            raise TmateNotFound(
                "TMate 1.0 (1721:0607) not found; check the USB cable and "
                "that the host controller is alive"
            )
        # Do NOT call set_configuration() or read endpoint 0x81 here.  This
        # firmware's descriptors are malformed (8-byte endpoint with
        # bmAttributes=0) and those calls have crashed the xHCI host.
        # Endpoint-0 vendor control transfers work without configuration.
        self._led = None

    def close(self):
        if self._dev is not None:
            usb.util.dispose_resources(self._dev)
            self._dev = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def read_frame(self, timeout=1000):
        """Return the raw 8-byte frame from the device."""
        data = self._dev.ctrl_transfer(
            REQUEST_TYPE,
            REQUEST_READ_VALUE,
            0,
            0,
            255,
            timeout=timeout,
        )
        return bytes(data)

    def read(self, timeout=1000):
        """Return (steps, keys, frame).

        steps is the signed encoder movement since the previous read,
        keys is a 4-bit mask of currently pressed keys (bit 0 = key 1).
        """
        frame = self.read_frame(timeout=timeout)
        if len(frame) < 8:
            raise OSError(f"short TMate frame: {frame.hex()}")

        keys = (~frame[6]) & KEY_MASK
        steps = frame[7] - ENCODER_CENTER
        return steps, keys, frame

    def set_led(self, value, timeout=1000):
        """Send the original SetLed value (bitmask, 0 = off).

        The official DLL puts the value in wIndex and uses a 1-byte IN data
        stage.  Many units answer with a zero-length packet, so the returned
        bytes are not treated as an error.
        """
        self._led = value
        try:
            return bytes(
                self._dev.ctrl_transfer(
                    REQUEST_TYPE, REQUEST_SET_LED, 0, value, 1, timeout=timeout
                )
            )
        except usb.core.USBError:
            return b""
