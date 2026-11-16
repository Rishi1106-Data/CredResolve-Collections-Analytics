"""
PTP (promise-to-pay) validation.   Run from repo root:  python src/ptp_validation.py
Also imported by src/metrics.py.

QUESTION: of the promises that have had time to come due, how many were followed by a real
SUCCESS payment on the same account?

WHY THE OLD CHECK WAS TOO LOOSE
  An account can hold several promises at once (3,675 accounts hold 8,143 of the 18,000 promises). One
  payment can then fall inside the windows of more than one promise and be counted as "proof" for
  all of them. We therefore report several versions side by side and treat them as a RANGE.

DEFINITIONS (all use the de-duplicated SUCCESS payments only)
  window            = [promise created at, promised_date]   (optionally + a grace period)
  matured           = promised_date (+ grace) <= observation cutoff. Un-matured promises are EXCLUDED
                      because their outcome is not observable yet.
  overlap_allowed   = >=1 SUCCESS payment in the window. A payment may count for several promises.
                      -> UPPER bound.
  one_to_one        = each payment may be credited to at most ONE promise on the account (the one with
                      the earliest promised_date whose window contains it). -> conservative.
  full_amount       = rupee "waterfall": payment rupees are applied to the earliest-due promise
                      until its promised_amount is covered, the remainder goes to the next promise.
                      A promise is fully kept only if its promised_amount is covered.
  unambiguous       = promises whose window overlaps NO other promise window on the same account.
                      Here attribution is not in doubt.
LIMITS: payments carry no promise ID, so a payment inside the window is "consistent with" a kept
promise, not proof of it. Timestamps have no timezone. A promise that was kept by a payment made
before it was created, or after promised_date + grace, is not seen.
"""
import numpy as np
import pandas as pd

CUTOFF = pd.Timestamp("2026-08-08 23:59:59")     # last payment / promise timestamp in the data


def validate_ptps(ptp, ok, cutoff=CUTOFF, grace_days=0):
    """Return one row per MATURED promise with the validation flags. ptp: golden promises; ok: SUCCESS payments."""
    g = pd.Timedelta(days=grace_days)
    p = ptp.copy()
    p["window_end"] = p.promised_date + g
    p["matured"] = p.window_end <= cutoff
    m = p[p.matured].copy()

    pay = ok[["payment_id", "account_id", "event_at", "amount"]].rename(columns={"event_at": "pay_at"})
    link = m[["ptp_id", "account_id", "event_at", "window_end", "promised_date", "promised_amount"]].merge(pay, on="account_id")
    link = link[(link.pay_at >= link.event_at) & (link.pay_at <= link.window_end)].copy()

    # A) overlap allowed
    m["paid_overlap_allowed"] = m.ptp_id.isin(link.ptp_id)
    # how often is one payment inside several promise windows?
    per_pay = link.groupby("payment_id").ptp_id.nunique()
    m.attrs["payments_in_any_window"] = int(len(per_pay))
    m.attrs["payments_in_2plus_windows"] = int((per_pay >= 2).sum())
    shared = link[link.payment_id.isin(per_pay[per_pay >= 2].index)].ptp_id.unique()
    m["shares_payment_with_other_ptp"] = m.ptp_id.isin(shared)

    # B) one payment -> one promise (earliest promised_date first); C) rupee waterfall
    link = link.sort_values(["payment_id", "promised_date", "event_at", "ptp_id"])
    first = link.groupby("payment_id").head(1)
    m["paid_one_to_one"] = m.ptp_id.isin(first.ptp_id)

    covered = dict.fromkeys(m.ptp_id, 0.0)
    need = m.set_index("ptp_id").promised_amount.to_dict()
    for _, grp in link.sort_values(["pay_at", "payment_id"]).groupby("payment_id", sort=False):
        left = float(grp.amount.iloc[0])
        for r in grp.sort_values(["promised_date", "event_at", "ptp_id"]).itertuples():
            if left <= 0:
                break
            take = min(left, max(need[r.ptp_id] - covered[r.ptp_id], 0.0))
            covered[r.ptp_id] += take
            left -= take
    m["covered_rs"] = m.ptp_id.map(covered)
    m["paid_full_amount_waterfall"] = m.covered_rs >= m.promised_amount - 1e-6

    # D) unambiguous subset: no other promise window on the same account overlaps this one
    w = m.sort_values(["account_id", "event_at"])[["ptp_id", "account_id", "event_at", "window_end"]]
    # overlap uses ALL promises of the account (matured or not), not only the matured ones
    allw = p[["ptp_id", "account_id", "event_at", "window_end"]]
    x = w.merge(allw, on="account_id", suffixes=("", "_o"))
    x = x[(x.ptp_id != x.ptp_id_o) & (x.event_at <= x.window_end_o) & (x.event_at_o <= x.window_end)]
    m["window_overlaps_other_ptp"] = m.ptp_id.isin(x.ptp_id)
    return m, p


