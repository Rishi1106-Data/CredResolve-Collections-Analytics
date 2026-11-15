# Statistical tests (zero-filled calendar, 1 Jan - 31 Jul 2026)

**Status: EXPLORATORY.** One synthetic extract, 212 daily values, several tests. A non-significant p-value means *no statistically detectable* difference or trend in the observed period; it is NOT proof that performance is unchanged.

- Calendar days: 212 | days with zero SUCCESS recovery (filled as 0): 0 | days present in raw data: 212
- Feb: 28 days, mean ₹60.77 lakh/day | Mar: 31 days, mean ₹60.94 lakh/day
- Total Feb→Mar change: +11.03% | Per-day change: +0.29%

## A. Feb vs Mar, per-day recovery

Naive tests (treat each day as an independent observation):
- Welch t-test (daily means): t=0.09, p=0.932
- Mann-Whitney U: p=0.885
- Bootstrap, days resampled one by one (10,000x) 95% CI for per-day change: [-5.9%, +7.1%]
- Permutation test (shuffle day labels Feb/Mar): p=0.935
- **Block bootstrap (7-day blocks, 10,000x) 95% CI for per-day change: [-5.2%, +5.9%]** (robust to short-range correlation; preferred interval)
- Reading: the data are compatible with a true per-day change anywhere from about -5% to +6%. A per-day gain as large as the reported 11% is not supported; a small gain or loss cannot be excluded.

## B. Trend over Jan–Jul (212 days)

- Naive OLS slope: ₹-697 per day per day (-0.35% of mean per 30 days), p=0.456 (assumes independent days)
- Kendall tau trend test: tau=-0.040, p=0.384
- Autocorrelation of daily recovery, lags 1–7: -0.17, +0.08, -0.06, +0.05, -0.05, -0.05, -0.00 (rough ±0.13 band for a single lag)
- Ljung–Box test for serial correlation: lags 1–7 p=0.20; lags 1–14 p=0.32
  → Lag-1 autocorrelation (-0.17) is slightly outside the single-lag band, but the joint tests do not detect serial correlation. That is reassuring, but 212 days is short and the test has limited power, so the robust versions below are still the ones to quote.
- **Newey–West (HAC, 7-day lag) slope: -0.35% of mean per 30 days, 95% CI [-1.05%, +0.35%], p=0.327**
- **Conclusion: no statistically detectable trend was identified in the observed period.** The HAC interval shows the size of trend this data could detect: changes smaller than roughly the interval width cannot be ruled out. This is not proof that performance is flat.
- Limitations of these tests: exploratory; only 7 months of one extract; day-level payments are aggregated from rows whose timestamps have no timezone; several tests were run without multiplicity control; a synthetic dataset may have no real trend by construction.
- Day-of-week index (1.00 = average; Mon..Sun): 1.01, 0.98, 1.03, 1.01, 1.00, 0.97, 1.00
- Month-over-month swings in TOTAL recovery (Feb..Jul): -9.1%, +11.0%, -7.3%, +5.2%, -4.7%, +6.7% | calendar-day ratio: -9.7%, +10.7%, -3.2%, +3.3%, -3.2%, +3.3% | PER-DAY swings: +0.6%, +0.3%, -4.2%, +1.8%, -1.5%, +3.2%

## C. Feb→Mar decomposition (total recovery ratio = product of factors; identity, not a model)

|                             |   ratio |   pct_change |   share_of_total_log_change_pct |
|:----------------------------|--------:|-------------:|--------------------------------:|
| calendar days (31 vs 28)    |    1.11 |        10.71 |                           97.26 |
| paying accounts per day     |    1.01 |         0.55 |                            5.22 |
| payments per paying account |    1    |        -0.03 |                           -0.29 |
| average ticket              |    1    |        -0.23 |                           -2.2  |
| TOTAL (Mar/Feb)             |    1.11 |        11.03 |                          100    |

Note: 'paying accounts per day' counts distinct accounts per month, so a longer month adds fewer new payers than days; the 97% share of calendar days should be read as 'about 97%', and the same conclusion holds with payments per day × ticket (payments per day +0.52%, ticket -0.23%).

## D. Account volume, paying-account share, ticket, mix

- Accounts worked (outbound): Feb 8,933 → Mar 9,766 (+9.3%); per day -1.3%
- Share of the 30,000 base accounts paying in the month: Feb 7.24% → Mar 8.06% (months differ in length); paying accounts per day +0.5%
- Average payment (ticket): Feb ₹75,019 → Mar ₹74,846 (-0.23%)
- Mix of payments by loan_type, Feb vs Mar: chi-square p=0.924 (no statistically detectable composition shift)
- Mix of payments by dpd_bucket, Feb vs Mar: chi-square p=0.184 (no statistically detectable composition shift)
- Mix of payments by risk_segment, Feb vs Mar: chi-square p=0.334 (no statistically detectable composition shift)
- Mix-standardised avg ticket by dpd_bucket: Feb ₹75,045 → Mar ₹74,835 (-0.3%) vs raw -0.2%
- Mix-standardised avg ticket by loan_type: Feb ₹75,032 → Mar ₹74,856 (-0.2%) vs raw -0.2%
- PTP: see reports/ptp_validation.md. Matured promises (16,758; 1,242 un-matured excluded): recorded KEPT = 24.94% of matured (49.76% of KEPT+BROKEN) but a SUCCESS payment inside the promise window exists for only 3.67% (one payment → one promise) to 3.71% (overlap allowed); recorded KEPT 4.09% vs BROKEN 3.39% have a payment in window. Jul/Aug promises are maturity-censored.
- The 30,000-account base is a fixed snapshot (all opened 2024-01-01..2025-11-30, before the window). A fixed base cannot show portfolio acquisition, and an eligible-balance population cannot be built from it (see reports/denominator_audit.md).
- Counting rules (Jan 1–Aug 8): clean SUCCESS ₹131.56 Cr | raw SUCCESS incl. duplicate rows ₹134.15 Cr (+1.97%) | raw all statuses ₹191.73 Cr (+45.7%). Mar/Feb: raw SUCCESS +10.99%, raw all-status +12.2%, clean +11.03%.
- Day-of-week index, month swings and decomposition are descriptive; they are not causal estimates.
