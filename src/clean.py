"""
Cleaning pipeline for the CredResolve collections assignment.

Run from the repository root:   python src/clean.py

Reads  : collections_30k_dataset/*.csv   (raw files are NEVER modified)
Writes : golden/*.csv            cleaned tables
         rejects/*.csv           every row removed or merged, with a reason
         reports/cleaning_summary.csv and .md
"""
import os
import pandas as pd

RAW, GOLD, REJ, REP = "collections_30k_dataset", "golden", "rejects", "reports"
for folder in (GOLD, REJ, REP):
    os.makedirs(folder, exist_ok=True)

summary = []     # one line per table / rule
rejected = {}    # table -> list of reject DataFrames


def read(name, dates=()):
    return pd.read_csv(f"{RAW}/{name}.csv", parse_dates=list(dates), low_memory=False)


def add_summary(table, rule, rows, note=""):
    summary.append({"table": table, "step": rule, "rows": int(rows), "note": note})


def reject(table, df, reason):
    if len(df):
        out = df.copy()
        out["reject_reason"] = reason
        rejected.setdefault(table, []).append(out)


def dedupe_by_id(df, key, table, coalesce_cols=()):
    """
    1) Exact duplicate rows (every column identical)  -> dropped, logged.
    2) Same ID but different content (conflict)       -> NOT blindly dropped:
         - for columns in coalesce_cols, a non-null value fills a null one
         - the first-ingested row is kept, the other versions are logged
    """
    add_summary(table, "raw rows", len(df))
    exact = df.duplicated(keep="first")
    reject(table, df[exact], "exact_duplicate_row")
    add_summary(table, "removed: exact duplicate rows", exact.sum())
    df = df[~exact].copy()

    dup_ids = df[key].duplicated(keep=False)
    conflicts = df[dup_ids]
    n_conf_ids = conflicts[key].nunique()
    filled = 0
    for col in coalesce_cols:
        best = df.groupby(key)[col].transform(lambda s: s.dropna().iloc[0] if s.notna().any() else pd.NA)
        need = df[col].isna() & best.notna() & df[key].duplicated(keep=False)
        filled += int(need.sum())
        df.loc[df[col].isna() & best.notna(), col] = best
    later = df[key].duplicated(keep="first")
    reject(table, df[later], "conflicting_id_later_version_merged")
    add_summary(table, f"conflicting {key} (same ID, different content)", n_conf_ids,
                "kept first-ingested row; null fields filled from other version")
    add_summary(table, "removed: later versions of conflicting IDs", later.sum())
    add_summary(table, "corrected: null fields filled from duplicate", filled)
    return df[~later].copy()


# ---------------------------------------------------------------- accounts
acc = read("accounts", ["opened_at"])
add_summary("accounts", "raw rows", len(acc))
acc["borrower_id_missing"] = acc.borrower_id.isna()
bor_raw = read("borrowers")
acc["borrower_not_in_borrowers"] = acc.borrower_id.notna() & ~acc.borrower_id.isin(bor_raw.borrower_id)
acc["dpd_bucket"] = pd.cut(acc.dpd, [-1, 0, 30, 60, 90, 1000],
                           labels=["0", "1-30", "31-60", "61-90", "90+"]).astype(str)
add_summary("accounts", "flagged: borrower_id missing (kept)", acc.borrower_id_missing.sum(),
            "not imputed: borrower_id in other tables does not match accounts (see report)")
add_summary("accounts", "flagged: borrower_id not found in borrowers (kept)", acc.borrower_not_in_borrowers.sum())
add_summary("accounts", "golden rows", len(acc))
acc.to_csv(f"{GOLD}/accounts_clean.csv", index=False)

# ---------------------------------------------------------------- payments
pay = read("payments", ["event_at"])
pay = dedupe_by_id(pay, "payment_id", "payments", coalesce_cols=["payment_reference"])
pay["is_success"] = pay.payment_status.eq("SUCCESS")           # only SUCCESS counts as recovery
pay["missing_reference"] = pay.payment_reference.isna()
pay = pay.merge(acc[["account_id", "outstanding_amount", "status"]].rename(
    columns={"status": "account_status"}), on="account_id", how="left")
pay["amount_gt_outstanding"] = pay.amount > pay.outstanding_amount
pay["ts_timezone_known"] = False                                # payments carry no timezone column
add_summary("payments", "flagged: SUCCESS payments > outstanding amount (kept)",
            (pay.is_success & pay.amount_gt_outstanding).sum())
add_summary("payments", "flagged: SUCCESS but still no payment_reference (kept)",
            (pay.is_success & pay.missing_reference).sum())
add_summary("payments", "golden rows", len(pay))
add_summary("payments", "golden rows with status SUCCESS (valid recovery)", pay.is_success.sum())
pay.to_csv(f"{GOLD}/payments_clean.csv", index=False)

