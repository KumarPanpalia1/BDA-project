import unittest

from ledger_logic import (
    binary_label_counts,
    fraud_rate_percent,
    missing_required_headers,
    requires_review,
)


class MissingRequiredHeadersTests(unittest.TestCase):
    def test_returns_sorted_missing_required_headers(self):
        self.assertEqual(
            missing_required_headers(["Amount", "Time"], ["Time", "V1", "Amount"]),
            ["V1"],
        )

    def test_returns_no_missing_headers_when_all_required_headers_exist(self):
        self.assertEqual(
            missing_required_headers(["Amount", "Time", "V1"], ["Time", "V1", "Amount"]),
            [],
        )


class FraudRatePercentTests(unittest.TestCase):
    def test_calculates_rate_from_labeled_record_denominator(self):
        self.assertEqual(fraud_rate_percent(2, 8), 25.0)

    def test_returns_zero_when_there_are_no_labeled_records(self):
        self.assertEqual(fraud_rate_percent(0, 0), 0.0)


class BinaryLabelCountsTests(unittest.TestCase):
    def test_returns_legitimate_and_fraud_counts(self):
        self.assertEqual(binary_label_counts({0.0: 8, 1.0: 2}), (8, 2))

    def test_returns_zero_for_an_absent_binary_class(self):
        self.assertEqual(binary_label_counts({0.0: 8}), (8, 0))


class RequiresReviewTests(unittest.TestCase):
    def test_includes_scores_at_the_threshold(self):
        self.assertTrue(requires_review(0.5, 0.5))

    def test_excludes_scores_below_the_threshold(self):
        self.assertFalse(requires_review(0.499, 0.5))

    def test_includes_scores_above_the_threshold(self):
        self.assertTrue(requires_review(0.501, 0.5))


if __name__ == "__main__":
    unittest.main()