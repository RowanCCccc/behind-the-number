"""
Calculation functions for Behind the Number.

Everything here is plain Python (no Streamlit), so it can be tested on its own:
    python3 test_metrics.py

Notation
    se   = sensitivity  (share of true positives the AI finds)
    sp   = specificity  (share of true negatives the AI finds)
    prev = prevalence   (share of people in the group who are truly positive)
All three are proportions between 0 and 1.
"""

from math import floor, isnan, sqrt
from typing import Dict, List, Optional, Tuple

Z_95 = 1.959963984540054  # z value for a 95% confidence interval


def safe_div(a: float, b: float) -> float:
    """Divide, returning NaN instead of crashing when b is 0."""
    return a / b if b > 0 else float("nan")


def calc_metrics(se: float, sp: float, prev: float) -> Dict[str, float]:
    """
    Turn sensitivity, specificity and prevalence into the numbers readers need.

    tp, fn, tn, fp are shares of the whole group (they add up to 1),
    so multiplying by 100 gives "out of 100 patients".
    """
    tp = se * prev               # truly positive, AI says positive
    fn = (1 - se) * prev         # truly positive, AI says negative (missed)
    tn = sp * (1 - prev)         # truly negative, AI says negative
    fp = (1 - sp) * (1 - prev)   # truly negative, AI says positive (false alarm)

    return {
        "tp": tp,
        "fn": fn,
        "tn": tn,
        "fp": fp,
        "se": se,
        "sp": sp,
        "prev": prev,
        "ppv": safe_div(tp, tp + fp),   # AI says positive -> how often right
        "npv": safe_div(tn, tn + fn),   # AI says negative -> how often right
        "acc": tp + tn,                 # share of all answers that are right
        "bal": (se + sp) / 2,           # average of sensitivity and specificity
    }


def rates_from_counts(tp: int, fp: int, tn: int, fn: int) -> Optional[Tuple[float, float, float]]:
    """Convert the four counts of a confusion matrix into (se, sp, prev)."""
    positives = tp + fn
    negatives = tn + fp
    if positives == 0 or negatives == 0:
        return None
    return tp / positives, tn / negatives, positives / (positives + negatives)


def prevalence_curve(se: float, sp: float, steps: int = 199) -> Tuple[List[float], List[float], List[float]]:
    """PPV and NPV across prevalence values from 0.5% to 99.5%."""
    xs, ppvs, npvs = [], [], []
    for i in range(1, steps + 1):
        prev = i / (steps + 1)
        m = calc_metrics(se, sp, prev)
        xs.append(prev)
        ppvs.append(m["ppv"])
        npvs.append(m["npv"])
    return xs, ppvs, npvs


def round_to_total(values: List[float], total: int = 100) -> List[int]:
    """
    Round shares (that add up to 1) into whole numbers that add up to `total`.
    Uses the largest remainder method, so the 100-patient picture always has 100 squares.
    """
    raw = [v * total for v in values]
    rounded = [int(floor(x)) for x in raw]
    left = total - sum(rounded)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - rounded[i], reverse=True)
    for i in order[:left]:
        rounded[i] += 1
    return rounded


def wilson_ci(k: int, n: int, z: float = Z_95) -> Tuple[float, float]:
    """
    95% Wilson score confidence interval for k successes out of n.
    More reliable than the simple (Wald) formula when n is small
    or the rate is close to 0% or 100%.
    """
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def parse_percent(text: str) -> Optional[float]:
    """Read '83', '83%' or '0.83' as 0.83. Returns None if empty or invalid."""
    cleaned = (text or "").replace("%", "").strip()
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if value > 1:
        value = value / 100
    if value < 0 or value > 1:
        return None
    return value


METRIC_NAMES = {
    "acc": "accuracy",
    "bal": "balanced accuracy",
    "se": "sensitivity",
    "sp": "specificity",
    "ppv": "PPV",
    "npv": "NPV",
}


def match_headline(value: float, metrics: Dict[str, float], tolerance: float = 0.01) -> List[Tuple[str, float]]:
    """
    Which measures match a headline number (within 1 percentage point)?
    Returns (measure name, measure value) pairs, closest first.
    """
    matches = []
    for key, name in METRIC_NAMES.items():
        v = metrics[key]
        if not isnan(v) and abs(v - value) <= tolerance:
            matches.append((name, v))
    matches.sort(key=lambda pair: abs(pair[1] - value))
    return matches
