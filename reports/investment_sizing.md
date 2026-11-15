# Investment sizing (measured facts + clearly labelled hypotheticals)

## Measured facts

- Jan–Jul 2026 SUCCESS recovery = ₹126.8 Cr over 212 days = ₹0.598 Cr/day.
- Annualised run-rate (× 365) = ₹218 Cr. This is an **extrapolation** from 7 months; it assumes no seasonality and a constant book.
- No table in the dataset holds agent salaries, telephony, WhatsApp/SMS, AI-voice or field costs, or the company's share (commission) of recovered rupees. **Cost per ₹ recovered and ROI cannot be measured.**

## Break-even arithmetic (HYPOTHETICAL parameter c)

Spending ₹10 Cr breaks even when `incremental recovery × c = ₹10 Cr`, where **c = the share of recovered rupees the company keeps / is worth to it**. c is NOT in the data; the rows below are sensitivities, not estimates. One-off spend, 12-month horizon, no discounting.

| assumed c | incremental recovery needed (₹ Cr) | needed uplift on annualised run-rate |
|---:|---:|---:|
| 100% | 10 | 4.6% |
| 50% | 20 | 9.2% |
| 25% | 40 | 18.3% |
| 10% | 100 | 45.8% |

### Hypothetical net-benefit grid (₹ Cr) = uplift × run-rate × c − 10

*Illustration of how sensitive the decision is. The uplift values are NOT forecasts: no uplift has been measured for any of the six options.*

| hypothetical uplift on run-rate | c = 100% | c = 50% | c = 25% | c = 10% |
|---:|---:|---:|---:|---:|
| 0% | -10.0 | -10.0 | -10.0 | -10.0 |
| 2% | -5.6 | -7.8 | -8.9 | -9.6 |
| 5% | +0.9 | -4.5 | -7.3 | -8.9 |
| 10% | +11.8 | +0.9 | -4.5 | -7.8 |
| 20% | +33.7 | +11.8 | +0.9 | -5.6 |

Reading: at c = 10–25% even a +10% uplift would not repay ₹10 Cr; at c = 100% a +5% uplift would. Because c and the uplift are both unknown, the sign of the return is unknown.

## Experiment sizing on a UNIQUE-ACCOUNT cohort

**Correction.** The earlier calculation used the share of `daily_targeting` **rows** followed by a payment (3.59%). That table has 45,000 rows but only 23,344 distinct accounts (up to 8 rows per account, mean 1.93), so rows are not independent units and the resulting '11,557 per arm' must not be read as a requirement in unique accounts. It is replaced by the cohort below.

**Cohort definition.** One row per account: the account's FIRST `daily_targeting` date is its index date. Outcome = at least one de-duplicated SUCCESS payment in the 14 days from the index date (index date ≤ payment < index date + 14 days). Only accounts whose full 14-day window ends by 8 Aug 2026 are kept (index date ≤ 26 Jul), so late accounts are not under-counted.

- Distinct targeted accounts: 23,344; with a fully observable window: **22,736**
- Baseline 14-day payment rate: **3.76%** (854 of 22,736 accounts); Wilson 95% CI 3.52%–4.01%
- Reconciliation: the old row-level figure was 3.59% (repeated accounts, window ≤14 days inclusive). The unique-account baseline differs slightly and is the one to use.
- Baseline by index month: 2026-01 3.72% (n=5,732); 2026-02 3.60% (n=4,193); 2026-03 3.77% (n=3,795); 2026-04 3.65% (n=3,072); 2026-05 3.70% (n=2,566); 2026-06 3.92% (n=1,990); 2026-07 4.47% (n=1,388)
- Baseline by recommended channel: FIELD 3.85% (n=5,769); SMS 3.58% (n=5,695); VOICE 3.63% (n=5,598); WHATSAPP 3.97% (n=5,674) – no clear difference between channels in this observational data.

### Accounts needed per arm (unit = unique account; 80% power; 5% two-sided; 2-arm comparison of proportions)

| relative lift to detect | absolute lift (at baseline) | accounts PER ARM (baseline) | if baseline is at CI upper | if baseline is at CI lower |
|---:|---:|---:|---:|---:|
| 10% | 0.38 pp | 42,148 | 39,357 | 45,135 |
| 20% | 0.75 pp | 11,015 | 10,284 | 11,797 |
| 50% | 1.88 pp | 1,988 | 1,855 | 2,130 |

**Feasibility.** The book has 30,000 accounts. A 2-arm test needs 2 × n accounts: 3,976 for a +50% relative lift (13% of the book), 22,030 for +20% (73%), 84,296 for +10% (281% – larger than the book). A 3-arm test at +20% needs 33,045 (110%) and would not fit in one cycle. These figures assume that every account in the book is eligible and reachable, which cannot be verified today (see reports/denominator_audit.md); the real eligible pool will be smaller, so the detectable lift will be larger.

**What the baseline is and is not.** It is an *observational* rate for accounts that were targeted, measured on this extract. It is used only to size a future randomised test; it does not measure the effect of targeting. The first-target cohort contains accounts that may also have been called, messaged or visited in the same 14 days.
