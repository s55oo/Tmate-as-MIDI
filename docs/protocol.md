# TMate 1.0 USB protocol

Recovered from the official Windows software (`ELAD_Encoder.dll`, 2009) and
verified against the unit.

## Device

- VID:PID `1721:0607`, product string `Tmate 1.0 USB`
- USB 1.01 low speed, vendor-specific class, one interface
- Only endpoint 0 is safe to use; endpoint `0x81` has a malformed descriptor
  (8-byte transfer, `bmAttributes=0`)

## Control requests

All transfers are vendor requests to endpoint 0 with `bmRequestType = 0xC2`
(device-to-host, vendor, recipient = endpoint).

### ReadValue

| Field | Value |
| --- | --- |
| `bRequest` | `0x0E` |
| `wValue` | `0` |
| `wIndex` | `0` |
| `wLength` | `255` |

The device returns 8 bytes:

```
00 01 XX 01 YY 00 KK EE
```

| Byte | Meaning |
| --- | --- |
| 0 | always `0x00` |
| 1 | always `0x01` |
| 2 | jitter/counter, varies (`0xB4..0xBC` observed) |
| 3 | always `0x01` |
| 4 | jitter/counter, varies |
| 5 | always `0x00` |
| 6 | key state |
| 7 | `0x80 + signed steps since previous read` |

Bytes 2 and 4 move together and are not needed for input decoding.

### Key byte (byte 6)

Idle is `0x3F`; the four keys are active-low and clear bits 0..3:

| Physical key | Raw byte | Bit cleared |
| --- | --- | --- |
| leftmost (`key1`) | `0x3E` | 0 |
| 2nd (`key2`) | `0x3D` | 1 |
| 3rd (`key3`) | `0x3B` | 2 |
| rightmost (`key4`) | `0x37` | 3 |

`Tmate.exe` also recognizes `0x77`, `0x7B`, `0x7D` (the same low bits with
bit 6 cleared).  That alternate group was not observed on this unit; it may be
a shifted/held-key state.

### Encoder byte (byte 7)

The value is a signed step count with `0x80` as zero, consumed by each read:

- `0x80` = no movement since the previous read
- `0x81..0xFF` = positive steps (counterclockwise on this unit)
- `0x7F..0x00` = negative steps (clockwise on this unit)

The original DLL computes `0x80 - byte7`; the sign convention above is the one
used by this project.  Because each read clears the count, the host poll rate
determines resolution.  Reading faster than the device updates simply yields
zero-valued deltas between steps.  The first read after opening can contain a
backlog of movement made while nothing was polling; discard it.

### SetLed

| Field | Value |
| --- | --- |
| `bRequest` | `0x01` |
| `wValue` | `0` |
| `wIndex` | LED value (official app uses `1` on connect, `0` on exit) |
| `wLength` | `1` |

The unit may answer with a zero-length packet; that is not an error.

## References

- `ELAD_Encoder.dll` (2009) exports: `OpenConnection`, `CloseConnection`,
  `ReadValue`, `SetLed`
- `Tmate.exe` keys the same controls and maps the key codes above
- TMate 2 (`1721:0614`) is a different protocol (64-byte HID-style reports)
  and is not handled here.
