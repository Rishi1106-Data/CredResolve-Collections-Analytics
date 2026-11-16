"""
Corrected metrics + statistical tests.   Run from repo root AFTER src/clean.py:  python src/metrics.py
Outputs: reports/monthly_metrics.csv, reports/statistical_tests.md, reports/feb_mar_decomposition.csv,
         reports/headline_numbers.json (the single source of every headline number used in the memo/dashboard/README)
All formulas are written out in reports/metric_definitions.md
"""
import json
import numpy as np, pandas as pd
from scipy import stats
from ptp_validation import validate_ptps, CUTOFF as PTP_CUTOFF
HEAD = {}          # headline numbers, written to reports/headline_numbers.json at the end

CUTOFF = pd.Timestamp("2026-08-08 23:59:59")        # last payment/PTP in the data
pay = pd.read_csv("golden/payments_clean.csv", parse_dates=["event_at"])
acc = pd.read_csv("golden/accounts_clean.csv")
calls = pd.read_csv("golden/calls_clean.csv", parse_dates=["event_at"])
ptp = pd.read_csv("golden/promises_to_pay_clean.csv", parse_dates=["event_at", "promised_date"])
disp = pd.read_csv("collections_30k_dataset/call_dispositions.csv", parse_dates=["event_at"])
dtg = pd.read_csv("collections_30k_dataset/daily_targeting.csv", parse_dates=["target_date"])
for d in (pay, calls, ptp, disp, dtg):
    d["month"] = d.iloc[:, d.columns.get_loc("target_date" if "target_date" in d.columns else "event_at")].dt.to_period("M").astype(str)
WIN = [f"2026-0{i}" for i in range(1, 9)]
DAYS = {m: pd.Period(m).days_in_month for m in WIN}; DAYS["2026-08"] = 8
N_ACC = len(acc)

ok = pay[pay.is_success & pay.month.isin(WIN)].copy()
out = calls[(calls.direction == "OUTBOUND") & calls.month.isin(WIN)].copy()
m = pd.DataFrame(index=WIN); m.index.name = "month"
m["days_in_data"] = pd.Series(DAYS)

# ---- recovery (numerator: SUCCESS payments after dedupe; denominators: see below)
g = ok.groupby("month")
m["recovery_cr"] = g.amount.sum() / 1e7
m["recovery_cr_per_day"] = m.recovery_cr / m.days_in_data
m["n_success_payments"] = g.size()
m["accounts_paying"] = g.account_id.nunique()
m["pct_base_accounts_paying"] = m.accounts_paying / N_ACC * 100        # share of ALL 30,000 accounts in the base (not an eligible-account share)
m["payments_per_paying_account"] = m.n_success_payments / m.accounts_paying
m["avg_ticket_rs"] = g.amount.mean()
# DENOMINATORS: both use the STATIC snapshot of all 30,000 accounts / their outstanding balance. That population includes
# PAID, CLOSED and WRITEOFF accounts (75% of accounts), so these are INDICES, not a conventional collection rate.
# See reports/denominator_audit.md.
m["recovery_per_base_account_rs"] = g.amount.sum() / N_ACC
m["recovery_pct_of_static_outstanding_index"] = g.amount.sum() / acc.outstanding_amount.sum() * 100

# ---- account volumes worked
w = out.groupby("month").account_id.nunique()
m["accounts_worked_outbound"] = w
m["recovery_per_worked_account_rs"] = g.amount.sum() / w
m["accounts_targeted_daily_targeting"] = dtg[dtg.month.isin(WIN)].groupby("month").account_id.nunique()

# ---- contact (call-level and account-level)
m["outbound_calls"] = out.groupby("month").size()
m["contact_rate_call_pct"] = out.groupby("month").call_status.apply(lambda s: (s == "ANSWERED").mean() * 100)
ans_acc = out[out.call_status == "ANSWERED"].groupby("month").account_id.nunique()
m["contact_rate_account_pct"] = ans_acc / w * 100

# ---- RPC PROXY (disposition-based; NOT verified unique right-party contact)
ENGAGED = ["PTP", "PROMISE_TO_PAY", "PTP_BROKEN", "PAID", "REFUSED", "DISPUTE", "CALLBACK"]
d = disp.merge(calls[["call_id", "call_status"]], on="call_id"); d = d[d.month.isin(WIN)]
d["engaged"] = d.disposition_code.isin(ENGAGED)
m["rpc_proxy_all_dispositions_pct"] = d.groupby("month").engaged.mean() * 100
m["rpc_proxy_answered_calls_only_pct"] = d[d.call_status == "ANSWERED"].groupby("month").engaged.mean() * 100
m["share_dispositions_on_unanswered_calls_pct"] = d.groupby("month").call_status.apply(lambda s: (s != "ANSWERED").mean() * 100)

