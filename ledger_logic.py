def missing_required_headers(headers, required_headers):
    return sorted(set(required_headers) - set(headers))


def binary_label_counts(class_counts):
    return class_counts.get(0.0, 0), class_counts.get(1.0, 0)


def fraud_rate_percent(fraud_count, labeled_count):
    return 100 * fraud_count / max(labeled_count, 1)


def requires_review(probability, threshold):
    return probability >= threshold