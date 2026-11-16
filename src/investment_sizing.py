"""
Facts + clearly-labelled scenarios for the Rs 10 Cr question, and the sizing of a controlled experiment.
NO costs, margins or uplifts are invented: every number is either measured from the data or is a parameter
that is printed as a hypothetical sensitivity.
Run from repo root AFTER metrics.py:  python src/investment_sizing.py
Writes: reports/investment_sizing.md, reports/experiment_design.md, reports/investment_recommendation.md
"""
import json
import numpy as np, pandas as pd
from scipy import stats

H = json.load(open("reports/headline_numbers.json"))
m = pd.read_csv("reports/monthly_metrics.csv", index_col="month")
full = m.drop("2026-08")                                    # Jan-Jul, 212 days
rec_cr = full.recovery_cr.sum(); per_day = rec_cr / full.days_in_data.sum(); annual = per_day * 365

# ---------------------------------------------------------------------------------------------------------------
# 1. BASELINE ON A UNIQUE-ACCOUNT COHORT  (the old 3.59% used daily_targeting ROWS, which repeat accounts)
# ---------------------------------------------------------------------------------------------------------------
OBS_END = pd.Timestamp("2026-08-09")                         # first instant AFTER the last payment day (8 Aug)
WINDOW = 14                                                  # days
dtg = pd.read_csv("collections_30k_dataset/daily_targeting.csv", parse_dates=["target_date"])
pay = pd.read_csv("golden/payments_clean.csv", parse_dates=["event_at"]); ok = pay[pay.is_success][["account_id", "event_at"]]

n_rows, n_accts = len(dtg), dtg.account_id.nunique()
rows_per_acct = dtg.groupby("account_id").size()
# cohort: one row per account = its FIRST targeting date (index date)
first = dtg.sort_values(["target_date", "target_id"]).groupby("account_id").first().reset_index()
# keep only accounts whose full 14-day window is observable (otherwise recent accounts look artificially unsuccessful)
cohort = first[first.target_date + pd.Timedelta(days=WINDOW) <= OBS_END].copy()
t = cohort[["account_id", "target_date"]].merge(ok, on="account_id", how="left")
t["hit"] = (t.event_at >= t.target_date) & (t.event_at < t.target_date + pd.Timedelta(days=WINDOW))
cohort["paid14"] = cohort.account_id.map(t.groupby("account_id").hit.max()).astype(bool)
n_c = len(cohort); k = int(cohort.paid14.sum()); base = k / n_c
z = stats.norm.ppf(0.975); wil = (base + z**2 / (2 * n_c) + np.array([-1, 1]) * z * np.sqrt(base * (1 - base) / n_c + z**2 / (4 * n_c**2))) / (1 + z**2 / n_c)
# the OLD (row-level) number, for reconciliation
tt = dtg.merge(ok, on="account_id", how="left"); tt["hit"] = (tt.event_at >= tt.target_date) & (tt.event_at <= tt.target_date + pd.Timedelta(days=14))
old_row_rate = tt.groupby("target_id").hit.max().mean()
by_month = cohort.groupby(cohort.target_date.dt.to_period("M").astype(str)).paid14.agg(["mean", "size"])
by_chan = cohort.groupby("recommended_channel").paid14.agg(["mean", "size"])

def n_per_arm(p1, rel, alpha=0.05, power=0.8):
    p2 = p1 * (1 + rel); za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return (za + zb) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2

POOL = len(pd.read_csv("golden/accounts_clean.csv"))
LIFTS = [0.10, 0.20, 0.50]
size = {(b, r): int(np.ceil(n_per_arm(b, r))) for b in (wil[0], base, wil[1]) for r in LIFTS}
H.update(cohort_accounts_all=int(n_accts), cohort_accounts_observable=int(n_c), cohort_baseline_pct=round(base * 100, 2),
         cohort_ci_lo=round(wil[0] * 100, 2), cohort_ci_hi=round(wil[1] * 100, 2), old_row_baseline_pct=round(old_row_rate * 100, 2),
         n_arm_10=size[(base, .10)], n_arm_20=size[(base, .20)], n_arm_50=size[(base, .50)],
         n_arm_20_lo=size[(wil[1], .20)], n_arm_20_hi=size[(wil[0], .20)], pool_accounts=POOL,
         annualised_cr=round(annual), run_rate_cr_per_day=round(per_day, 3))
