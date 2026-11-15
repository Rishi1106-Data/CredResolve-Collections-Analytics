-- CredResolve: metric validation queries (MySQL 8.0)
-- Recalculates recovery, outbound-call and PTP metrics from the raw tables.
--
-- IMPORTANT IMPORT REQUIREMENT
-- `import_row_id` must be assigned while importing each CSV (for example, as an
-- AUTO_INCREMENT column in an empty staging table). Do NOT add AUTO_INCREMENT
-- after the data has already been loaded and assume it recreates CSV row order:
-- MySQL does not guarantee that existing physical row order is the source order.
--
-- Expected columns used below:
-- payments: payment_id, account_id, event_at, payment_status, amount, import_row_id
-- calls:    call_id, account_id, event_at, direction, call_status, import_row_id
-- promises_to_pay: ptp_id, account_id, event_at, promised_date, status
--
-- Reporting cutoff: source data is available through 8 Aug 2026.
-- The exclusive upper bound below includes all of 8 Aug and excludes later rows.
-- August is therefore a partial month and must not be compared with full months
-- without accounting for the shorter observation period.


-- STEP 0: Import / key checks
-- Run these checks after loading. Both import_row_id columns should be populated
-- and unique. If they are not, re-import into staging tables that assign the ID
-- during ingestion before running the metric queries.

SELECT
    'payments' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(import_row_id) AS rows_with_import_id,
    COUNT(DISTINCT import_row_id) AS distinct_import_ids
FROM payments
UNION ALL
SELECT
    'calls' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(import_row_id) AS rows_with_import_id,
    COUNT(DISTINCT import_row_id) AS distinct_import_ids
FROM calls;


-- STEP 1: Duplicate-key audit
-- This reports repeated IDs. It does not automatically resolve conflicting
-- duplicate records or merge missing fields from later rows.

SELECT
    'payments' AS table_name,
    COUNT(*) AS duplicated_ids
FROM (
    SELECT payment_id
    FROM payments
    GROUP BY payment_id
    HAVING COUNT(*) > 1
) AS d
UNION ALL
SELECT
    'calls' AS table_name,
    COUNT(*) AS duplicated_ids
FROM (
    SELECT call_id
    FROM calls
    GROUP BY call_id
    HAVING COUNT(*) > 1
) AS d;


-- STEP 2: Monthly recovery
-- Deduplication rule: retain the earliest imported row for each payment_id.
-- This is deterministic only when import_row_id was assigned during ingestion.
-- SUCCESS payments only. Same reporting cutoff as the calls query.

WITH payment_rank AS (
    SELECT
        payment_id,
        account_id,
        event_at,
        payment_status,
        amount,
        ROW_NUMBER() OVER (
            PARTITION BY payment_id
            ORDER BY import_row_id
        ) AS row_num
    FROM payments
), clean_payments AS (
    SELECT
        payment_id,
        account_id,
        event_at,
        payment_status,
        amount
    FROM payment_rank
    WHERE row_num = 1
)
SELECT
    DATE_FORMAT(event_at, '%Y-%m') AS month,
    SUM(amount) / 10000000.0 AS recovery_cr,
    COUNT(*) AS n_success_payments,
    COUNT(DISTINCT account_id) AS accounts_paying,
    AVG(amount) AS avg_ticket_rs
FROM clean_payments
WHERE payment_status = 'SUCCESS'
  AND event_at >= '2026-01-01'
  AND event_at <  '2026-08-09'
GROUP BY DATE_FORMAT(event_at, '%Y-%m')
ORDER BY month;


-- STEP 3: Monthly outbound calls
-- Deduplication rule: retain the earliest imported row for each call_id.
-- Contact rate = ANSWERED outbound calls / all outbound calls.

WITH call_rank AS (
    SELECT
        call_id,
        account_id,
        event_at,
        direction,
        call_status,
        ROW_NUMBER() OVER (
            PARTITION BY call_id
            ORDER BY import_row_id
        ) AS row_num
    FROM calls
), clean_calls AS (
    SELECT
        call_id,
        account_id,
        event_at,
        direction,
        call_status
    FROM call_rank
    WHERE row_num = 1
)
SELECT
    DATE_FORMAT(event_at, '%Y-%m') AS month,
    COUNT(*) AS outbound_calls,
    100.0 * SUM(CASE WHEN call_status = 'ANSWERED' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) AS contact_rate_call_pct,
    COUNT(DISTINCT account_id) AS accounts_worked_outbound
FROM clean_calls
WHERE direction = 'OUTBOUND'
  AND event_at >= '2026-01-01'
  AND event_at <  '2026-08-09'
GROUP BY DATE_FORMAT(event_at, '%Y-%m')
ORDER BY month;


