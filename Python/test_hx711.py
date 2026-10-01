import unittest
from unittest.mock import patch


class Hx711PureHelpersTest(unittest.TestCase):
    def test_get_reference_unit_returns_channel_a(self):
        from hx711 import HX711

        with patch("hx711.GPIO"):
            hx = HX711.__new__(HX711)
            hx.REFERENCE_UNIT = 425.37
            self.assertEqual(hx.get_reference_unit(), 425.37)

    def test_even_median_uses_integer_midpoint(self):
        from hx711 import HX711

        hx = HX711.__new__(HX711)
        values = iter([10, 20, 30, 40])
        hx.read_long = lambda: next(values)
        self.assertEqual(hx.read_median(4), 25.0)

    def test_constructing_without_gpio_does_not_crash(self):
        from hx711 import HX711

        hx = HX711(5, 6)
        self.assertEqual(hx.get_gain(), 128)

    def test_wait_ready_times_out(self):
        from hx711 import HX711, Hx711TimeoutError

        with patch("hx711.GPIO") as gpio:
            gpio.input.return_value = 1
            hx = HX711.__new__(HX711)
            hx.DOUT = 5
            with self.assertRaises(Hx711TimeoutError):
                hx._wait_ready(timeout_s=0.01)


if __name__ == "__main__":
    unittest.main()