json.dump(H, open("reports/headline_numbers.json", "w", encoding="utf-8"), indent=1)

# ---------------------------------------------------------------------------------------------------------------
# reports/investment_sizing.md   (measured facts + labelled arithmetic + experiment sizing)
# ---------------------------------------------------------------------------------------------------------------
L = ["# Investment sizing (measured facts + clearly labelled hypotheticals)\n",
     "## Measured facts\n",
     f"- Jan–Jul 2026 SUCCESS recovery = ₹{rec_cr:.1f} Cr over {int(full.days_in_data.sum())} days = ₹{per_day:.3f} Cr/day.",
     f"- Annualised run-rate (× 365) = ₹{annual:.0f} Cr. This is an **extrapolation** from 7 months; it assumes no seasonality and a constant book.",
     "- No table in the dataset holds agent salaries, telephony, WhatsApp/SMS, AI-voice or field costs, or the company's share (commission) of recovered rupees. **Cost per ₹ recovered and ROI cannot be measured.**\n",
     "## Break-even arithmetic (HYPOTHETICAL parameter c)\n",
     "Spending ₹10 Cr breaks even when `incremental recovery × c = ₹10 Cr`, where **c = the share of recovered rupees the company keeps / is worth to it**. c is NOT in the data; the rows below are sensitivities, not estimates. One-off spend, 12-month horizon, no discounting.\n",
     "| assumed c | incremental recovery needed (₹ Cr) | needed uplift on annualised run-rate |", "|---:|---:|---:|"]
for c in [1.0, 0.5, 0.25, 0.10]:
    L.append(f"| {c:.0%} | {10/c:.0f} | {10/c/annual*100:.1f}% |")
L += ["\n### Hypothetical net-benefit grid (₹ Cr) = uplift × run-rate × c − 10\n",
      "*Illustration of how sensitive the decision is. The uplift values are NOT forecasts: no uplift has been measured for any of the six options.*\n",
      "| hypothetical uplift on run-rate | c = 100% | c = 50% | c = 25% | c = 10% |", "|---:|---:|---:|---:|---:|"]
for u in [0.0, 0.02, 0.05, 0.10, 0.20]:
    L.append(f"| {u:.0%} | " + " | ".join(f"{u*annual*c-10:+.1f}" for c in (1.0, 0.5, 0.25, 0.10)) + " |")
L.append("\nReading: at c = 10–25% even a +10% uplift would not repay ₹10 Cr; at c = 100% a +5% uplift would. Because c and the uplift are both unknown, the sign of the return is unknown.")

L += ["\n## Experiment sizing on a UNIQUE-ACCOUNT cohort\n",
      "**Correction.** The earlier calculation used the share of `daily_targeting` **rows** followed by a payment (3.59%). "
      f"That table has {n_rows:,} rows but only {n_accts:,} distinct accounts (up to {int(rows_per_acct.max())} rows per account, mean {rows_per_acct.mean():.2f}), so rows are not independent units and the "
      "resulting '11,557 per arm' must not be read as a requirement in unique accounts. It is replaced by the cohort below.\n",
      "**Cohort definition.** One row per account: the account's FIRST `daily_targeting` date is its index date. "
      f"Outcome = at least one de-duplicated SUCCESS payment in the {WINDOW} days from the index date (index date ≤ payment < index date + {WINDOW} days). "
      f"Only accounts whose full {WINDOW}-day window ends by 8 Aug 2026 are kept (index date ≤ 26 Jul), so late accounts are not under-counted.\n",
      f"- Distinct targeted accounts: {n_accts:,}; with a fully observable window: **{n_c:,}**",
      f"- Baseline 14-day payment rate: **{base*100:.2f}%** ({k:,} of {n_c:,} accounts); Wilson 95% CI {wil[0]*100:.2f}%–{wil[1]*100:.2f}%",
      f"- Reconciliation: the old row-level figure was {old_row_rate*100:.2f}% (repeated accounts, window ≤14 days inclusive). The unique-account baseline differs slightly and is the one to use.",
      "- Baseline by index month: " + "; ".join(f"{i} {r['mean']*100:.2f}% (n={int(r['size']):,})" for i, r in by_month.iterrows()),
      "- Baseline by recommended channel: " + "; ".join(f"{i} {r['mean']*100:.2f}% (n={int(r['size']):,})" for i, r in by_chan.iterrows()) + " – no clear difference between channels in this observational data.\n",
      "### Accounts needed per arm (unit = unique account; 80% power; 5% two-sided; 2-arm comparison of proportions)\n",
      "| relative lift to detect | absolute lift (at baseline) | accounts PER ARM (baseline) | if baseline is at CI upper | if baseline is at CI lower |", "|---:|---:|---:|---:|---:|"]
