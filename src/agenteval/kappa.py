"""Cohen's kappa for judge-vs-human agreement.

Implemented directly (no sklearn dependency) since it's a handful of lines
over a k-class contingency table -- consistent with how wilson_ci in core.py
pulls in statsmodels only for the one thing it needs.
"""
from collections import Counter


def cohen_kappa(rater_a: list[str], rater_b: list[str], labels: list[str]) -> float:
    """Cohen's kappa for two raters scoring the same items on the same label set.

    kappa = (po - pe) / (1 - pe)
    po: observed proportion of agreement
    pe: proportion of agreement expected by chance, from each rater's own
        marginal distribution over labels
    """
    n = len(rater_a)
    if n == 0 or n != len(rater_b):
        raise ValueError("rater_a and rater_b must be equal-length and non-empty")

    po = sum(1 for a, b in zip(rater_a, rater_b) if a == b) / n

    count_a = Counter(rater_a)
    count_b = Counter(rater_b)
    pe = sum((count_a.get(label, 0) / n) * (count_b.get(label, 0) / n) for label in labels)

    if pe == 1.0:
        # Both raters unanimous on the same single label -- no variance to measure
        # agreement beyond chance. Perfect observed agreement, kappa undefined;
        # by convention report 1.0 if po == pe == 1, else 0.0.
        return 1.0 if po == 1.0 else 0.0

    return (po - pe) / (1 - pe)


def confusion_matrix(rater_a: list[str], rater_b: list[str], labels: list[str]) -> dict[str, dict[str, int]]:
    """rows = rater_a (e.g. judge), columns = rater_b (e.g. human)."""
    matrix = {la: {lb: 0 for lb in labels} for la in labels}
    for a, b in zip(rater_a, rater_b):
        matrix[a][b] += 1
    return matrix