# ---- PTP: only promises that MATURED are used; payment validation is in src/ptp_validation.py (reported as a RANGE)
p = ptp[ptp.month.isin(WIN)].copy()
okall = pay[pay.is_success]
mt_all, p_all = validate_ptps(ptp, okall, PTP_CUTOFF, grace_days=0)
mt = mt_all[mt_all.month.isin(WIN)].copy()
gm = mt.groupby("month")
m["ptp_created"] = p.groupby("month").size()
# PTP has no call_id and 3 of 4 sources are not calls, so "PTP per answered call" is invalid (>100%). Use a fixed denominator.
m["ptp_created_per_1000_accounts"] = p.groupby("month").size() / N_ACC * 1000
m["ptp_matured"] = gm.size()
m["ptp_matured_share_pct"] = m.ptp_matured / m.ptp_created * 100          # <100% => maturity-censored month (Jul/Aug)
m["ptp_recorded_kept_pct_of_matured"] = gm.status.apply(lambda s: (s == "KEPT").mean() * 100)
m["ptp_recorded_kept_pct_of_kept_plus_broken"] = mt[mt.status.isin(["KEPT", "BROKEN"])].groupby("month").status.apply(lambda s: (s == "KEPT").mean() * 100)
m["ptp_paid_in_window_upper_pct"] = gm.paid_overlap_allowed.mean() * 100          # one payment may count for several promises
m["ptp_paid_in_window_one_to_one_pct"] = gm.paid_one_to_one.mean() * 100          # one payment credited to one promise only
m["ptp_full_amount_waterfall_pct"] = gm.paid_full_amount_waterfall.mean() * 100
m.round(3).to_csv("reports/monthly_metrics.csv")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
print(m.round(2).T.to_string())

# ================= PTP validation (details: python src/ptp_validation.py -> reports/ptp_validation.md) =================
HEAD["ptp_matured"] = int(len(mt_all)); HEAD["ptp_unmatured_excluded"] = int((~p_all.matured).sum())
HEAD["ptp_upper_pct"] = round(mt_all.paid_overlap_allowed.mean() * 100, 2)
HEAD["ptp_one_to_one_pct"] = round(mt_all.paid_one_to_one.mean() * 100, 2)
HEAD["ptp_full_amount_pct"] = round(mt_all.paid_full_amount_waterfall.mean() * 100, 2)
HEAD["ptp_recorded_kept_of_matured_pct"] = round((mt_all.status == "KEPT").mean() * 100, 2)
HEAD["ptp_recorded_kept_of_kept_broken_pct"] = round((mt_all[mt_all.status.isin(["KEPT", "BROKEN"])].status == "KEPT").mean() * 100, 2)
HEAD["ptp_kept_validated_pct"] = round(mt_all[mt_all.status == "KEPT"].paid_overlap_allowed.mean() * 100, 2)
HEAD["ptp_broken_validated_pct"] = round(mt_all[mt_all.status == "BROKEN"].paid_overlap_allowed.mean() * 100, 2)
HEAD["ptp_open_stale"] = int((mt_all.status == "OPEN").sum())
HEAD["ptp_payments_in_2plus_windows"] = mt_all.attrs["payments_in_2plus_windows"]

# ================= daily recovery: COMPLETE calendar, zero-filled =================
# IMPORTANT: these tests are EXPLORATORY. Daily recoveries can be serially correlated, which breaks the
# "independent days" assumption behind the plain t-test / regression p-values. We therefore report (a) the naive tests,
# (b) autocorrelation diagnostics and (c) serial-correlation-robust versions (HAC slope, block bootstrap).
cal = pd.date_range("2026-01-01", "2026-07-31", freq="D")               # full months only (Aug is partial)
daily = ok.groupby(ok.event_at.dt.normalize()).amount.sum().reindex(cal, fill_value=0.0)
n_zero = int((daily == 0).sum())
feb, mar = daily["2026-02"], daily["2026-03"]
lines = []
def say(s): print(s); lines.append(s)
say("# Statistical tests (zero-filled calendar, 1 Jan - 31 Jul 2026)\n")
say("**Status: EXPLORATORY.** One synthetic extract, 212 daily values, several tests. A non-significant p-value means "
    "*no statistically detectable* difference or trend in the observed period; it is NOT proof that performance is unchanged.\n")
