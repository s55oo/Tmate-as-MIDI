import unittest

from tmate1_midi.midi import resolve_port_name


class ResolvePortNameTests(unittest.TestCase):
    def test_exact_match_wins(self):
        names = ["TMate 1.0 1", "TMate 1.0"]
        self.assertEqual(resolve_port_name("TMate 1.0", names), "TMate 1.0")

    def test_windows_index_suffix(self):
        names = ["Microsoft GS Wavetable Synth 0", "TMate 1.0 1"]
        self.assertEqual(resolve_port_name("TMate 1.0", names), "TMate 1.0 1")

    def test_case_insensitive_fallback(self):
        self.assertEqual(resolve_port_name("tmate 1.0", ["TMate 1.0 2"]), "TMate 1.0 2")

    def test_trailing_space_in_config(self):
        self.assertEqual(resolve_port_name("TMate 1.0 ", ["TMate 1.0 1"]), "TMate 1.0 1")

    def test_does_not_match_other_suffixes(self):
        self.assertIsNone(resolve_port_name("TMate 1.0", ["TMate 1.0 backup"]))
        self.assertIsNone(resolve_port_name("TMate", ["TMate 1.0 1"]))

    def test_missing_or_empty(self):
        self.assertIsNone(resolve_port_name("TMate 1.0", []))
        self.assertIsNone(resolve_port_name("", ["TMate 1.0 1"]))


if __name__ == "__main__":
    unittest.main()
