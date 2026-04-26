from django.test import SimpleTestCase

from BTAPI.metrics import classify_developer_effectiveness


class ClassifierTests(SimpleTestCase):
    """Cover Sprint 3 §22-24: classify_developer_effectiveness.

    Six cases give full statement coverage and full branch coverage
    of BTAPI/metrics.py.  Boundary cases 4 and 6 pin the strict-`<`
    semantics of the thresholds and are the cases most likely to
    catch a future `<=` regression.
    """

    def test_zero_data_returns_insufficient(self):
        # fixed_count < 20 branch true (case 1)
        self.assertEqual(
            classify_developer_effectiveness(0, 0),
            "Insufficient data",
        )

    def test_just_below_threshold_returns_insufficient(self):
        # fixed_count < 20 branch true (case 2: 19 fixes is still not enough)
        self.assertEqual(
            classify_developer_effectiveness(19, 0),
            "Insufficient data",
        )

    def test_at_threshold_zero_reopened_returns_good(self):
        # fixed_count < 20 false; ratio 0 < 1/32 true (case 3)
        self.assertEqual(
            classify_developer_effectiveness(20, 0),
            "Good",
        )

    def test_ratio_exactly_one_thirty_second_returns_fair(self):
        # ratio == 1/32 -> ratio < 1/32 false; ratio < 1/8 true (case 4)
        self.assertEqual(
            classify_developer_effectiveness(32, 1),
            "Fair",
        )

    def test_ratio_between_thresholds_returns_fair(self):
        # ratio == 3/32 (0.09375) -> Fair (case 5)
        self.assertEqual(
            classify_developer_effectiveness(32, 3),
            "Fair",
        )

    def test_ratio_exactly_one_eighth_returns_poor(self):
        # ratio == 1/8 -> ratio < 1/8 false -> Poor (case 6)
        self.assertEqual(
            classify_developer_effectiveness(32, 4),
            "Poor",
        )