for r in LIFTS:
    L.append(f"| {r:.0%} | {base*r*100:.2f} pp | {size[(base,r)]:,} | {size[(wil[1],r)]:,} | {size[(wil[0],r)]:,} |")
L += ["",
      f"**Feasibility.** The book has {POOL:,} accounts. A 2-arm test needs 2 × n accounts: {2*size[(base,.5)]:,} for a +50% relative lift ({2*size[(base,.5)]/POOL*100:.0f}% of the book), "
      f"{2*size[(base,.2)]:,} for +20% ({2*size[(base,.2)]/POOL*100:.0f}%), {2*size[(base,.1)]:,} for +10% ({2*size[(base,.1)]/POOL*100:.0f}% – larger than the book). "
      f"A 3-arm test at +20% needs {3*size[(base,.2)]:,} ({3*size[(base,.2)]/POOL*100:.0f}%) and would not fit in one cycle. "
      "These figures assume that every account in the book is eligible and reachable, which cannot be verified today (see reports/denominator_audit.md); the real eligible pool will be smaller, so the detectable lift will be larger.",
      "",
      "**What the baseline is and is not.** It is an *observational* rate for accounts that were targeted, measured on this extract. It is used only to size a future randomised test; "
      "it does not measure the effect of targeting. The first-target cohort contains accounts that may also have been called, messaged or visited in the same 14 days."]
open("reports/investment_sizing.md", "w", encoding="utf-8").write("\n".join(L) + "\n")

