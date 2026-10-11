def missing_required_headers(headers, required_headers):
    return sorted(set(required_headers) - set(headers))


def duplicate_headers(headers):
    seen = set()
    duplicates = set()
    for header in headers:
        if header in seen:
            duplicates.add(header)
        seen.add(header)
    return sorted(duplicates)


def validate_scoring_feature_counts(invalid_counts, feature_columns):
    invalid_features = [
        f"{name} ({invalid_counts.get(name) or 0} rows)"
        for name in feature_columns
        if (invalid_counts.get(name) or 0) > 0
    ]
    if invalid_features:
        raise ValueError(
            "Invalid values in required feature columns: "
            + ", ".join(invalid_features)
            + ". Values must be present, numeric, and finite."
        )


def binary_label_counts(class_counts):
    return class_counts.get(0.0, 0), class_counts.get(1.0, 0)


def fraud_rate_percent(fraud_count, labeled_count):
    return 100 * fraud_count / max(labeled_count, 1)


def requires_review(probability, threshold):
    return probability >= threshold


def review_decision_labels(threshold):
    threshold_percent = f"{threshold:.0%}"
    return (
        f"Review signal (>= {threshold_percent})",
        f"Below threshold (< {threshold_percent})",
    )


def scored_record_counts(scored, threshold, functions):
    total = scored.count()
    review_count = scored.filter(
        functions.col("fraud_probability") >= threshold
    ).count()
    return total, review_count


def sort_scored_results(scored, functions):
    return scored.orderBy(functions.col("fraud_probability").desc())


def limited_scored_results(scored, limit):
    return scored.limit(limit).toPandas()


def scored_csv_bytes(scored, output_directory):
    from pathlib import Path

    scored.coalesce(1).write.option("header", True).mode("overwrite").csv(
        output_directory
    )
    part_file = next(Path(output_directory).glob("part-*.csv"))
    return part_file.read_bytes()