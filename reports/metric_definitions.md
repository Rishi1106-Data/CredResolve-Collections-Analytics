# Metric definitions (formula, numerator, denominator, exclusions)

All metrics are computed by `src/metrics.py` on the golden tables and re-computed independently from the RAW CSVs with SQL (`sql/metric_validation.sql`, run by `src/validate.py`): all 8 months × 10 checked metrics match (`reports/metric_validation.csv`). Headline numbers used in every deliverable are written once to `reports/headline_numbers.json`.

## Recovery and its denominators (read this first)

| Metric | Formula | Denominator | What it is | Caveat |
|---|---|---|---|---|
| **Successful payment amount** | Σ amount of `payment_status='SUCCESS'` after de-duplication on `payment_id` | – | Measured fact | Excludes FAILED, PENDING, REVERSED (together 30% of payment rupees), 486 exact-duplicate rows and 14 conflicting-ID rows. Timestamps have no timezone; used as stored. |
| **Recovery per calendar day** | Successful payment amount ÷ calendar days | 28/30/31 days; Aug = 8 | Headline performance measure | Removes the month-length effect. Jan–Jul are complete months; Aug is partial. |
| **Recovery per base account** | Successful payment amount ÷ 30,000 | All 30,000 accounts in the snapshot | **Index** | The base includes PAID/CLOSED/WRITEOFF accounts (75%) that still pay. Not per eligible account. |
| **Paying-account share** | distinct accounts with ≥1 SUCCESS payment in the month ÷ 30,000 | All 30,000 accounts | **Index** | Same caveat. Month totals scale with month length; compare paying accounts per day. |
| **Average payment (ticket)** | mean SUCCESS payment amount | SUCCESS payments | Measured fact | |
| **Recovery as % of static outstanding (index)** | Successful payment amount ÷ Σ `outstanding_amount` snapshot (₹1,049 Cr) | Static snapshot | **NOT a collection / recovery rate** | An eligible-balance denominator cannot be established (see `reports/denominator_audit.md`): no start-of-period balance, status contradicts payments, 13.8% of paying accounts recovered more than their snapshot balance. Useful only to compare months because the denominator is constant. |

## Other metrics

| Metric | Formula | Numerator | Denominator | Notes |
|---|---|---|---|---|
| Recovery per worked account | Recovery ÷ worked accounts | SUCCESS payments | distinct accounts with ≥1 outbound call in the month | Index: payments also come from accounts not called. |
| Contact rate (call level) | ANSWERED ÷ outbound calls | outbound calls with `call_status='ANSWERED'` | all outbound calls (de-duplicated) | Excludes inbound. |
| Contact rate (account level) | accounts answered ÷ accounts worked | accounts with ≥1 ANSWERED outbound call | accounts with ≥1 outbound call | |
| **RPC (PROXY ONLY)** | engaged dispositions ÷ dispositions | dispositions in {PTP, PROMISE_TO_PAY, PTP_BROKEN, PAID, REFUSED, DISPUTE, CALLBACK} | all dispositions (or only those on ANSWERED calls) | Not a verified right-party-contact rate: no RPC flag exists, ~80% of dispositions sit on unanswered calls, borrower IDs are unreliable. |
| PTP rate | PTPs created ÷ 1,000 accounts | PTP rows by creation month | 30,000 accounts | `promises_to_pay` has no `call_id` and 3 of 4 sources are not calls, so "PTP per call" is invalid. |
| PTP kept rate (recorded) | status = KEPT ÷ **matured** promises (also shown ÷ KEPT+BROKEN) | matured promises with `status='KEPT'` | promises with `promised_date ≤ 2026-08-08 23:59:59` | 1,242 un-matured promises excluded. 4,128 matured promises are still OPEN (stale). |
| **PTP paid in window, upper bound** | matured promises with ≥1 SUCCESS payment on the account in [created, promised_date] ÷ matured | | matured promises | One payment can count for several promises on the same account. |
| **PTP paid in window, one-to-one (conservative)** | same, but each payment is credited to at most ONE promise (earliest promised date) | | matured promises | Use the range 3.67%–3.71% rather than a single number. |
| PTP full amount (rupee waterfall) | promised amount fully covered by payment rupees applied earliest-due first | | matured promises | 2.38%. |
| Recovery per agent-hour | **not computed** | – | – | Agent identity unresolved; sessions cannot be linked reliably. |
| Cost per ₹ recovered | **not computed** | – | – | No cost data in any table. |
| Channel conversion | contact rate by campaign channel; payment within 14 days of a targeting row / first event | – | – | Payments carry no campaign/channel link, so this is correlation only. |

**Wording rules used in every deliverable:** say "recovery per calendar day" (not "recovery rate"); say "no statistically detectable trend/difference in the observed period" (not "flat"); quote the PTP kept rate as a range and say "payment in window", not "proof of kept".