# ---------------------------------------------------------------------------------------------------------------
# reports/experiment_design.md
# ---------------------------------------------------------------------------------------------------------------
n20, n50 = size[(base, .2)], size[(base, .5)]
D = f"""# Controlled experiment design (to establish incremental recovery before spending ₹10 Cr)

**Purpose.** Measure the *incremental* recovery caused by ONE candidate intervention (for example a new targeting rule, a WhatsApp sequence, an AI-voice script or more agent capacity on a defined segment). The current data cannot do this: payments carry no campaign or channel link and there is no assignment log.

| Element | Design |
|---|---|
| **Treatment group** | Accounts randomly assigned to receive the candidate intervention (one intervention per test; a second intervention needs its own arm and a larger sample). |
| **Control group** | Accounts randomly assigned to business-as-usual treatment, run at the same time on the same book. No new intervention; existing calling/messaging continues. |
| **Randomisation unit** | The **unique account** (or the unique borrower once borrower IDs are resolved, so that one person's accounts are not split across arms). Randomise once, stratified by DPD bucket, loan type, risk segment and outstanding-balance band. Assignment is stored in an assignment table and never changed. |
| **Index date** | The first date the account becomes eligible for the test (the same idea as the 'first targeting date' used for the baseline). |
| **Primary outcome** | Binary: at least one de-duplicated payment with `payment_status = 'SUCCESS'` within **14 days** of the index date (index date ≤ payment < index date + 14 days). Analysed by assigned arm (intention-to-treat). |
| **Secondary outcomes** | SUCCESS rupees per assigned account at 14 and 30 days (heavy-tailed: bootstrap CI); payment at 30/60 days (to detect pull-forward rather than extra recovery); contact rate; validated PTP rate (see `reports/ptp_validation.md`); complaints, disputes and payment reversals as guardrails. |
| **Observation window** | 14 days primary, 30 days secondary, 60 days for pull-forward check. Every account must be followed for the full window: accounts whose window would run past the data cut-off are excluded from that analysis. |
| **Exclusion rules** | Accounts with an open high-severity complaint or dispute; accounts already inside a live promise-to-pay window at the index date (or stratify on it); accounts with unresolved duplicate/conflicting identifiers; accounts with no reachable channel for the tested intervention; accounts confirmed settled or written off **as of the index date** by a validated source (not possible today: `accounts.status` and `account_status_history` disagree, see denominator audit). |
| **Sample size** | Unique accounts per arm at 80% power, 5% two-sided, baseline {base*100:.2f}% (CI {wil[0]*100:.2f}–{wil[1]*100:.2f}%): **{size[(base,.5)]:,}** to detect +50% relative; **{n20:,}** for +20%; {size[(base,.1)]:,} for +10%. A 2-arm test at +20% needs {2*n20:,} of {POOL:,} accounts ({2*n20/POOL*100:.0f}% of the book) **if all are eligible**. Add ~5–10% for exclusions/attrition. |
| **Analysis** | Difference in 14-day payment proportions with a 95% CI; stratified (Cochran–Mantel–Haenszel or regression with strata) as a robustness check. Pre-register the primary outcome, the decision threshold and the stopping time. Check sample-ratio mismatch and baseline balance. |
| **Decision rule** | Release the remaining budget only if the lower bound of the incremental recovery per account, multiplied by the company's keep rate **c**, exceeds the incremental cost per account. Both **c** and costs must be supplied by finance. |

**Potential confounders / threats.** Randomisation removes baseline confounding (DPD, mix, month length, seasonality) *if it is carried out properly*; it does not remove: contamination (an account treated by an agent who also works control accounts; two accounts of one borrower in different arms), non-compliance (accounts assigned to treatment that were never reached), concurrent campaigns, vendor outages, payment-posting delays, and agent capacity changes during the test. Treat these with intention-to-treat analysis, shared-agent balancing and an event log.

**Limitations.**
1. The sample-size baseline is observational (accounts that were targeted), not a clean untreated rate.
2. A binary 14-day outcome ignores rupee size and timing; rupee outcomes need more accounts because payment sizes vary widely.
3. The pool of eligible accounts is unknown (denominator problem), so the real power may be lower.
4. Borrower and agent identifiers are unreliable in the extract; the production test must fix identity first.
5. Effects on complaints and long-run relationships are not captured in 14 days.
6. The dataset is synthetic; the baseline here illustrates the method and must be re-estimated on production data.
"""
open("reports/experiment_design.md", "w", encoding="utf-8").write(D)