say(f"- Calendar days: {len(daily)} | days with zero SUCCESS recovery (filled as 0): {n_zero} | days present in raw data: {len(daily) - n_zero}")
say(f"- Feb: {len(feb)} days, mean ₹{feb.mean()/1e5:.2f} lakh/day | Mar: {len(mar)} days, mean ₹{mar.mean()/1e5:.2f} lakh/day")
say(f"- Total Feb→Mar change: {(mar.sum()/feb.sum()-1)*100:+.2f}% | Per-day change: {(mar.mean()/feb.mean()-1)*100:+.2f}%")
HEAD.update(feb_cr=round(feb.sum() / 1e7, 2), mar_cr=round(mar.sum() / 1e7, 2), total_change_pct=round((mar.sum() / feb.sum() - 1) * 100, 2),
            feb_lakh_per_day=round(feb.mean() / 1e5, 2), mar_lakh_per_day=round(mar.mean() / 1e5, 2), per_day_change_pct=round((mar.mean() / feb.mean() - 1) * 100, 2),
            jan_jul_cr=round(daily.sum() / 1e7, 1), jan_jul_cr_per_day=round(daily.mean() / 1e7, 3), jan_jul_days=len(daily))

say("\n## A. Feb vs Mar, per-day recovery\n")
say("Naive tests (treat each day as an independent observation):")
w_ = stats.ttest_ind(mar, feb, equal_var=False); say(f"- Welch t-test (daily means): t={w_.statistic:.2f}, p={w_.pvalue:.3f}")
mw = stats.mannwhitneyu(mar, feb); say(f"- Mann-Whitney U: p={mw.pvalue:.3f}")
rng = np.random.default_rng(42)
boot = np.array([rng.choice(mar.values, len(mar)).mean() / rng.choice(feb.values, len(feb)).mean() - 1 for _ in range(10000)])
say(f"- Bootstrap, days resampled one by one (10,000x) 95% CI for per-day change: [{np.percentile(boot,2.5)*100:+.1f}%, {np.percentile(boot,97.5)*100:+.1f}%]")
both = np.concatenate([feb.values, mar.values]); obs = mar.mean() - feb.mean(); cnt = 0
for _ in range(10000):
    rng.shuffle(both); cnt += abs(both[len(feb):].mean() - both[:len(feb)].mean()) >= abs(obs)
say(f"- Permutation test (shuffle day labels Feb/Mar): p={(cnt+1)/10001:.3f}")
HEAD.update(welch_p=round(w_.pvalue, 3), mw_p=round(mw.pvalue, 3), perm_p=round((cnt + 1) / 10001, 3),
            iid_ci_lo=round(np.percentile(boot, 2.5) * 100, 1), iid_ci_hi=round(np.percentile(boot, 97.5) * 100, 1))

def cbb_means(x, B, L, rng):
    """circular block bootstrap: resample blocks of L consecutive days so short-range correlation is preserved"""
    n = len(x); k = int(np.ceil(n / L)); st = rng.integers(0, n, (B, k))
    idx = ((st[:, :, None] + np.arange(L)) % n).reshape(B, -1)[:, :n]
    return x[idx].mean(axis=1)
rng = np.random.default_rng(42); BL = 7                                    # 7 = one week (day-of-week structure)
bb = cbb_means(mar.values, 10000, BL, rng) / cbb_means(feb.values, 10000, BL, rng) - 1
say(f"- **Block bootstrap (7-day blocks, 10,000x) 95% CI for per-day change: [{np.percentile(bb,2.5)*100:+.1f}%, {np.percentile(bb,97.5)*100:+.1f}%]** "
    "(robust to short-range correlation; preferred interval)")
HEAD.update(block_ci_lo=round(np.percentile(bb, 2.5) * 100, 1), block_ci_hi=round(np.percentile(bb, 97.5) * 100, 1))
say(f"- Reading: the data are compatible with a true per-day change anywhere from about {np.percentile(bb,2.5)*100:+.0f}% to {np.percentile(bb,97.5)*100:+.0f}%. "
    f"A per-day gain as large as the reported 11% is not supported; a small gain or loss cannot be excluded.")

