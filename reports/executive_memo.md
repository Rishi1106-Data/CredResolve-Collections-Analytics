# Executive memo: is recovery really up 11%?

**To:** Leadership | **Data:** collections extract, 1 Jan – 8 Aug 2026 (≈7.2 months, not 12) | **Status:** exploratory analysis of one synthetic extract

## What happened
The reported +11% is the **February → March** jump in total collected rupees (₹17.01 Cr → ₹18.89 Cr, +11.03%). February has 28 days and March 31. **Per calendar day, recovery moved from ₹60.77 lakh to ₹60.94 lakh (+0.3%; 95% interval −5.2% to +5.9%)**, so the data do not establish a statistically significant improvement in daily recovery. Across Jan–Jul recovery was ₹126.8 Cr (≈₹0.60 Cr/day) and **no statistically detectable trend was identified in the observed period** (−0.35% per 30 days, 95% CI −1.05% to +0.35%). This is not proof that performance is unchanged: a change of a few percent could not be seen with this data. Other months' per-day swings ranged from −4.2% to +3.2%. Contact rate was 19.3–20.4% of outbound calls every month.

## Why it looked like growth
1. **Month length** explains about 97% of the Feb→Mar change (fact; arithmetic).
2. **Counting rules** can inflate figures: counting all payment statuses is 45.7% above valid (SUCCESS) recovery, and duplicate payment rows add 1.97%.
3. **Not** volume or mix: paying accounts per day (+0.5%), average payment (−0.2%) and the mix of payments by loan type, DPD and risk (p = 0.92 / 0.18 / 0.33) show no detectable shift; all 30,000 accounts pre-date the period.
4. **Caution on "recovery rate":** dividing recovery by the static outstanding balance (≈12% over Jan–Jul) is only an index. 75% of accounts are marked PAID, CLOSED or WRITEOFF yet receive 75% of recovery, so an eligible balance cannot be established. We report recovery **per day**, paying-account share and average payment instead.

## How confident are we?
- **High (fact):** the 11% is largely a calendar effect; the headline metrics were rebuilt independently from raw files with SQL and match.
- **Moderate:** no detectable per-day change or trend. The tests are exploratory; days may be serially correlated (not detected, but power is limited), so we quote serial-correlation-robust intervals.
- **Low / unknown:** anything about agents, geography, tenure, language, campaigns, targeting or channel. Borrower and agent IDs are inconsistent, there is no language field, and payments are not linked to campaigns.
- **Reported "PTP kept" (~50% of KEPT+BROKEN) is not reliable.** Among 16,758 matured promises (1,242 un-matured excluded), a SUCCESS payment fell inside the promise window for only **3.7%** (3.67% counting each payment once; 3.71% allowing a payment to count for several promises). Payments carry no promise ID, so this is a range, not proof.
- The dataset looks synthetic and nearly uniform, so a lack of effects may reflect how it was generated.

## What should we do?
**The data cannot support a reliable recommendation for any of the six ₹10 Cr options, and no ROI can be calculated** (no cost data, no payment-to-campaign link, no measured effect for any option, including WhatsApp/SMS and field screens).
1. **Fix measurement first (weeks):** one agent ID, one borrower ID, payment-to-campaign linkage, timezone on every event, cost per channel, start-of-period eligible balance.
2. **Stage the money.** Release only a small test tranche now, then the remainder to the option that passes a pre-registered randomised holdout. If one option must be named today, **borrower targeting** is the most reversible and testable inside the existing book (a judgement on testability, not a measured return).
3. **Test design:** randomise unique accounts to treatment vs business-as-usual; primary outcome = a SUCCESS payment within 14 days. On a unique-account baseline of 3.76% (95% CI 3.52–4.01%), detecting a +20% relative lift needs about **11,015 accounts per arm** (+50%: 1,988), i.e. 73% of the 30,000-account book for two arms at +20% if all are eligible.
4. Replace "month-on-month recovery" on the dashboard with **recovery per day**, and quote PTP kept as a range.

## Expected financial impact
**Not estimable from this data; no figure has been invented.** Only arithmetic is available: break-even needs incremental recovery of ₹10 Cr ÷ c, where c is the share of recovered rupees the company keeps (unknown). Hypothetically, at c = 100% that is 4.6% of the ₹218 Cr annualised run-rate (an extrapolation); at c = 50%, 9.2%; at 25%, 18.3%; at 10%, 45.8%. **Downside:** if the spend produces no uplift, the loss is the full ₹10 Cr. Full scenario grid, labelled hypothetical: `reports/investment_sizing.md`.
