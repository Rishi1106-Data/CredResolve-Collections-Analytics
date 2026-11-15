"""Consistency check: every headline number quoted in the deliverables must match reports/headline_numbers.json,
and withdrawn wording must not reappear.  Run from repo root:  python src/check_consistency.py"""
import json, sys, re, os
H = json.load(open("reports/headline_numbers.json"))
f = lambda x, d=1: f"{x:.{d}f}"
MEMO, FIND, README, DASH = "reports/executive_memo.md", "reports/findings_report.md", "README.md", "dashboard/dashboard.html"
must = {  # file -> strings that must appear
    MEMO: [f"₹{f(H['feb_cr'],2)} Cr → ₹{f(H['mar_cr'],2)} Cr", f"+{f(H['total_change_pct'],2)}%", f"₹{f(H['feb_lakh_per_day'],2)} lakh to ₹{f(H['mar_lakh_per_day'],2)} lakh",
           f"−{abs(H['block_ci_lo']):.1f}% to +{H['block_ci_hi']:.1f}%", f"₹{H['jan_jul_cr']} Cr", f"{H['all_status_inflation_pct']}%", f"{H['dup_inflation_pct']}%",
           f"{H['n_arm_20']:,}", f"{H['n_arm_50']:,}", f"{H['cohort_baseline_pct']}%", f"{H['ptp_matured']:,}", f"{H['ptp_one_to_one_pct']}%", f"{H['ptp_upper_pct']}%",
           f"₹{H['annualised_cr']} Cr", f"{H['trend_pct_per_30d']}".replace("-", "−")],
    FIND: [f"₹{f(H['feb_cr'],2)} Cr → ₹{f(H['mar_cr'],2)} Cr", f"{H['n_arm_20']:,}", f"{H['n_arm_50']:,}", f"{H['cohort_baseline_pct']}%", f"{H['ptp_matured']:,}", f"{H['ptp_one_to_one_pct']}%",
           f"{H['ptp_upper_pct']}%", f"{H['ptp_full_amount_pct']}%", f"p={H['trend_hac_p']}", f"{H['den_hist_agree_pct']}%", f"{H['den_accts_over_outstanding_pct']}%", f"{H['ptp_recorded_kept_of_kept_broken_pct']}%"],
    README: [f"{H['n_arm_20']:,}", f"{H['cohort_baseline_pct']}%", f"{H['ptp_one_to_one_pct']}", f"{H['ptp_upper_pct']}%", f"{f(H['total_change_pct'],2)}%", f"{H['block_ci_hi']:+.1f}%"],
    DASH: [f"+{H['total_change_pct']:.1f}%", f"{H['per_day_change_pct']:+.1f}%", f"{H['n_arm_20']:,}", f"{H['ptp_one_to_one_pct']}–{H['ptp_upper_pct']}%"],
}
banned = {  # withdrawn wording / numbers
    "11,557": [MEMO, README, DASH, "reports/investment_recommendation.md", "reports/experiment_design.md"],
    "3.59%": [MEMO, README, DASH, "reports/experiment_design.md", "reports/investment_recommendation.md"],
    "flat": [MEMO, README, DASH, "reports/investment_recommendation.md"],
    "recovery rate %": [MEMO, README, DASH],
}
bad = []
for fn, items in must.items():
    t = open(fn, encoding="utf-8").read()
    for s in items:
        if s not in t: bad.append(f"{fn}: missing '{s}'")
for s, files in banned.items():
    for fn in files:
        if os.path.exists(fn) and re.search(r"(?<![A-Za-z])" + re.escape(s) + r"(?![A-Za-z])", open(fn, encoding="utf-8").read()): bad.append(f"{fn}: contains withdrawn text '{s}'")
nb = open("Analysis/Analysis.ipynb", encoding="utf-8").read()
for s in [f"{H['n_arm_20']:,}", f"{H['cohort_baseline_pct']}", "no statistically detectable"]:
    if s not in nb: bad.append(f"Analysis/Analysis.ipynb: missing '{s}'")
print("CONSISTENCY OK" if not bad else "INCONSISTENCIES:\n" + "\n".join(bad)); sys.exit(1 if bad else 0)