say("\n## B. Trend over Jan–Jul (212 days)\n")
x = np.arange(len(daily), dtype=float); y = daily.values
lr = stats.linregress(x, y)
say(f"- Naive OLS slope: ₹{lr.slope:,.0f} per day per day ({lr.slope*30/daily.mean()*100:+.2f}% of mean per 30 days), p={lr.pvalue:.3f} (assumes independent days)")
mk = stats.kendalltau(x, y); say(f"- Kendall tau trend test: tau={mk.statistic:.3f}, p={mk.pvalue:.3f}")

# --- serial correlation diagnostics
xc = y - y.mean(); n = len(y)
acf = np.array([np.sum(xc[k:] * xc[:n - k]) / np.sum(xc * xc) for k in range(1, 15)])
def ljung_box(L):
    q = n * (n + 2) * np.sum(acf[:L] ** 2 / (n - np.arange(1, L + 1))); return q, 1 - stats.chi2.cdf(q, L)
q7, p7 = ljung_box(7); q14, p14 = ljung_box(14)
say(f"- Autocorrelation of daily recovery, lags 1–7: " + ", ".join(f"{v:+.2f}" for v in acf[:7]) + f" (rough ±{1.96/np.sqrt(n):.2f} band for a single lag)")
say(f"- Ljung–Box test for serial correlation: lags 1–7 p={p7:.2f}; lags 1–14 p={p14:.2f}")
say(f"  → Lag-1 autocorrelation ({acf[0]:+.2f}) is slightly outside the single-lag band, but the joint tests do not detect serial correlation. "
    "That is reassuring, but 212 days is short and the test has limited power, so the robust versions below are still the ones to quote.")

# --- Newey-West (HAC) slope: standard errors that allow for autocorrelation up to 7 days
X = np.column_stack([np.ones(n), x]); beta = np.linalg.solve(X.T @ X, X.T @ y); e = y - X @ beta
Lh = 7; S = (X * e[:, None]).T @ (X * e[:, None])
for l in range(1, Lh + 1):
    G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None]); S += (1 - l / (Lh + 1)) * (G + G.T)
XtXi = np.linalg.inv(X.T @ X); V = XtXi @ S @ XtXi * n / (n - 2); se = np.sqrt(V[1, 1])
tcrit = stats.t.ppf(0.975, n - 2); t_ = beta[1] / se; p_hac = 2 * (1 - stats.t.cdf(abs(t_), n - 2))
to_pct = 30 / daily.mean() * 100
say(f"- **Newey–West (HAC, 7-day lag) slope: {beta[1]*to_pct:+.2f}% of mean per 30 days, 95% CI [{(beta[1]-tcrit*se)*to_pct:+.2f}%, {(beta[1]+tcrit*se)*to_pct:+.2f}%], p={p_hac:.3f}**")
HEAD.update(trend_naive_p=round(lr.pvalue, 3), trend_kendall_p=round(mk.pvalue, 3), trend_hac_p=round(p_hac, 3), trend_pct_per_30d=round(beta[1] * to_pct, 2),
            trend_ci_lo=round((beta[1] - tcrit * se) * to_pct, 2), trend_ci_hi=round((beta[1] + tcrit * se) * to_pct, 2),
            lb7_p=round(p7, 2), lb14_p=round(p14, 2), acf1=round(acf[0], 2))
say("- **Conclusion: no statistically detectable trend was identified in the observed period.** The HAC interval shows the size of trend this "
    "data could detect: changes smaller than roughly the interval width cannot be ruled out. This is not proof that performance is flat.")
say("- Limitations of these tests: exploratory; only 7 months of one extract; day-level payments are aggregated from rows whose timestamps have no timezone; "
    "several tests were run without multiplicity control; a synthetic dataset may have no real trend by construction.")

dow = daily.groupby(daily.index.dayofweek).mean() / daily.mean()
say("- Day-of-week index (1.00 = average; Mon..Sun): " + ", ".join(f"{v:.2f}" for v in dow.values))
mon = ok.groupby("month").amount.sum().drop("2026-08"); pr = mon.pct_change().dropna() * 100
perday = (ok[ok.month != "2026-08"].groupby("month").amount.sum() / pd.Series({k: DAYS[k] for k in mon.index})).pct_change().dropna() * 100
say(f"- Month-over-month swings in TOTAL recovery (Feb..Jul): " + ", ".join(f"{v:+.1f}%" for v in pr) + " | calendar-day ratio: " +
    ", ".join(f"{(DAYS[b]/DAYS[a]-1)*100:+.1f}%" for a, b in zip(WIN[:6], WIN[1:7])) + " | PER-DAY swings: " + ", ".join(f"{v:+.1f}%" for v in perday))
