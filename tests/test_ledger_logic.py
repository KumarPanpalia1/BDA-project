import csv
import tempfile
import unittest
from pathlib import Path

from ledger_logic import (
    binary_label_counts,
    duplicate_headers,
    fraud_rate_percent,
    missing_required_headers,
    requires_review,
    review_decision_labels,
    scored_record_counts,
    sort_scored_results,
    limited_scored_results,
    scored_csv_bytes,
    validate_scoring_feature_counts,
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


class ScoringUploadValidationTests(unittest.TestCase):
    def test_identifies_duplicate_headers_before_schema_creation(self):
        self.assertEqual(
            duplicate_headers(["Time", "V1", "Amount", "V1"]),
            ["V1"],
        )

    def test_accepts_feature_counts_without_invalid_values(self):
        validate_scoring_feature_counts({"Time": 0, "Amount": 0}, ["Time", "Amount"])

    def test_reports_features_with_missing_values(self):
        with self.assertRaisesRegex(ValueError, "Time.*present, numeric, and finite"):
            validate_scoring_feature_counts({"Time": 2, "Amount": 0}, ["Time", "Amount"])

    def test_reports_features_with_malformed_numeric_values(self):
        with self.assertRaisesRegex(ValueError, "Amount.*present, numeric, and finite"):
            validate_scoring_feature_counts({"Time": 0, "Amount": 1}, ["Time", "Amount"])


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


class ScoreColumn:
    def __init__(self, name):
        self.name = name

    def __ge__(self, threshold):
        return lambda row: row[self.name] >= threshold

    def desc(self):
        return self.name


class FakeFunctions:
    @staticmethod
    def col(name):
        return ScoreColumn(name)


class FakeWriter:
    def __init__(self, frame):
        self.frame = frame
        self.options = {}

    def option(self, name, value):
        self.options[name] = value
        return self

    def mode(self, value):
        return self

    def csv(self, path):
        output_path = Path(path) / "part-00000.csv"
        with output_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=self.frame.rows[0].keys())
            if self.options.get("header"):
                writer.writeheader()
            writer.writerows(self.frame.rows)


class FakeScoredFrame:
    def __init__(self, rows):
        self.rows = rows

    @property
    def write(self):
        return FakeWriter(self)

    def count(self):
        return len(self.rows)

    def filter(self, predicate):
        return FakeScoredFrame([row for row in self.rows if predicate(row)])

    def orderBy(self, key):
        return FakeScoredFrame(sorted(self.rows, key=lambda row: row[key], reverse=True))

    def limit(self, count):
        return FakeScoredFrame(self.rows[:count])

    def toPandas(self):
        return self.rows

    def coalesce(self, partitions):
        return self


class ScoredResultsTests(unittest.TestCase):
    def test_large_upload_counts_all_records_caps_display_and_downloads_all_sorted_rows(self):
        row_count = 10025
        scored = FakeScoredFrame(
            [
                {
                    "transaction_id": index,
                    "fraud_probability": index / row_count,
                    "decision": "Review signal" if index / row_count >= 0.5 else "Below review threshold",
                }
                for index in range(row_count)
            ]
        )

        ordered = sort_scored_results(scored, FakeFunctions)
        total, review = scored_record_counts(ordered, 0.5, FakeFunctions)
        display = limited_scored_results(ordered, 10000)
        with tempfile.TemporaryDirectory() as output_directory:
            download = scored_csv_bytes(ordered, output_directory)

        self.assertEqual((total, review), (10025, 5012))
        self.assertEqual(len(display), 10000)
        self.assertEqual(display[0]["fraud_probability"], (row_count - 1) / row_count)
        self.assertEqual(display[-1]["fraud_probability"], 25 / row_count)
        self.assertTrue(
            all(
                current["fraud_probability"] >= following["fraud_probability"]
                for current, following in zip(display, display[1:])
            )
        )
        downloaded_rows = list(csv.DictReader(download.decode("utf-8").splitlines()))
        self.assertEqual(len(downloaded_rows), 10025)
        self.assertEqual(
            float(downloaded_rows[0]["fraud_probability"]), (row_count - 1) / row_count
        )
        self.assertEqual(float(downloaded_rows[-1]["fraud_probability"]), 0.0)
        self.assertEqual(
            sum(row["decision"] == "Review signal" for row in downloaded_rows), 5012
        )
        self.assertTrue(
            all(
                float(current["fraud_probability"])
                >= float(following["fraud_probability"])
                for current, following in zip(downloaded_rows, downloaded_rows[1:])
            )
        )

    def test_review_count_includes_score_exactly_at_threshold(self):
        scored = FakeScoredFrame(
            [
                {"fraud_probability": 0.5},
                {"fraud_probability": 0.499},
            ]
        )

        self.assertEqual(scored_record_counts(scored, 0.5, FakeFunctions), (2, 1))

    def test_threshold_label_states_inclusive_probability_boundary(self):
        self.assertEqual(
            review_decision_labels(0.5),
            ("Review signal (>= 50%)", "Below threshold (< 50%)"),
        )


if __name__ == "__main__":
    unittest.main()