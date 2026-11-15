# CredResolve – Collections Analytics Assignment

## Live dashboard (Tableau Public)
**[Open the interactive executive dashboard](https://public.tableau.com/app/profile/rishiraj.karn/viz/CredResolve_Executive_Dashboard/CredResolveExecutiveDashboard)**: no Tableau install needed. The workbook (`CredResolve_Executive_Dashboard.twbx`) is also in this repo; download it from Tableau Public or open the `.twbx` in Tableau to see every worksheet and calculated field.

## 1. Objective
Leadership reports that "recovery improved 11% month-on-month" and must decide where to put ₹10 Cr (telephony, agents, AI voice, targeting, WhatsApp/digital, field). This project (a) tests whether the 11% is real, (b) identifies drivers without confusing correlation with causation, (c) states what the data can and cannot say about the ₹10 Cr decision, and (d) designs the production system and the experiment needed.

**Short answer**
- **The 11% is a month-length effect, not demonstrated growth.** The only +11% pair is Feb→Mar total recovery (₹17.01 Cr → ₹18.89 Cr, +11.03%). February has 28 days, March 31. Per calendar day: ₹60.77 → ₹60.94 lakh (**+0.3%**, 95% CI −5.2% to +5.9% by block bootstrap; −5.9% to +7.1% if days are treated as independent). The evidence does not establish a statistically significant improvement in daily recovery.
- **No statistically detectable trend was identified in the observed period** (Jan–Jul, ≈₹0.60 Cr/day; Newey–West slope −0.35% per 30 days, 95% CI −1.05% to +0.35%). This is exploratory and is not proof that performance is unchanged.
- **₹10 Cr:** no reliable ROI can be calculated (no cost data, no payment→campaign link, no measured effect for any option). Recommendation: stage the money and run a randomised holdout. On a unique-account baseline of 3.76%, detecting a +20% relative lift needs ≈11,015 accounts per arm. No ROI figure was invented; scenario numbers are labelled hypothetical.
- **Payment-checked PTP kept rate is 3.67–3.71%** of matured promises (recorded status says ≈50% of KEPT+BROKEN).
- "Recovery ÷ outstanding" is an **index, not a collection rate**: an eligible balance cannot be established.
- Coverage is 1 Jan – 8 Aug 2026 (≈7.2 months), not 12.

## 2. Dataset
17 synthetic CSV tables (borrowers, accounts, agents, agent_sessions, campaigns, daily_targeting, calls, call_attempts, call_dispositions, whatsapp_events, sms_events, field_visits, promises_to_pay, payments, vendor_telephony, complaints, account_status_history) plus `data_dictionary.csv` and a README, in `collections_30k_dataset/` (never modified). Intentional problems include duplicates (500 repeated payment IDs, 1,350 repeated call IDs, 600 duplicate borrower rows), missing values (382 payment references, 1,827 call agent IDs), mixed timezones, conflicting identifiers and stale statuses.

## 3. Folder structure
| Path | What |
|---|---|
| `collections_30k_dataset/` | RAW data (read-only) |
| `src/clean.py` | cleaning pipeline → `golden/`, `rejects/`, `reports/cleaning_summary.*` |
| `src/ptp_validation.py` | PTP maturity filter, one-payment-one-promise validation, placebo |
| `src/metrics.py` | monthly metrics, exploratory tests (naive, HAC, block bootstrap), decomposition, `headline_numbers.json` |
| `src/denominators.py` | denominator audit (eligible balance, status, status history) |
| `src/validate.py`, `SQL/metric_validation.sql` | independent SQL re-computation from raw files (SQLite; run by the pipeline) |
| `SQL/metric_validation_mysql.sql` | MySQL 8.0 version of the validation queries: import/key checks, duplicate audit, monthly recovery, contact rate, PTP validation (upper bound and one-payment-one-PTP) |
| `src/investigate.py`, `src/drivers.py` | attribution / channel / driver screens (correlation only) |
| `src/investment_sizing.py` | unique-account baseline, sample sizes, scenario arithmetic, experiment design, investment recommendation |
| `CredResolve_Executive_Dashboard.twbx` / `.png` | **Executive dashboard (Tableau, one screen, 1200×850; [live on Tableau Public](https://public.tableau.com/app/profile/rishiraj.karn/viz/CredResolve_Executive_Dashboard/CredResolveExecutiveDashboard))**: 4 KPI cards, recovery-per-day, contact-rate and paying-accounts trends (August flagged as partial), executive insight panel. Open the `.twbx` in Tableau Desktop/Reader; the `.png` is a static export |
| `src/make_dashboard.py` | optional HTML version of the dashboard (generated into `dashboard/`, not committed) |
| `src/make_architecture.py` → `docs/architecture.png/.svg` | architecture diagram |
| `src/check_consistency.py` | checks deliverables against `reports/headline_numbers.json` |
| `Analysis/Analysis.ipynb` | notebook with reasoning and outputs |
| `golden/`, `rejects/` | golden tables; every removed/merged row with a reason |
| `reports/` | `executive_memo.md/.docx`, `findings_report.md`, `data_quality_report.md`, `limitations.md`, `metric_definitions.md`, `statistical_tests.md`, `denominator_audit.md`, `ptp_validation.md`, `experiment_design.md`, `investment_recommendation.md`, `investment_sizing.md`, CSVs |
| `docs/architecture.md` | production design (diagram, contracts, keys, lineage, incremental/late data, backfills, checks, monitoring) |

## 4. Dependencies and installation
Python 3.10+ with: `pandas`, `numpy`, `scipy`, `tabulate`, `matplotlib` (diagram), `playwright` optional (dashboard screenshot only). To run the notebook in Jupyter also install `jupyter nbformat nbconvert ipykernel`. To rebuild the memo .docx: `pandoc reports/executive_memo.md -o reports/executive_memo.docx`.
```bash
pip install pandas numpy scipy tabulate matplotlib
pip install jupyter nbformat nbconvert ipykernel    # only for the notebook
```

## 5. Execution order (run from the repository root)
```bash
bash run_all.sh      # runs everything below in order, then the consistency check
```
1. **Cleaning pipeline:** `python src/clean.py`
2. **PTP validation:** `python src/ptp_validation.py`
3. **Metrics + tests:** `python src/metrics.py` (writes `reports/monthly_metrics.csv`, `statistical_tests.md`, `headline_numbers.json`)
4. `python src/denominators.py`, `python src/validate.py`, `python src/investigate.py`, `python src/drivers.py`, `python src/investment_sizing.py`
5. **Dashboard:** open `CredResolve_Executive_Dashboard.twbx` in Tableau (or view `CredResolve_Executive_Dashboard.png`). Optional HTML version: `python src/make_dashboard.py`, then open `dashboard/dashboard.html`
6. **Diagram:** `python src/make_architecture.py`
7. **Consistency:** `python src/check_consistency.py`

## 6. Important assumptions
- Only `payment_status = 'SUCCESS'` counts as recovery; duplicates are removed on `payment_id` (not `payment_reference`, which is not unique).
- Recovery per calendar day is the headline measure; Jan–Jul are complete months, August (8 days) is excluded from month-on-month comparisons.
- Borrower and agent identities cannot be resolved; no "latest record" is treated as truth.
- Calls are converted to UTC assuming `event_at` is local time in the row's timezone label (assumption); payments and PTPs are used as stored.
- PTP: a promise is *matured* if `promised_date ≤ 2026-08-08 23:59:59`; "kept" means a SUCCESS payment on the account inside [created, promised date], reported as a range.
- Experiment baseline: unique accounts, index date = first targeting date, outcome = SUCCESS payment within 14 days, only accounts with a fully observable window.
- ₹10 Cr scenario values (keep rate c, uplift) are hypothetical parameters, not estimates.

## 7. SQL note
Cleaning, transformations and metric calculations are implemented in Python (`src/`); the SQL files re-compute the headline metrics independently from the RAW tables as a cross-check (`reports/metric_validation.csv`). The MySQL file additionally documents the deduplication rule (`import_row_id` assigned at ingestion).

## 8. Known limitations (full list: `reports/limitations.md`)
Exploratory statistics on one synthetic extract; no eligible-balance denominator; PTP kept rate is a range; borrower/agent identity unresolved so geography, tenure and agent productivity are not analysed; no language field; no client field in any table, so the client driver cannot be analysed; no cost data or keep rate, so no ROI; payments not linked to campaigns, so channel attribution is not identifiable; WhatsApp/SMS/field tables screened but not fully cleaned; `complaints` and `agent_sessions` not analysed; the dataset is synthetic, so absence of effects may reflect how it was generated.
