"""
Checks the calculations against published and hand-calculated figures.
Run with:  python3 test_metrics.py
"""

from metrics import (
    calc_metrics,
    match_headline,
    parse_percent,
    rates_from_counts,
    round_to_total,
    wilson_ci,
)


def close(a, b, tol=0.005):
    return abs(a - b) <= tol


# UCL brain tumour MRI study (Ruffle et al., 2026):
# sensitivity 91.5%, specificity 74.4%, 89.4% of test cases enhancing
ucl = calc_metrics(0.915, 0.744, 0.894)
assert close(ucl["bal"], 0.830), ucl["bal"]   # paper: balanced accuracy 83.0%
assert close(ucl["npv"], 0.51), ucl["npv"]    # paper: NPV 0.51
assert close(ucl["ppv"], 0.968), ucl["ppv"]
assert close(ucl["acc"], 0.897), ucl["acc"]

# Authors' estimate: NPV about 0.95 at around 30% prevalence
low = calc_metrics(0.915, 0.744, 0.30)
assert close(low["npv"], 0.953), low["npv"]
assert close(low["ppv"], 0.605), low["ppv"]

# The four shares always add up to 1
assert close(ucl["tp"] + ucl["fn"] + ucl["tn"] + ucl["fp"], 1.0, 1e-9)

# The 100-patient picture always has exactly 100 squares
counts = round_to_total([ucl["tp"], ucl["fn"], ucl["tn"], ucl["fp"]])
assert sum(counts) == 100, counts

# Wilson intervals for the subgroup examples
lo, hi = wilson_ci(9, 20)       # children
assert close(lo, 0.258) and close(hi, 0.658), (lo, hi)
lo, hi = wilson_ci(93, 100)     # meningioma
assert close(lo, 0.862) and close(hi, 0.966), (lo, hi)
lo, hi = wilson_ci(0, 10)       # edge case: never goes below 0
assert lo == 0.0 and hi < 0.35, (lo, hi)

# Headline check: "83%" matches balanced accuracy, not accuracy
matches = [name for name, _ in match_headline(0.83, ucl)]
assert matches == ["balanced accuracy"], matches

# Reading what users type
assert parse_percent("83") == 0.83
assert parse_percent("83%") == 0.83
assert parse_percent("0.83") == 0.83
assert parse_percent("") is None
assert parse_percent("abc") is None

# Counts -> rates
se, sp, prev = rates_from_counts(tp=90, fp=10, tn=90, fn=10)
assert close(se, 0.9) and close(sp, 0.9) and close(prev, 0.5)
assert rates_from_counts(0, 5, 5, 0) is None

print("All checks passed.")
print(f"UCL study: PPV {ucl['ppv']:.1%}, NPV {ucl['npv']:.1%}, "
      f"accuracy {ucl['acc']:.1%}, balanced accuracy {ucl['bal']:.1%}")
print(f"At 30% prevalence: PPV {low['ppv']:.1%}, NPV {low['npv']:.1%}")
print(f"100 patients (TP, FN, TN, FP): {counts}")
