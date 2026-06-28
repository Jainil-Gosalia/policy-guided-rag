"""
Statistical significance testing for paired retrieval comparisons.

All experiments compare two systems on the *same* set of queries, so the
appropriate tests are paired:

  * accuracy (binary hit/miss per query) -> McNemar's exact test
  * rank / position (ordinal per query)   -> Wilcoxon signed-rank test

Bootstrap percentile confidence intervals are provided for effect sizes
(accuracy deltas and mean-rank deltas) so the reader can judge magnitude as
well as significance. The bootstrap is seeded for reproducibility.
"""
from typing import List, Dict, Sequence
import random

from scipy.stats import wilcoxon
from scipy.stats import binomtest


def mcnemar_test(a_hits: Sequence[bool], b_hits: Sequence[bool]) -> Dict:
    """Exact McNemar test on paired binary outcomes (e.g. top-k hit).

    Compares system A vs system B over the same queries. Uses the exact
    binomial form, which is valid for small discordant counts.

    Args:
        a_hits: per-query hit/miss for system A
        b_hits: per-query hit/miss for system B (same order/length)

    Returns:
        Dict with discordant counts (b01: A miss & B hit, b10: A hit & B miss)
        and the two-sided exact p-value.
    """
    if len(a_hits) != len(b_hits):
        raise ValueError("paired sequences must be the same length")

    # b01 = A wrong, B right (B helped); b10 = A right, B wrong (B hurt)
    b01 = sum(1 for a, b in zip(a_hits, b_hits) if (not a) and b)
    b10 = sum(1 for a, b in zip(a_hits, b_hits) if a and (not b))
    n = b01 + b10

    if n == 0:
        p_value = 1.0
    else:
        p_value = binomtest(b01, n, 0.5, alternative="two-sided").pvalue

    return {
        "b01_only_B_correct": b01,
        "b10_only_A_correct": b10,
        "discordant": n,
        "p_value": float(p_value),
        "significant_at_0.05": bool(p_value < 0.05),
    }


def wilcoxon_test(a_positions: Sequence[float], b_positions: Sequence[float]) -> Dict:
    """Wilcoxon signed-rank test on paired ranks/positions (lower is better).

    Args:
        a_positions: per-query position for system A
        b_positions: per-query position for system B (same order/length)

    Returns:
        Dict with the statistic, two-sided p-value, and number of non-tied pairs.
        p_value is None when every pair is tied (test undefined).
    """
    if len(a_positions) != len(b_positions):
        raise ValueError("paired sequences must be the same length")

    diffs = [a - b for a, b in zip(a_positions, b_positions)]
    non_tied = sum(1 for d in diffs if d != 0)

    if non_tied == 0:
        return {"statistic": None, "p_value": None, "non_tied_pairs": 0,
                "significant_at_0.05": False}

    stat, p_value = wilcoxon(a_positions, b_positions, zero_method="wilcox")
    return {
        "statistic": float(stat),
        "p_value": float(p_value),
        "non_tied_pairs": non_tied,
        "significant_at_0.05": bool(p_value < 0.05),
    }


def bootstrap_ci_mean(values: Sequence[float],
                      n_boot: int = 10000,
                      alpha: float = 0.05,
                      seed: int = 42) -> Dict:
    """Percentile bootstrap CI for the mean of a sample.

    Useful for the mean of paired deltas (e.g. per-query rank improvement),
    where the CI excluding 0 indicates a reliable effect.

    Args:
        values: sample (e.g. per-query deltas)
        n_boot: number of bootstrap resamples
        alpha: 1 - confidence level (0.05 -> 95% CI)
        seed: RNG seed for reproducibility

    Returns:
        Dict with point estimate (mean) and the lower/upper CI bounds.
    """
    values = list(values)
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}

    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()

    lo = means[int((alpha / 2) * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot)]
    point = sum(values) / n
    return {"mean": float(point), "ci_low": float(lo), "ci_high": float(hi), "n": n}


def paired_comparison(a_metrics: List[Dict],
                      b_metrics: List[Dict],
                      label_a: str = "A",
                      label_b: str = "B") -> Dict:
    """Full paired significance report comparing system B against system A.

    Expects per-query metric dicts with keys 'top_1', 'top_5', 'position'
    (as produced by ``src.evaluation.metrics.get_retrieval_metrics``).

    Args:
        a_metrics: per-query metrics for the reference system (e.g. baseline)
        b_metrics: per-query metrics for the system under test (e.g. PG)
        label_a, label_b: names for reporting

    Returns:
        Dict of significance tests for top-1, top-5, and position, plus a
        bootstrap CI on the mean position improvement (A_pos - B_pos).
    """
    if len(a_metrics) != len(b_metrics):
        raise ValueError("paired metric lists must be the same length")

    a1 = [bool(m["top_1"]) for m in a_metrics]
    b1 = [bool(m["top_1"]) for m in b_metrics]
    a5 = [bool(m["top_5"]) for m in a_metrics]
    b5 = [bool(m["top_5"]) for m in b_metrics]
    apos = [float(m["position"]) for m in a_metrics]
    bpos = [float(m["position"]) for m in b_metrics]

    # positive delta = B ranks the target higher (lower position number)
    pos_deltas = [a - b for a, b in zip(apos, bpos)]

    return {
        "comparison": f"{label_b} vs {label_a}",
        "n": len(a_metrics),
        "top_1_mcnemar": mcnemar_test(a1, b1),
        "top_5_mcnemar": mcnemar_test(a5, b5),
        "position_wilcoxon": wilcoxon_test(apos, bpos),
        "mean_position_improvement_ci": bootstrap_ci_mean(pos_deltas),
    }
