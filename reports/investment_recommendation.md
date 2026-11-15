# ₹10 Cr investment: what the evidence supports

## Bottom line
**The data does not support committing ₹10 Cr to any single option, and no reliable ROI can be calculated.** We therefore give a *conditional* recommendation, scenario arithmetic (labelled hypothetical) and a test that would settle the question.

## Why a financial ROI cannot be calculated
1. **No cost data.** There are no agent salary, telephony/vendor, WhatsApp/SMS, AI-voice or field-visit cost fields, and no commission/keep rate on recovered money.
2. **No incremental-effect estimate.** Payments carry no campaign, channel or interaction ID. 'Last call before payment' attribution performs no better than a placebo (calls after the payment), so recovery cannot be assigned to a channel.
3. **No measured difference between options in the screens we could run** (correlational only; see `reports/driver_screen.csv`): contact rate by vendor/channel/strategy/hour band; 14-day payment rate by recommended channel and by target status (3.6–4.0% by channel); payment rate after WhatsApp, SMS and field events, which is ≈3.3–4.2% whatever the event type or recorded outcome (even a field visit recorded as 'PAID').
4. **Baseline has not moved.** Per-day recovery shows no statistically detectable trend in Jan–Jul (HAC p=0.327), so there is no observed improvement to attribute to any past investment.
5. The dataset is synthetic and almost uniform; the lack of effects may reflect how it was generated rather than the business.

## The six options against the evidence

| Option | What the data shows | Evidence | What is missing |
|---|---|---|---|
| 1. Better telephony | Contact rate 19.3–20.4% every month; vendor differences borderline (p=0.050, 19.5–20.7%); no mapping change detected | Correlation (null) | Vendor cost, call-quality data, timezone-correct timestamps |
| 2. More agents | Agent IDs unresolved (one ID ↔ ~29 employee codes); no productivity or agent-hour measure possible | Cannot be assessed | Resolved agent identity, hours, cost, capacity utilisation |
| 3. AI voice | No identifiable agentic-voice channel/outcome link to payments | Cannot be assessed | Channel-tagged calls linked to payments, per-minute cost |
| 4. Better borrower targeting | 14-day payment rate is 3.6–4.0% whatever the recommended channel or target status; no identifiable strategy change date | Correlation (null) | Assignment log, propensity features, a holdout |
| 5. WhatsApp / digital | Payment rate after WhatsApp/SMS events is similar for every event type (screen only, not cleaned) | Correlation (null) | Opt-in/consent, cost per message, linkage to payments |
| 6. Field operations | Payment rate after field visits ≈3.3–4.2% for every outcome, including 'PAID' | Correlation (null) | Visit cost, verified outcomes, geography (borrower identity unresolved) |

## Conditional recommendation (a judgement, not a data finding)
- **Do not release the full ₹10 Cr yet.** Release only a small measurement-and-test tranche first (size to be set by finance), then the remainder to whichever option passes a pre-registered test.
- **If leadership must nominate one option now: better borrower targeting**, because it is reversible, can be randomised inside the existing book without new capacity (agents, telephony or field networks are harder to unwind), and sits upstream of the other five options. This ranking rests on testability and reversibility, **not on a measured return**; the data shows no measurable targeting effect today.
- Revisit immediately if finance supplies costs and keep rate: with them, the break-even table below becomes a real hurdle rate.

## Scenario arithmetic (HYPOTHETICAL; no value below is observed)
Annualised run-rate = ₹218 Cr (extrapolated from Jan–Jul). Needed incremental recovery to repay ₹10 Cr: ₹10 Cr if the company keeps 100% of recovered rupees (4.6% of run-rate), ₹20 Cr at 50% (9.2%), ₹40 Cr at 25% (18.3%), ₹100 Cr at 10% (45.8%). Full grid in `reports/investment_sizing.md`.

## Downside
If the spend produces no uplift (as every observational screen here would suggest), the loss is the full ₹10 Cr. If c is low (10–25%), even a +10% uplift on the run-rate would not repay the spend. Over-hiring or telephony contracts are hard to reverse; AI-voice and WhatsApp raise compliance/complaint risk that this data cannot quantify.

## How to measure the investment's success
1. Randomised holdout as in `reports/experiment_design.md` (1,988 accounts per arm detects +50%; 11,015 per arm detects +20%; per-arm numbers are unique accounts).
2. Primary KPI: incremental SUCCESS recovery per assigned account (14/30/60 days) versus control; secondary: payer share, validated PTP kept rate, contact rate.
3. Financial KPI: (incremental recovery × c) − incremental cost, with a 95% interval; success = lower bound above zero.
4. Guardrails: complaints, disputes, reversals/failed payments, opt-outs.
5. Report **recovery per calendar day** (never monthly totals) and keep the corrected definitions (`reports/metric_definitions.md`).
