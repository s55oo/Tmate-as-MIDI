import unittest

from tmate1_midi.config import default_config
from tmate1_midi.mapping import (
    effective_delta,
    encode_relative,
    keys_from_byte,
    keys_from_mask,
    midi_hex,
    signed_delta,
    wheel_values,
)


def wheel(**overrides):
    config = default_config()["wheel"]
    config.update(overrides)
    return config


class SignedDeltaTests(unittest.TestCase):
    def test_center(self):
        self.assertEqual(signed_delta(0x80), 0)

    def test_positive(self):
        self.assertEqual(signed_delta(0x81), 1)
        self.assertEqual(signed_delta(0xFF), 127)

    def test_negative(self):
        self.assertEqual(signed_delta(0x7F), -1)
        self.assertEqual(signed_delta(0x00), -128)


class KeyTests(unittest.TestCase):
    def test_mask(self):
        self.assertEqual(
            keys_from_mask(0b0101),
            {"key1": True, "key2": False, "key3": True, "key4": False},
        )

    def test_active_low_byte(self):
        self.assertEqual(
            keys_from_byte(0x3E),
            {"key1": True, "key2": False, "key3": False, "key4": False},
        )
        self.assertEqual(
            keys_from_byte(0x30),
            {"key1": True, "key2": True, "key3": True, "key4": True},
        )
        self.assertEqual(
            keys_from_byte(0x37),
            {"key1": False, "key2": False, "key3": False, "key4": True},
        )


class EncodingTests(unittest.TestCase):
    def test_offset(self):
        self.assertEqual(encode_relative(0, "offset"), 64)
        self.assertEqual(encode_relative(1, "offset"), 65)
        self.assertEqual(encode_relative(-1, "offset"), 63)
        self.assertEqual(encode_relative(100, "offset"), 127)
        self.assertEqual(encode_relative(-100, "offset"), 0)

    def test_twos(self):
        self.assertEqual(encode_relative(1, "twos"), 1)
        self.assertEqual(encode_relative(-1, "twos"), 127)
        self.assertEqual(encode_relative(5, "twos"), 5)
        self.assertEqual(encode_relative(-5, "twos"), 123)
        self.assertEqual(encode_relative(-64, "twos"), 64)

    def test_increment(self):
        self.assertEqual(encode_relative(1, "increment"), 127)
        self.assertEqual(encode_relative(-1, "increment"), 1)
        self.assertEqual(encode_relative(0, "increment"), 0)

    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            encode_relative(1, "nope")


class WheelTests(unittest.TestCase):
    def test_default_inverts_raw_direction(self):
        w = wheel(invert=True)
        self.assertEqual(wheel_values(-1, w), [65])
        self.assertEqual(wheel_values(1, w), [63])

    def test_no_invert(self):
        w = wheel(invert=False)
        self.assertEqual(wheel_values(1, w), [65])
        self.assertEqual(wheel_values(-1, w), [63])

    def test_step_multiplier(self):
        w = wheel(invert=False, step=3)
        self.assertEqual(wheel_values(1, w), [67])

    def test_acceleration(self):
        w = wheel(invert=False, acceleration=True)
        self.assertEqual(effective_delta(3, w), 6)
        self.assertEqual(wheel_values(3, w), [70])
        self.assertEqual(effective_delta(1, w), 1)

    def test_increment_sends_one_message_per_step(self):
        w = wheel(invert=False, format="increment")
        self.assertEqual(wheel_values(3, w), [127, 127, 127])
        self.assertEqual(wheel_values(-2, w), [1, 1])

    def test_chunking(self):
        w = wheel(invert=False, max_delta=63)
        self.assertEqual(wheel_values(100, w), [127, 101])
        self.assertEqual(wheel_values(-100, w), [1, 27])

    def test_zero(self):
        self.assertEqual(wheel_values(0, wheel()), [])

    def test_twos_chunks(self):
        w = wheel(invert=False, format="twos", max_delta=63)
        self.assertEqual(wheel_values(100, w), [63, 37])
        self.assertEqual(wheel_values(-100, w), [65, 91])

    def test_midi_hex(self):
        self.assertEqual(midi_hex(0xB0, 1, 65), "B0 01 41")


if __name__ == "__main__":
    unittest.main()
