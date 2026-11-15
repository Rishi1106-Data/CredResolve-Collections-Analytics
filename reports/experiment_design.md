# Controlled experiment design (to establish incremental recovery before spending ₹10 Cr)

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
| **Sample size** | Unique accounts per arm at 80% power, 5% two-sided, baseline 3.76% (CI 3.52–4.01%): **1,988** to detect +50% relative; **11,015** for +20%; 42,148 for +10%. A 2-arm test at +20% needs 22,030 of 30,000 accounts (73% of the book) **if all are eligible**. Add ~5–10% for exclusions/attrition. |
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
