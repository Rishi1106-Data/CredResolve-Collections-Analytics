"""Channel, attribution-window and PTP validation. Run from repo root: python src/investigate.py"""
import pandas as pd, numpy as np
pd.set_option("display.width", 220)
pay = pd.read_csv("golden/payments_clean.csv", parse_dates=["event_at"])
calls = pd.read_csv("golden/calls_clean.csv", parse_dates=["event_at"])
ptp = pd.read_csv("golden/promises_to_pay_clean.csv", parse_dates=["event_at", "promised_date"])
dt = pd.read_csv("collections_30k_dataset/daily_targeting.csv", parse_dates=["target_date"])
camp = pd.read_csv("collections_30k_dataset/campaigns.csv", parse_dates=["start_at", "end_at"])
ok = pay[pay.is_success].copy()

# 1. Attribution window: share of SUCCESS rupees that have ANY call on the account in the N days before
c = calls[["account_id", "event_at", "campaign_id"]].sort_values("event_at")
ok = ok.sort_values("event_at")
a = pd.merge_asof(ok, c.rename(columns={"event_at": "call_at"}), left_on="event_at", right_on="call_at", by="account_id")
a["gap_days"] = (a.event_at - a.call_at).dt.total_seconds() / 86400
for n in [1, 3, 7, 14, 30, 60]:
    hit = a.gap_days.between(0, n)
    print(f"attribution window {n:>2}d: {hit.mean()*100:5.1f}% of SUCCESS payments / {a.amount[hit].sum()/a.amount.sum()*100:5.1f}% of rupees have a prior call")
# placebo: do accounts with a call just AFTER payment look the same? (random timing -> same coverage means window is meaningless)
c2 = c.copy(); c2["event_at"] = c2.event_at
b = pd.merge_asof(ok, c.rename(columns={"event_at": "call_at"}), left_on="event_at", right_on="call_at", by="account_id", direction="forward")
b["gap"] = (b.call_at - b.event_at).dt.total_seconds() / 86400
print("PLACEBO call in N days AFTER payment:", {n: round(b.gap.between(0, n).mean()*100, 1) for n in [7, 30]})
# "latest campaign" attribution vs last-touch before payment
last_camp = c.groupby("account_id").campaign_id.last()
ok["latest_campaign"] = ok.account_id.map(last_camp)
a["last_touch_campaign"] = a.campaign_id.where(a.gap_days.between(0, 30))
cmp_ = pd.DataFrame({"latest_ever": ok.set_index("payment_id").latest_campaign, "last_touch_30d": a.set_index("payment_id").last_touch_campaign})
print("Payments where 'latest campaign ever' differs from last-touch-before-payment (30d):",
      round((cmp_.latest_ever != cmp_.last_touch_30d).mean()*100, 1), "% (incl. no-touch)")

# 2. Payments vs account with no call at all (selection)
called = set(calls.account_id)
print("SUCCESS payment accounts never called:", round((~ok.account_id.isin(called)).mean()*100, 1), "% | share of all accounts never called:",
      round((~pd.read_csv('golden/accounts_clean.csv').account_id.isin(called)).mean()*100, 1), "%")

# 3. Contacted vs not: pay rate
acc = pd.read_csv("golden/accounts_clean.csv")
acc["called"] = acc.account_id.isin(called)
acc["answered"] = acc.account_id.isin(calls[calls.call_status == "ANSWERED"].account_id)
acc["paid"] = acc.account_id.isin(ok.account_id)
print(acc.groupby("answered").paid.agg(["mean", "size"]).round(4).to_string())
print(acc.groupby("called").paid.agg(["mean", "size"]).round(4).to_string())

# 4. Channel performance (campaign channel via call -> campaign) : contact rate; via daily_targeting: recommended channel -> pay in 14d
cc = calls.merge(camp[["campaign_id", "channel", "strategy_version"]], on="campaign_id", how="left")
print(cc[cc.direction == "OUTBOUND"].groupby("channel").call_status.apply(lambda s: round((s == "ANSWERED").mean()*100, 1)).to_dict())
print(cc[cc.direction == "OUTBOUND"].groupby("strategy_version").call_status.apply(lambda s: round((s == "ANSWERED").mean()*100, 1)).to_dict())
t = dt.merge(ok[["account_id", "event_at", "amount"]], on="account_id", how="left")
t["paid14"] = (t.event_at >= t.target_date) & (t.event_at <= t.target_date + pd.Timedelta(days=14))
tt = t.groupby(["target_id", "recommended_channel", "status"]).agg(paid=("paid14", "max"), amt=("amount", lambda s: 0)).reset_index()
print("Target->paid within 14d, by recommended channel:\n", tt.groupby("recommended_channel").paid.agg(["mean", "size"]).round(4).to_string())
print("by target status:\n", tt.groupby("status").paid.agg(["mean", "size"]).round(4).to_string())
# 5. Targeting change over time: monthly mix of target status/channel
dt["m"] = dt.target_date.dt.to_period("M").astype(str)
print((pd.crosstab(dt.m, dt.recommended_channel, normalize="index")*100).round(1).to_string())
print("Distinct accounts targeted:", dt.account_id.nunique(), "of", len(acc), "| targeted rows per account (max):", dt.account_id.value_counts().max())

# 6. PTP validation: see src/ptp_validation.py (maturity-filtered, one-payment-one-promise, range reported). Printed here for convenience.
from ptp_validation import validate_ptps, summarise
m_, p_ = validate_ptps(ptp, ok, grace_days=0)
print("PTP: matured", len(m_), "| un-matured excluded", int((~p_.matured).sum()), "| payments inside 2+ promise windows:", m_.attrs["payments_in_2plus_windows"])
print(pd.DataFrame(summarise(m_, p_, 0)).to_string(index=False))
# 7. disposition PAID vs payments; call status vs disposition consistency
d = pd.read_csv("collections_30k_dataset/call_dispositions.csv").merge(calls[["call_id", "call_status"]], on="call_id")
print("Share of dispositions logged on calls that were NOT answered:", round((d.call_status != "ANSWERED").mean()*100, 1), "%")
print("Late-arriving: PAYMENT rows where event_at < account opened_at:", int((pay.event_at < pd.to_datetime(acc.set_index('account_id').opened_at.reindex(pay.account_id).values)).sum()))