# ---------------------------------------------------------------- calls
calls = read("calls", ["event_at"])
calls = dedupe_by_id(calls, "call_id", "calls", coalesce_cols=["agent_id"])
calls["agent_missing"] = calls.agent_id.isna()
# Each call row has its own timezone label, so the zone is KNOWN. ASSUMPTION: event_at is local
# wall-clock time in that labelled zone. Original event_at is kept untouched.
calls["ts_timezone_known"] = calls.timezone.isin(["UTC", "Asia/Kolkata", "Asia/Dubai"])
offset = {"UTC": 0, "Asia/Kolkata": 330, "Asia/Dubai": 240}      # minutes ahead of UTC
calls["event_at_utc_assumed"] = calls.event_at - pd.to_timedelta(calls.timezone.map(offset), unit="m")
calls["in_payment_window"] = calls.event_at.between("2026-01-01", "2026-08-08 23:59:59")
add_summary("calls", "flagged: agent_id still missing (kept)", calls.agent_missing.sum())
add_summary("calls", "flagged: outside 1-Jan..8-Aug-2026 window (kept, flagged)", (~calls.in_payment_window).sum())
add_summary("calls", "golden rows", len(calls))
calls.to_csv(f"{GOLD}/calls_clean.csv", index=False)

# ---------------------------------------------------------------- promises to pay
ptp = read("promises_to_pay", ["event_at", "promised_date"])
add_summary("promises_to_pay", "raw rows", len(ptp))
add_summary("promises_to_pay", "duplicate ptp_id", ptp.ptp_id.duplicated().sum(), "none found")
ptp["ts_timezone_known"] = False
add_summary("promises_to_pay", "flagged: promised_date before event_at", (ptp.promised_date < ptp.event_at).sum())
add_summary("promises_to_pay", "golden rows", len(ptp))
ptp.to_csv(f"{GOLD}/promises_to_pay_clean.csv", index=False)

# ---------------------------------------------------------------- borrowers
# ENTITY RESOLUTION IS NOT POSSIBLE with this table: the same borrower_id appears with different
# names / cities / states, and updated_at is often EARLIER than created_at. So we do NOT pick a
# "latest" record as truth. We keep every row (except byte-identical duplicates) and label the problem.
bor = read("borrowers", ["created_at", "updated_at"])
add_summary("borrowers", "raw rows", len(bor))
exact = bor.duplicated(keep="first")
reject("borrowers", bor[exact], "exact_duplicate_row")
add_summary("borrowers", "removed: exact duplicate rows", exact.sum())
bor = bor[~exact].copy()
bor["rows_for_this_id"] = bor.groupby("borrower_id").borrower_id.transform("size")
bor["id_conflict"] = bor.rows_for_this_id > 1
bor["updated_before_created"] = bor.updated_at < bor.created_at
bor["entity_resolution_status"] = bor.id_conflict.map({True: "UNRESOLVED_MULTIPLE_VERSIONS", False: "SINGLE_VERSION_UNVERIFIED"})
bor["phone"] = bor.phone.round().astype("Int64").astype("string")
add_summary("borrowers", "borrower_ids with >1 DIFFERENT row", bor[bor.id_conflict].borrower_id.nunique(),
            "ID is not a valid key; no record is treated as verified truth")
add_summary("borrowers", "rows with updated_at earlier than created_at", bor.updated_before_created.sum(),
            "makes 'latest updated_at' rule unsafe")
add_summary("borrowers", "golden rows (all versions kept, labelled)", len(bor))
bor.to_csv(f"{GOLD}/borrowers_clean.csv", index=False)

# ---------------------------------------------------------------- agents
# Same story: agent_id maps to ~30 different employee codes / names / vendors / teams. All rows kept.
ag = read("agents", ["joined_at", "updated_at"])
add_summary("agents", "raw rows", len(ag))
add_summary("agents", "unique agent_id", ag.agent_id.nunique())
add_summary("agents", "avg employee_codes per agent_id", round(ag.groupby("agent_id").employee_code.nunique().mean(), 1),
            "same agent_id carries many employee codes / names / vendors / teams")
add_summary("agents", "avg agent_ids per employee_code", round(ag.groupby("employee_code").agent_id.nunique().mean(), 1),
            "no consistent crosswalk between the two identifiers")
ag["versions_for_this_agent_id"] = ag.groupby("agent_id").agent_id.transform("size")
ag["entity_resolution_status"] = "UNRESOLVED_MULTIPLE_VERSIONS"
add_summary("agents", "golden rows (all versions kept, labelled)", len(ag),
            "agent tenure / team / vendor NOT usable; agent_id used only as a grouping key")
ag.to_csv(f"{GOLD}/agents_clean.csv", index=False)

# ---------------------------------------------------------------- write logs
for table, parts in rejected.items():
    pd.concat(parts).to_csv(f"{REJ}/{table}_rejected.csv", index=False)

s = pd.DataFrame(summary)
s.to_csv(f"{REP}/cleaning_summary.csv", index=False)
with open(f"{REP}/cleaning_summary.md", "w", encoding="utf-8") as f:
    f.write("# Cleaning summary (auto-generated by src/clean.py)\n\n")
    for table, g in s.groupby("table", sort=False):
        f.write(f"## {table}\n\n| step | rows | note |\n|---|---:|---|\n")
        for _, r in g.iterrows():
            f.write(f"| {r.step} | {r.rows:,} | {r.note} |\n")
        f.write("\n")
print(s.to_string(index=False))
