import json
import os
import tempfile
import unittest
from unittest.mock import patch


class ScaleConfigLoadTest(unittest.TestCase):
    def test_config_without_initial_max_weight_is_valid(self):
        from scale_config import load_scale_config

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "scale_config.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"offset": 140173.33, "referenceUnit": 425.37}, handle)
            loaded = load_scale_config(path)
        self.assertEqual(loaded["offset"], 140173.33)
        self.assertEqual(loaded["referenceUnit"], 425.37)
        self.assertIsNone(loaded["initialMaxWeight"])
        self.assertIsNone(loaded["lastWeight"])

    def test_round_trip_preserves_last_weight(self):
        from scale_config import load_scale_config, save_scale_config

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "scale_config.json")
            save_scale_config(
                path,
                {
                    "offset": 1,
                    "referenceUnit": 425.37,
                    "lastWeight": 248.5,
                },
            )
            loaded = load_scale_config(path)
        self.assertEqual(loaded["lastWeight"], 248.5)
        self.assertIsNone(loaded["initialMaxWeight"])

    def test_bt_mac_prefers_environment(self):
        from bt import resolve_target_address

        with patch.dict(os.environ, {"DRINKSYNC_BT_MAC": "AA:BB:CC:DD:EE:FF"}):
            self.assertEqual(resolve_target_address(), "AA:BB:CC:DD:EE:FF")

    def test_bt_mac_falls_back_to_default(self):
        from bt import DEFAULT_TARGET_ADDRESS, resolve_target_address

        env = os.environ.copy()
        env.pop("DRINKSYNC_BT_MAC", None)
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(resolve_target_address(), DEFAULT_TARGET_ADDRESS)


if __name__ == "__main__":
    unittest.main()
