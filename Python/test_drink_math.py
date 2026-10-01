import unittest

from drink_math import MIN_DRINK_GRAMS, leftover_after_adding, next_drink


class NextDrinkTest(unittest.TestCase):
    def test_first_reading_adopts_weight_and_sends_nothing(self):
        grams, previous = next_drink(None, 300.0)
        self.assertIsNone(grams)
        self.assertEqual(previous, 300.0)

    def test_sip_sends_only_the_drop(self):
        grams, previous = next_drink(300.0, 250.0)
        self.assertAlmostEqual(grams, 50.0)
        self.assertEqual(previous, 250.0)

    def test_second_sip_is_not_cumulative(self):
        _, after_first = next_drink(300.0, 250.0)
        grams, after_second = next_drink(after_first, 200.0)
        self.assertAlmostEqual(grams, 50.0)
        self.assertEqual(after_second, 200.0)

    def test_refill_sends_nothing_and_adopts_new_weight(self):
        grams, previous = next_drink(200.0, 310.0)
        self.assertIsNone(grams)
        self.assertEqual(previous, 310.0)

    def test_noise_below_threshold_keeps_previous(self):
        grams, previous = next_drink(200.0, 197.0)
        self.assertIsNone(grams)
        self.assertEqual(previous, 200.0)

    def test_exact_minimum_counts_as_a_drink(self):
        grams, previous = next_drink(200.0, 200.0 - MIN_DRINK_GRAMS)
        self.assertAlmostEqual(grams, MIN_DRINK_GRAMS)
        self.assertEqual(previous, 195.0)


class LeftoverGramsTest(unittest.TestCase):
    def test_small_sip_stays_in_leftover(self):
        ounces, leftover = leftover_after_adding(0.0, 10.0)
        self.assertEqual(ounces, 0)
        self.assertAlmostEqual(leftover, 10.0)

    def test_leftover_plus_sip_can_make_one_ounce(self):
        ounces, leftover = leftover_after_adding(10.0, 20.0)
        self.assertEqual(ounces, 1)
        self.assertAlmostEqual(leftover, 30.0 - 29.5735, places=4)


if __name__ == "__main__":
    unittest.main()