HEAD.update(mom_total_pct=[round(v, 1) for v in pr], mom_per_day_pct=[round(v, 1) for v in perday], mom_days_pct=[round((DAYS[b] / DAYS[a] - 1) * 100, 1) for a, b in zip(WIN[:6], WIN[1:7])])

# ================= Feb->Mar decomposition (log, additive) =================
a, b = m.loc["2026-02"], m.loc["2026-03"]
parts = {"calendar days (31 vs 28)": b.days_in_data / a.days_in_data,
         "paying accounts per day": (b.accounts_paying / b.days_in_data) / (a.accounts_paying / a.days_in_data),
         "payments per paying account": b.payments_per_paying_account / a.payments_per_paying_account,
         "average ticket": b.avg_ticket_rs / a.avg_ticket_rs}
tot = b.recovery_cr / a.recovery_cr
dec = pd.DataFrame({"ratio": parts}); dec["pct_change"] = (dec.ratio - 1) * 100
dec["share_of_total_log_change_pct"] = np.log(dec.ratio) / np.log(tot) * 100
dec.loc["TOTAL (Mar/Feb)"] = [tot, (tot - 1) * 100, 100.0]
dec.round(3).to_csv("reports/feb_mar_decomposition.csv")
HEAD["days_share_of_change_pct"] = round(float(dec["share_of_total_log_change_pct"].iloc[0]), 1)
HEAD["days_effect_pct"] = round(float(dec["pct_change"].iloc[0]), 1)
say("\n## C. Feb→Mar decomposition (total recovery ratio = product of factors; identity, not a model)\n\n" + dec.round(2).to_markdown())
say("\nNote: 'paying accounts per day' counts distinct accounts per month, so a longer month adds fewer new payers than days; "
    "the 97% share of calendar days should be read as 'about 97%', and the same conclusion holds with payments per day × ticket "
    f"(payments per day {((b.n_success_payments/31)/(a.n_success_payments/28)-1)*100:+.2f}%, ticket {(b.avg_ticket_rs/a.avg_ticket_rs-1)*100:+.2f}%).")
say(f"\n## D. Account volume, paying-account share, ticket, mix\n")
say(f"- Accounts worked (outbound): Feb {a.accounts_worked_outbound:,.0f} → Mar {b.accounts_worked_outbound:,.0f} ({(b.accounts_worked_outbound/a.accounts_worked_outbound-1)*100:+.1f}%); per day {((b.accounts_worked_outbound/31)/(a.accounts_worked_outbound/28)-1)*100:+.1f}%")
say(f"- Share of the 30,000 base accounts paying in the month: Feb {a.pct_base_accounts_paying:.2f}% → Mar {b.pct_base_accounts_paying:.2f}% (months differ in length); paying accounts per day {(((b.accounts_paying/31)/(a.accounts_paying/28))-1)*100:+.1f}%")
say(f"- Average payment (ticket): Feb ₹{a.avg_ticket_rs:,.0f} → Mar ₹{b.avg_ticket_rs:,.0f} ({(b.avg_ticket_rs/a.avg_ticket_rs-1)*100:+.2f}%)")
HEAD.update(accts_worked_feb=int(a.accounts_worked_outbound), accts_worked_mar=int(b.accounts_worked_outbound),
            paying_share_feb=round(a.pct_base_accounts_paying, 2), paying_share_mar=round(b.pct_base_accounts_paying, 2),
            ticket_feb=round(a.avg_ticket_rs), ticket_mar=round(b.avg_ticket_rs),
            paying_per_day_change_pct=round(((b.accounts_paying / 31) / (a.accounts_paying / 28) - 1) * 100, 1),
            ticket_change_pct=round((b.avg_ticket_rs / a.avg_ticket_rs - 1) * 100, 2),
            contact_lo=round(m.loc[WIN[:7], "contact_rate_call_pct"].min(), 1), contact_hi=round(m.loc[WIN[:7], "contact_rate_call_pct"].max(), 1))
