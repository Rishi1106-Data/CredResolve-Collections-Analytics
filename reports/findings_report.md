# Findings report

## Verdict on the "11% month-on-month improvement"
**The 11% is a month-length effect, not demonstrated growth.** The only +11% month pair is Feb→Mar total SUCCESS recovery (₹17.01 Cr → ₹18.89 Cr, +11.03%). Per calendar day the change is +0.29%, and the evidence does not establish a statistically significant improvement in daily recovery. This is an exploratory analysis of one extract; it does not prove performance is unchanged.

| Check | Result | Evidence class |
|---|---|---|
| Month length | Mar has 31 days, Feb 28 (+10.7%). Calendar days explain about 97% of the log change (decomposition identity) | Fact (arithmetic) |
| Per-day recovery, Feb→Mar | ₹60.77 → ₹60.94 lakh/day = **+0.3%**. 95% CI **−5.2% to +5.9%** (7-day block bootstrap); −5.9% to +7.1% if days are treated as independent. Welch p=0.93, permutation p=0.94 | Strong evidence that the per-day gain is far below 11%; small changes cannot be excluded |
| Trend Jan–Jul (212 days, none missing) | Newey–West slope −0.35% of mean per 30 days, 95% CI −1.05% to +0.35%, p=0.327 (naive OLS p=0.46, Kendall p=0.38). **No statistically detectable trend was identified in the observed period** | Exploratory; absence of evidence, not evidence of absence |
| Serial correlation | Lag-1 autocorrelation −0.17; Ljung–Box p=0.20 (7 lags), 0.32 (14 lags): none detected, but power is limited | Diagnostic |
| Account volume | Accounts worked +9.3% (8,933 → 9,766), per day −1.3%; paying accounts per day +0.5% | Fact |
| Paying-account share | 7.24% → 8.06% of the 30,000 base (longer month); per day +0.5% | Fact (index) |
| Average payment | ₹75,019 → ₹74,846 (−0.23%) | Fact |
| Portfolio mix | Mix of payments by loan type / DPD / risk, Feb vs Mar: chi-square p = 0.92 / 0.18 / 0.33; mix-standardised ticket −0.2 to −0.3% | Strong evidence (no detectable shift) |
| Account population | All 30,000 accounts opened before the window; no acquisition. Terminal-status share steady ≈43% each month; eligible balance cannot be established | Fact / limitation |
| Counting rules | Duplicate rows inflate SUCCESS rupees by 1.97% (₹134.15 vs ₹131.56 Cr); counting all statuses inflates by 45.7%. Raw all-status Mar/Feb = +12.2%; raw SUCCESS +10.99% | Fact |
| Other months | MoM total swings −9.1, +11.0, −7.3, +5.2, −4.7, +6.7% follow calendar-day ratios (−9.7, +10.7, −3.2, +3.3, −3.2, +3.3%); per-day swings −4.2% to +3.2% | Strong evidence |

## Recovery-rate denominators (correction C)
Only these have defensible denominators: successful payment amount, recovery **per calendar day** (₹0.598 Cr/day Jan–Jul), **paying-account share** and **average payment**. "Recovery ÷ static outstanding" (≈12.1% over Jan–Jul; 1.6–1.8% per month) is an **index, not a collection rate**: 75% of accounts are PAID/CLOSED/WRITEOFF yet pay at the same rate as ACTIVE ones, the status history contradicts the accounts table (14.2% agreement), and 13.8% of paying accounts recovered more than their snapshot balance. Details: `reports/denominator_audit.md`.

## Which metrics are real vs misleading
- **Measured, no statistically detectable change:** per-day recovery ≈ ₹0.60 Cr/day; contact rate 19.3–20.4% (call level); paying accounts per day.
- **Misleading:** total monthly recovery (month length); recorded "PTP kept" (49.76% of KEPT+BROKEN, 24.94% of matured promises) versus payment-checked 3.67–3.71%; disposition "RPC" (proxy ~77%); any figure counting non-SUCCESS payments or duplicates; "recovery rate" from a static balance.

## PTP validation (correction D)
Matured promises: 16,758 (1,242 un-matured excluded). A SUCCESS payment inside the promise window exists for **3.67% (one payment → one promise) to 3.71% (overlap allowed)**; the full promised amount is covered for 2.38%. Only 8 payments fall inside two or more promise windows. Recorded KEPT vs BROKEN promises have payments in window 4.09% vs 3.39%, and a same-length window placed after the due date gives 3.71%, so promises do not visibly raise payment probability. Details: `reports/ptp_validation.md`.

## Why (drivers): classification
| Driver | Result | Class |
|---|---|---|
| Month length | explains the reported jump | Fact |
| Vendor, strategy version, channel, hour band, DPD, loan type, risk (contact rate) | no significant differences (vendor p=0.050 borderline, 19.5–20.7%) | Correlation (null) |
| DPD bucket vs account paying | 43.4–45.8%, p=0.028; not robust to multiple testing (18 tests) | Correlation (weak) |
| WhatsApp / SMS / field events vs payment within 14 days | 3.3–4.2% whatever the event type or outcome (all p>0.14) | Correlation (null) |
| Campaign / agent / geography / tenure / language | cannot be tested reliably (see limitations) | Hypothesis / unknown |
| Targeting change | no identifiable change date or payment-campaign link | Cannot be verified |

## Experiment sizing (correction A)
The earlier "11,557 per arm" used `daily_targeting` rows (45,000 rows, 23,344 distinct accounts) and is withdrawn. On a unique-account cohort (first targeting date as index; 22,736 accounts with an observable 14-day window) the baseline 14-day payment rate is 3.76% (95% CI 3.52–4.01%). A +20% relative lift needs about 11,015 unique accounts per arm, +50% about 1,988. See `reports/experiment_design.md`.

## Corrections applied in this revision
1. Sample size recomputed on unique accounts with a defined cohort/outcome (A).
2. Trend wording changed to "no statistically detectable trend"; serial-correlation diagnostics, Newey–West and block bootstrap added (B).
3. Denominators separated and audited; static-outstanding ratio relabelled as an index (C).
4. PTP validation: maturity filter, one-payment-one-promise, rupee waterfall, grace and placebo checks (D).
5. All headline numbers come from `reports/headline_numbers.json`; `src/check_consistency.py` checks every deliverable (E).
6. Visual architecture diagram added (F); README rewritten (G).