-- STEP 4: PTP validation
-- Only promises whose promised_date had matured by the data cutoff are included.
-- Two payment-evidence measures are shown:
--   (a) upper bound: a successful payment may support more than one PTP;
--   (b) one-payment-one-PTP: each successful payment is assigned to at most one
--       eligible PTP, choosing the most recently created eligible promise.
--
-- Neither measure proves that the payment was caused by the promise. They are
-- payment-in-window evidence checks. Recorded KEPT status is reported separately.

WITH payment_rank AS (
    SELECT
        payment_id,
        account_id,
        event_at,
        payment_status,
        ROW_NUMBER() OVER (
            PARTITION BY payment_id
            ORDER BY import_row_id
        ) AS row_num
    FROM payments
), clean_success_payments AS (
    SELECT
        payment_id,
        account_id,
        event_at
    FROM payment_rank
    WHERE row_num = 1
      AND payment_status = 'SUCCESS'
      AND event_at >= '2026-01-01'
      AND event_at <  '2026-08-09'
), matured_ptp AS (
    SELECT
        ptp_id,
        account_id,
        event_at,
        promised_date,
        status
    FROM promises_to_pay
    WHERE promised_date <= '2026-08-08 23:59:59'
      AND event_at >= '2026-01-01'
      AND event_at <  '2026-08-09'
), upper_bound_check AS (
    SELECT
        m.ptp_id,
        DATE_FORMAT(m.event_at, '%Y-%m') AS month,
        m.status,
        MAX(CASE WHEN p.payment_id IS NOT NULL THEN 1 ELSE 0 END)
            AS paid_in_window_upper
    FROM matured_ptp AS m
    LEFT JOIN clean_success_payments AS p
        ON p.account_id = m.account_id
       AND p.event_at >= m.event_at
       AND p.event_at <= m.promised_date
    GROUP BY m.ptp_id, DATE_FORMAT(m.event_at, '%Y-%m'), m.status
), payment_ptp_candidates AS (
    SELECT
        p.payment_id,
        m.ptp_id,
        ROW_NUMBER() OVER (
            PARTITION BY p.payment_id
            ORDER BY m.event_at DESC, m.ptp_id
        ) AS payment_assignment_rank
    FROM clean_success_payments AS p
    INNER JOIN matured_ptp AS m
        ON m.account_id = p.account_id
       AND p.event_at >= m.event_at
       AND p.event_at <= m.promised_date
), one_payment_one_ptp AS (
    SELECT
        payment_id,
        ptp_id
    FROM payment_ptp_candidates
    WHERE payment_assignment_rank = 1
), conservative_check AS (
    SELECT
        m.ptp_id,
        DATE_FORMAT(m.event_at, '%Y-%m') AS month,
        m.status,
        MAX(CASE WHEN a.payment_id IS NOT NULL THEN 1 ELSE 0 END)
            AS paid_in_window_one_to_one
    FROM matured_ptp AS m
    LEFT JOIN one_payment_one_ptp AS a
        ON a.ptp_id = m.ptp_id
    GROUP BY m.ptp_id, DATE_FORMAT(m.event_at, '%Y-%m'), m.status
), combined AS (
    SELECT
        u.ptp_id,
        u.month,
        u.status,
        u.paid_in_window_upper,
        c.paid_in_window_one_to_one
    FROM upper_bound_check AS u
    INNER JOIN conservative_check AS c
        ON c.ptp_id = u.ptp_id
)
SELECT
    month,
    COUNT(*) AS ptp_matured,
    100.0 * SUM(CASE WHEN status = 'KEPT' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) AS ptp_recorded_kept_pct_of_matured,
    100.0 * SUM(paid_in_window_upper)
        / NULLIF(COUNT(*), 0) AS ptp_paid_in_window_upper_pct,
    100.0 * SUM(paid_in_window_one_to_one)
        / NULLIF(COUNT(*), 0) AS ptp_paid_in_window_one_payment_one_ptp_pct
FROM combined
GROUP BY month
ORDER BY month;


-- INTERPRETATION NOTES
-- 1. The first-imported-row rule is a deduplication convention, not a conflict
--    resolution strategy. Conflicting duplicates must be reviewed separately.
-- 2. These queries do not merge null fields from later duplicate records.
-- 3. August 2026 is partial (through 8 Aug); label it as partial in reports.
-- 4. The one-payment-one-PTP rule assigns each payment to the most recently
--    created eligible promise. It is a conservative allocation convention,
--    not proof of causal attribution or a definitive business rule.
-- 5. Keep denominator definitions explicit. These queries do not establish an
--    eligible outstanding-balance denominator for a true collection rate.
