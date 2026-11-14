import unittest

from tmate1_midi.config import default_config
from tmate1_midi.engine import MidiEngine
from tmate1_midi.midi import NullMidiOut


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.config = default_config()
        self.midi = NullMidiOut()
        self.engine = MidiEngine(self.config, self.midi)
        self.engine.process_sample(0, 0)

    def sent(self):
        return self.midi.sent

    def test_prime_ignores_first_sample(self):
        midi = NullMidiOut()
        engine = MidiEngine(default_config(), midi)
        engine.process_sample(-5, 0b0001)
        self.assertEqual(midi.sent, [])

    def test_key_press_and_release(self):
        self.engine.process_sample(0, 0b0001)
        message = self.sent()[-1]
        self.assertEqual(message.type, "note_on")
        self.assertEqual(message.channel, 0)
        self.assertEqual(message.note, 60)
        self.assertEqual(message.velocity, 127)

        self.engine.process_sample(0, 0)
        message = self.sent()[-1]
        self.assertEqual(message.type, "note_off")
        self.assertEqual(message.note, 60)

    def test_wheel_default_inverts_clockwise(self):
        self.engine.process_sample(-1, 0)
        message = self.sent()[-1]
        self.assertEqual(message.type, "control_change")
        self.assertEqual(message.control, 1)
        self.assertEqual(message.value, 65)

        self.engine.process_sample(1, 0)
        self.assertEqual(self.sent()[-1].value, 63)

    def test_wheel_step_multiplier(self):
        self.config["wheel"]["step"] = 2
        self.engine.process_sample(-1, 0)
        self.assertEqual(self.sent()[-1].value, 66)

    def test_wheel_twos(self):
        self.config["wheel"]["format"] = "twos"
        self.engine.process_sample(-1, 0)
        self.assertEqual(self.sent()[-1].value, 1)
        self.engine.process_sample(1, 0)
        self.assertEqual(self.sent()[-1].value, 127)

    def test_toggle_note(self):
        self.config["keys"]["key1"]["behavior"] = "toggle"
        self.engine.process_sample(0, 0b0001)
        self.assertEqual(self.sent()[-1].type, "note_on")

        count = len(self.sent())
        self.engine.process_sample(0, 0)
        self.assertEqual(len(self.sent()), count)

        self.engine.process_sample(0, 0b0001)
        self.assertEqual(self.sent()[-1].type, "note_off")

        count = len(self.sent())
        self.engine.process_sample(0, 0)
        self.assertEqual(len(self.sent()), count)

    def test_toggle_cc(self):
        self.config["keys"]["key2"] = {
            "channel": 1,
            "type": "cc",
            "number": 20,
            "velocity": 127,
            "value": 100,
            "behavior": "toggle",
        }
        self.engine.process_sample(0, 0b0010)
        self.assertEqual(self.sent()[-1].control, 20)
        self.assertEqual(self.sent()[-1].value, 100)

        self.engine.process_sample(0, 0)
        count = len(self.sent())
        self.engine.process_sample(0, 0b0010)
        self.assertEqual(len(self.sent()), count + 1)
        self.assertEqual(self.sent()[-1].control, 20)
        self.assertEqual(self.sent()[-1].value, 0)

    def test_momentary_cc(self):
        self.config["keys"]["key3"] = {
            "channel": 1,
            "type": "cc",
            "number": 21,
            "velocity": 127,
            "value": 100,
            "behavior": "momentary",
        }
        self.engine.process_sample(0, 0b0100)
        self.assertEqual(self.sent()[-1].control, 21)
        self.assertEqual(self.sent()[-1].value, 100)
        self.engine.process_sample(0, 0)
        self.assertEqual(self.sent()[-1].control, 21)
        self.assertEqual(self.sent()[-1].value, 0)

    def test_release_all(self):
        self.engine.process_sample(0, 0b0001)
        self.engine._release_all()
        self.assertEqual(self.sent()[-1].type, "note_off")
        self.assertEqual(self.sent()[-1].note, 60)

    def test_test_control(self):
        result = self.engine.test_control("key2")
        self.assertEqual(result, ["90 3D 7F", "80 3D 00"])
        result = self.engine.test_control("wheel", -1)
        self.assertEqual(result, ["B0 01 41"])
        result = self.engine.test_control("wheel", 1)
        self.assertEqual(result, ["B0 01 3F"])
        with self.assertRaises(ValueError):
            self.engine.test_control("nope")

    def test_activity(self):
        self.engine.process_sample(0, 0b0001)
        activity = self.engine.status()["activity"]
        self.assertEqual(activity[0]["control"], "key1")
        self.assertTrue(activity[0]["sent"])
        self.assertEqual(activity[0]["hex"], "90 3C 7F")
        self.engine.clear_activity()
        self.assertEqual(self.engine.status()["activity"], [])

    def test_status_keys(self):
        self.engine.process_sample(0, 0b0101)
        keys = self.engine.status()["keys"]
        self.assertTrue(keys["key1"])
        self.assertFalse(keys["key2"])
        self.assertTrue(keys["key3"])


if __name__ == "__main__":
    unittest.main()