# ---------------------------------------------------------------------------------------------------------------
# reports/investment_recommendation.md
# ---------------------------------------------------------------------------------------------------------------
R = f"""# ₹10 Cr investment: what the evidence supports

## Bottom line
**The data does not support committing ₹10 Cr to any single option, and no reliable ROI can be calculated.** We therefore give a *conditional* recommendation, scenario arithmetic (labelled hypothetical) and a test that would settle the question.

## Why a financial ROI cannot be calculated
1. **No cost data.** There are no agent salary, telephony/vendor, WhatsApp/SMS, AI-voice or field-visit cost fields, and no commission/keep rate on recovered money.
2. **No incremental-effect estimate.** Payments carry no campaign, channel or interaction ID. 'Last call before payment' attribution performs no better than a placebo (calls after the payment), so recovery cannot be assigned to a channel.
3. **No measured difference between options in the screens we could run** (correlational only; see `reports/driver_screen.csv`): contact rate by vendor/channel/strategy/hour band; 14-day payment rate by recommended channel and by target status ({by_chan['mean'].min()*100:.1f}–{by_chan['mean'].max()*100:.1f}% by channel); payment rate after WhatsApp, SMS and field events, which is ≈3.3–4.2% whatever the event type or recorded outcome (even a field visit recorded as 'PAID').
4. **Baseline has not moved.** Per-day recovery shows no statistically detectable trend in Jan–Jul (HAC p={H['trend_hac_p']}), so there is no observed improvement to attribute to any past investment.
5. The dataset is synthetic and almost uniform; the lack of effects may reflect how it was generated rather than the business.

## The six options against the evidence

| Option | What the data shows | Evidence | What is missing |
|---|---|---|---|
| 1. Better telephony | Contact rate {H['contact_lo']}–{H['contact_hi']}% every month; vendor differences borderline (p=0.050, 19.5–20.7%); no mapping change detected | Correlation (null) | Vendor cost, call-quality data, timezone-correct timestamps |
| 2. More agents | Agent IDs unresolved (one ID ↔ ~29 employee codes); no productivity or agent-hour measure possible | Cannot be assessed | Resolved agent identity, hours, cost, capacity utilisation |
| 3. AI voice | No identifiable agentic-voice channel/outcome link to payments | Cannot be assessed | Channel-tagged calls linked to payments, per-minute cost |
| 4. Better borrower targeting | 14-day payment rate is {by_chan['mean'].min()*100:.1f}–{by_chan['mean'].max()*100:.1f}% whatever the recommended channel or target status; no identifiable strategy change date | Correlation (null) | Assignment log, propensity features, a holdout |
| 5. WhatsApp / digital | Payment rate after WhatsApp/SMS events is similar for every event type (screen only, not cleaned) | Correlation (null) | Opt-in/consent, cost per message, linkage to payments |
| 6. Field operations | Payment rate after field visits ≈3.3–4.2% for every outcome, including 'PAID' | Correlation (null) | Visit cost, verified outcomes, geography (borrower identity unresolved) |

## Conditional recommendation (a judgement, not a data finding)
- **Do not release the full ₹10 Cr yet.** Release only a small measurement-and-test tranche first (size to be set by finance), then the remainder to whichever option passes a pre-registered test.
- **If leadership must nominate one option now: better borrower targeting**, because it is reversible, can be randomised inside the existing book without new capacity (agents, telephony or field networks are harder to unwind), and sits upstream of the other five options. This ranking rests on testability and reversibility, **not on a measured return**; the data shows no measurable targeting effect today.
- Revisit immediately if finance supplies costs and keep rate: with them, the break-even table below becomes a real hurdle rate.

## Scenario arithmetic (HYPOTHETICAL; no value below is observed)
Annualised run-rate = ₹{annual:.0f} Cr (extrapolated from Jan–Jul). Needed incremental recovery to repay ₹10 Cr: ₹{10/1:.0f} Cr if the company keeps 100% of recovered rupees ({10/annual*100:.1f}% of run-rate), ₹{10/.5:.0f} Cr at 50% ({10/.5/annual*100:.1f}%), ₹{10/.25:.0f} Cr at 25% ({10/.25/annual*100:.1f}%), ₹{10/.1:.0f} Cr at 10% ({10/.1/annual*100:.1f}%). Full grid in `reports/investment_sizing.md`.

## Downside
If the spend produces no uplift (as every observational screen here would suggest), the loss is the full ₹10 Cr. If c is low (10–25%), even a +10% uplift on the run-rate would not repay the spend. Over-hiring or telephony contracts are hard to reverse; AI-voice and WhatsApp raise compliance/complaint risk that this data cannot quantify.

## How to measure the investment's success
1. Randomised holdout as in `reports/experiment_design.md` ({size[(base,.5)]:,} accounts per arm detects +50%; {n20:,} per arm detects +20%; per-arm numbers are unique accounts).
2. Primary KPI: incremental SUCCESS recovery per assigned account (14/30/60 days) versus control; secondary: payer share, validated PTP kept rate, contact rate.
3. Financial KPI: (incremental recovery × c) − incremental cost, with a 95% interval; success = lower bound above zero.
4. Guardrails: complaints, disputes, reversals/failed payments, opt-outs.
5. Report **recovery per calendar day** (never monthly totals) and keep the corrected definitions (`reports/metric_definitions.md`).
"""
open("reports/investment_recommendation.md", "w", encoding="utf-8").write(R)
print("\n".join(L))
