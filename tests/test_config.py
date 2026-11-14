import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tmate1_midi.config import (
    ConfigError,
    default_config,
    default_config_path,
    load_config,
    save_config,
    validate_config,
)


class DefaultConfigTests(unittest.TestCase):
    def test_default_is_a_copy(self):
        first = default_config()
        first["wheel"]["cc"] = 99
        self.assertEqual(default_config()["wheel"]["cc"], 1)

    def test_empty_config_gets_defaults(self):
        config = validate_config({})
        self.assertEqual(config["wheel"]["cc"], 1)
        self.assertEqual(config["midi"]["port"], "TMate 1.0")
        self.assertEqual(config["device"]["hz"], 100)
        self.assertEqual(len(config["keys"]), 4)

    def test_partial_config_is_merged(self):
        config = validate_config({"wheel": {"cc": 7}})
        self.assertEqual(config["wheel"]["cc"], 7)
        self.assertEqual(config["wheel"]["channel"], 1)
        self.assertEqual(config["keys"]["key1"]["number"], 60)

    def test_unknown_keys_are_preserved(self):
        config = validate_config({"extra": {"a": 1}})
        self.assertEqual(config["extra"], {"a": 1})


class ValidationTests(unittest.TestCase):
    def test_channels(self):
        for value in (0, 17):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                validate_config({"wheel": {"channel": value}})
        for value in (0, 17):
            with self.subTest(key=value), self.assertRaises(ConfigError):
                validate_config({"keys": {"key1": {"channel": value}}})

    def test_cc_and_numbers(self):
        for value in (-1, 128):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    validate_config({"wheel": {"cc": value}})
                with self.assertRaises(ConfigError):
                    validate_config({"keys": {"key1": {"number": value}}})

    def test_choices(self):
        with self.assertRaises(ConfigError):
            validate_config({"wheel": {"format": "nope"}})
        with self.assertRaises(ConfigError):
            validate_config({"keys": {"key1": {"type": "nope"}}})
        with self.assertRaises(ConfigError):
            validate_config({"keys": {"key1": {"behavior": "nope"}}})

    def test_limits(self):
        with self.assertRaises(ConfigError):
            validate_config({"wheel": {"step": 0}})
        with self.assertRaises(ConfigError):
            validate_config({"wheel": {"step": 17}})
        with self.assertRaises(ConfigError):
            validate_config({"wheel": {"max_delta": 0}})
        with self.assertRaises(ConfigError):
            validate_config({"wheel": {"max_delta": 64}})
        with self.assertRaises(ConfigError):
            validate_config({"device": {"hz": 10}})
        with self.assertRaises(ConfigError):
            validate_config({"device": {"hz": 501}})
        with self.assertRaises(ConfigError):
            validate_config({"web": {"port": 0}})

    def test_virtual_normalization(self):
        self.assertEqual(validate_config({"midi": {"virtual": "auto"}})["midi"]["virtual"], "auto")
        self.assertIs(validate_config({"midi": {"virtual": "true"}})["midi"]["virtual"], True)
        self.assertIs(validate_config({"midi": {"virtual": "no"}})["midi"]["virtual"], False)
        with self.assertRaises(ConfigError):
            validate_config({"midi": {"virtual": "maybe"}})

    def test_booleans(self):
        config = validate_config({"wheel": {"invert": "no", "acceleration": "yes"}})
        self.assertIs(config["wheel"]["invert"], False)
        self.assertIs(config["wheel"]["acceleration"], True)


class FileTests(unittest.TestCase):
    def test_missing_file_is_created(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nested" / "config.json"
            config = load_config(path, create=True)
            self.assertTrue(path.exists())
            self.assertEqual(config["wheel"]["cc"], 1)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            config = default_config()
            config["wheel"]["cc"] = 42
            config["keys"]["key4"]["type"] = "cc"
            save_config(path, config)
            loaded = load_config(path)
            self.assertEqual(loaded["wheel"]["cc"], 42)
            self.assertEqual(loaded["keys"]["key4"]["type"], "cc")

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_saved_file_is_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            save_config(path, default_config())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("wheel", data)

    def test_default_path_env(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "custom.json"
            with patch.dict(os.environ, {"TMATE1_MIDI_CONFIG": str(path)}):
                self.assertEqual(default_config_path(), path)


if __name__ == "__main__":
    unittest.main()
