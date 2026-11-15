-- Independent re-computation of key metrics directly from the RAW tables (SQLite dialect).
-- De-duplication rule: keep the first-ingested row (lowest rowid) per business key.
-- Used by src/validate.py, which compares the output with reports/monthly_metrics.csv.

-- name: recovery
WITH p AS (SELECT * FROM payments WHERE rowid IN (SELECT MIN(rowid) FROM payments GROUP BY payment_id))
SELECT substr(event_at,1,7) AS month,
       SUM(amount)/1e7 AS recovery_cr,
       COUNT(*) AS n_success_payments,
       COUNT(DISTINCT account_id) AS accounts_paying,
       AVG(amount) AS avg_ticket_rs
FROM p WHERE payment_status = 'SUCCESS'
GROUP BY 1 ORDER BY 1;

-- name: calls
WITH c AS (SELECT * FROM calls WHERE rowid IN (SELECT MIN(rowid) FROM calls GROUP BY call_id))
SELECT substr(event_at,1,7) AS month,
       COUNT(*) AS outbound_calls,
       100.0*SUM(call_status='ANSWERED')/COUNT(*) AS contact_rate_call_pct,
       COUNT(DISTINCT account_id) AS accounts_worked_outbound
FROM c WHERE direction='OUTBOUND' AND event_at >= '2026-01-01' AND event_at < '2026-09-01'
GROUP BY 1 ORDER BY 1;

-- name: ptp
-- matured = promised_date <= 2026-08-08 23:59:59 ; "paid in window (upper bound)" = a SUCCESS payment on the account
-- between the promise creation time and the promised date (one payment may count for several promises: upper bound; the one-to-one version is in src/ptp_validation.py).
WITH p AS (SELECT * FROM payments WHERE rowid IN (SELECT MIN(rowid) FROM payments GROUP BY payment_id)
           AND payment_status='SUCCESS'),
m AS (SELECT * FROM promises_to_pay WHERE promised_date <= '2026-08-08 23:59:59'),
v AS (SELECT m.ptp_id, substr(m.event_at,1,7) AS month, m.status,
             MAX(CASE WHEN p.payment_id IS NOT NULL THEN 1 ELSE 0 END) AS validated
      FROM m LEFT JOIN p ON p.account_id=m.account_id AND p.event_at>=m.event_at AND p.event_at<=m.promised_date
      GROUP BY m.ptp_id)
SELECT month, COUNT(*) AS ptp_matured,
       100.0*SUM(status='KEPT')/COUNT(*) AS ptp_recorded_kept_pct_of_matured,
       100.0*SUM(validated)/COUNT(*) AS ptp_paid_in_window_upper_pct
FROM v WHERE month >= '2026-01' GROUP BY 1 ORDER BY 1;