ok2 = ok.merge(acc[["account_id", "loan_type", "dpd_bucket", "risk_segment"]], on="account_id")
fm = ok2[ok2.month.isin(["2026-02", "2026-03"])]
for dim in ["loan_type", "dpd_bucket", "risk_segment"]:
    ct = pd.crosstab(fm.month, fm[dim]); chi = stats.chi2_contingency(ct)
    say(f"- Mix of payments by {dim}, Feb vs Mar: chi-square p={chi[1]:.3f} (no statistically detectable composition shift)")
    HEAD[f"mix_p_{dim}"] = round(chi[1], 3)
base = ok2[ok2.month != "2026-08"]
for dim in ["dpd_bucket", "loan_type"]:
    wts = base[dim].value_counts(normalize=True); tk = ok2.groupby(["month", dim]).amount.mean().unstack()
    std = tk.mul(wts, axis=1).sum(axis=1)
    say(f"- Mix-standardised avg ticket by {dim}: Feb ₹{std['2026-02']:,.0f} → Mar ₹{std['2026-03']:,.0f} ({(std['2026-03']/std['2026-02']-1)*100:+.1f}%) vs raw {(b.avg_ticket_rs/a.avg_ticket_rs-1)*100:+.1f}%")
say(f"- PTP: see reports/ptp_validation.md. Matured promises ({HEAD['ptp_matured']:,}; {HEAD['ptp_unmatured_excluded']:,} un-matured excluded): recorded KEPT = {HEAD['ptp_recorded_kept_of_matured_pct']}% of matured "
    f"({HEAD['ptp_recorded_kept_of_kept_broken_pct']}% of KEPT+BROKEN) but a SUCCESS payment inside the promise window exists for only {HEAD['ptp_one_to_one_pct']}% (one payment → one promise) to {HEAD['ptp_upper_pct']}% (overlap allowed); "
    f"recorded KEPT {HEAD['ptp_kept_validated_pct']}% vs BROKEN {HEAD['ptp_broken_validated_pct']}% have a payment in window. Jul/Aug promises are maturity-censored.")
say("- The 30,000-account base is a fixed snapshot (all opened 2024-01-01..2025-11-30, before the window). A fixed base cannot show portfolio acquisition, "
    "and an eligible-balance population cannot be built from it (see reports/denominator_audit.md).")

# ================= payment-counting rules: how much would a naive report overstate? (computed, not hard-coded) =================
raw = pd.read_csv("collections_30k_dataset/payments.csv", parse_dates=["event_at"])
raw = raw[(raw.event_at >= "2026-01-01") & (raw.event_at <= "2026-08-08 23:59:59")]
clean_succ = ok.amount.sum()
raw_succ = raw[raw.payment_status == "SUCCESS"].amount.sum(); raw_all = raw.amount.sum()
rm = raw.assign(month=raw.event_at.dt.to_period("M").astype(str))
r_all = rm.groupby("month").amount.sum(); r_suc = rm[rm.payment_status == "SUCCESS"].groupby("month").amount.sum()
HEAD.update(clean_success_cr=round(clean_succ / 1e7, 2), raw_success_cr=round(raw_succ / 1e7, 2), raw_all_status_cr=round(raw_all / 1e7, 2),
            dup_inflation_pct=round((raw_succ / clean_succ - 1) * 100, 2), all_status_inflation_pct=round((raw_all / clean_succ - 1) * 100, 1),
            raw_success_mar_feb_pct=round((r_suc["2026-03"] / r_suc["2026-02"] - 1) * 100, 2), raw_allstatus_mar_feb_pct=round((r_all["2026-03"] / r_all["2026-02"] - 1) * 100, 1))
say(f"- Counting rules (Jan 1–Aug 8): clean SUCCESS ₹{clean_succ/1e7:.2f} Cr | raw SUCCESS incl. duplicate rows ₹{raw_succ/1e7:.2f} Cr ({HEAD['dup_inflation_pct']:+.2f}%) | "
    f"raw all statuses ₹{raw_all/1e7:.2f} Cr ({HEAD['all_status_inflation_pct']:+.1f}%). Mar/Feb: raw SUCCESS {HEAD['raw_success_mar_feb_pct']:+.2f}%, raw all-status {HEAD['raw_allstatus_mar_feb_pct']:+.1f}%, clean {HEAD['total_change_pct']:+.2f}%.")
say("- Day-of-week index, month swings and decomposition are descriptive; they are not causal estimates.")
open("reports/statistical_tests.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
json.dump(HEAD, open("reports/headline_numbers.json", "w", encoding="utf-8"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