def summarise(m, p, label):
    rows = []
    def add(measure, mask, col):
        d = m[mask]
        rows.append({"grace_days": label, "measure": measure, "n_promises": len(d),
                     "pct": round(d[col].mean() * 100, 2) if len(d) else np.nan})
    allm = m.ptp_id.notna()
    add("paid in window, overlap allowed (UPPER bound)", allm, "paid_overlap_allowed")
    add("paid in window, one payment -> one promise (CONSERVATIVE)", allm, "paid_one_to_one")
    add("promised amount fully covered (rupee waterfall)", allm, "paid_full_amount_waterfall")
    add("paid in window, only promises with NO overlapping promise on the account", ~m.window_overlaps_other_ptp, "paid_overlap_allowed")
    return rows


def run(ptp, ok, cutoff=CUTOFF):
    out, base = {}, None
    for gd in (0, 3):
        m, p = validate_ptps(ptp, ok, cutoff, gd)
        out[gd] = (m, p)
    return out


if __name__ == "__main__":
    pay = pd.read_csv("golden/payments_clean.csv", parse_dates=["event_at"])
    ptp = pd.read_csv("golden/promises_to_pay_clean.csv", parse_dates=["event_at", "promised_date"])
    ok = pay[pay.is_success]
    res = run(ptp, ok)
    m0, p0 = res[0]
    lines = ["# PTP validation (generated by src/ptp_validation.py)\n",
             f"- Promises: {len(p0):,} | matured by {CUTOFF:%d %b %Y} (promised_date <= cutoff): {len(m0):,} | "
             f"EXCLUDED as not yet matured: {int((~p0.matured).sum()):,}",
             f"- Matured promises whose recorded status is still OPEN (stale): {int((m0.status == 'OPEN').sum()):,}; CANCELLED: {int((m0.status == 'CANCELLED').sum()):,}",
             f"- Promises on accounts that hold more than one promise: {int(p0.account_id.duplicated(keep=False).sum()):,} of {len(p0):,}",
             f"- SUCCESS payments inside at least one matured promise window: {m0.attrs['payments_in_any_window']:,}; "
             f"inside TWO OR MORE windows of the same account: {m0.attrs['payments_in_2plus_windows']:,} "
             f"(touching {int(m0.shares_payment_with_other_ptp.sum()):,} promises) -> the double-counting risk is real but small here",
             f"- Matured promises with an overlapping window on the same account: {int(m0.window_overlaps_other_ptp.sum()):,} of {len(m0):,}\n",
             "## Kept rate among matured promises\n"]
    rec = pd.DataFrame([{"grace_days": 0, "measure": "RECORDED status = KEPT (as stored, not reliable)", "n_promises": len(m0),
                         "pct": round((m0.status == "KEPT").mean() * 100, 2)}])
    tab = pd.concat([rec] + [pd.DataFrame(summarise(*res[g], g)) for g in (0, 3)], ignore_index=True)
    lines.append(tab.to_markdown(index=False))
    # by recorded status (one-to-one measure, grace 0)
    bs = m0.groupby("status").agg(matured=("ptp_id", "size"), paid_overlap_allowed_pct=("paid_overlap_allowed", "mean"),
                                  paid_one_to_one_pct=("paid_one_to_one", "mean"), full_amount_pct=("paid_full_amount_waterfall", "mean"))
    for c in bs.columns[1:]:
        bs[c] = (bs[c] * 100).round(2)
    lines += ["\n## By recorded status (grace 0)\n", bs.to_markdown()]
    # placebo: same-length window starting at promised_date, using only promises where that window is fully observed
    pay_ = ok[["account_id", "event_at"]].rename(columns={"event_at": "pay_at"})
    q = m0.assign(len_d=(m0.promised_date - m0.event_at))
    q = q[q.promised_date + q.len_d <= CUTOFF]
    z = q[["ptp_id", "account_id", "promised_date", "len_d"]].merge(pay_, on="account_id")
    z = z[(z.pay_at > z.promised_date) & (z.pay_at <= z.promised_date + z.len_d)]
    plc = q.ptp_id.isin(z.ptp_id).mean() * 100
    real = q.paid_overlap_allowed.mean() * 100
    lines += [f"\n## Placebo\n\nSame-length window placed immediately AFTER promised_date (n={len(q):,} promises where it is fully observed): "
              f"{plc:.2f}% have a SUCCESS payment, versus {real:.2f}% inside the real window for the same promises. "
              "If a promise really raised payment probability, the real window should beat the placebo clearly."]
    lines += ["\n## How to read this\n",
              "- Report the kept rate as a RANGE (conservative to upper bound), not one number.",
              "- A payment in the window is *consistent with* a kept promise; payments carry no promise ID, so attribution cannot be proven.",
              "- Rates are low because only a few promises are followed by ANY payment; recorded KEPT status is not supported by payment data.",
              "- Promises created in Jul/Aug are maturity-censored (only short-horizon promises have matured): compare Jan-Jun only."]
    open("reports/ptp_validation.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    tab.to_csv("reports/ptp_validation.csv", index=False)
    print("\n".join(lines))
