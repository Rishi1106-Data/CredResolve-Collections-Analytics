"""Quick driver screen: does contact / payment differ by vendor, hour, strategy, attempt count, DPD, loan type?
Chi-square tests only (simple, explainable). CORRELATION ONLY. Run from repo root: python src/drivers.py"""
import json
import pandas as pd, numpy as np
from scipy import stats
calls = pd.read_csv("golden/calls_clean.csv", parse_dates=["event_at", "event_at_utc_assumed"])
acc = pd.read_csv("golden/accounts_clean.csv"); pay = pd.read_csv("golden/payments_clean.csv")
ven = pd.read_csv("collections_30k_dataset/vendor_telephony.csv"); camp = pd.read_csv("collections_30k_dataset/campaigns.csv")
o = calls[(calls.direction == "OUTBOUND") & calls.in_payment_window].copy()
o["answered"] = o.call_status == "ANSWERED"
o = o.merge(ven[["vendor_id", "vendor_name", "schema_version"]], on="vendor_id", how="left").merge(camp[["campaign_id", "strategy_version", "channel"]], on="campaign_id", how="left")
o["hour_as_stored"] = o.event_at.dt.hour; o["hour_utc_assumed"] = o.event_at_utc_assumed.dt.hour
o["hour_band_stored"] = pd.cut(o.hour_as_stored, [-1, 8, 12, 16, 20, 23], labels=["00-08", "09-12", "13-16", "17-20", "21-23"])
rows = []
def test(label, df, col, y):
    ct = pd.crosstab(df[col], df[y]); chi = stats.chi2_contingency(ct)
    rates = df.groupby(col)[y].mean() * 100
    rows.append({"driver": label, "outcome": y, "groups": len(rates), "min_rate_pct": round(rates.min(), 2), "max_rate_pct": round(rates.max(), 2), "chi2_p": round(chi[1], 3)})
for lab, col in [("telephony vendor", "vendor_name"), ("vendor schema_version", "schema_version"), ("campaign strategy_version", "strategy_version"),
                 ("campaign channel", "channel"), ("hour band (as stored)", "hour_band_stored"), ("call timezone label", "timezone")]:
    test(lab, o, col, "answered")
o = o.merge(acc[["account_id", "dpd_bucket", "loan_type", "risk_segment"]], on="account_id")
for lab, col in [("DPD bucket", "dpd_bucket"), ("loan type", "loan_type"), ("risk segment", "risk_segment")]:
    test(lab, o, col, "answered")
# account-level: paid in window?  attempts per account (selection: accounts with more calls)
n_calls = o.groupby("account_id").size().rename("n_calls"); a = acc.merge(n_calls, on="account_id", how="left").fillna({"n_calls": 0})
a["paid"] = a.account_id.isin(pay[pay.is_success].account_id)
a["attempt_band"] = pd.cut(a.n_calls, [-1, 0, 2, 4, 100], labels=["0", "1-2", "3-4", "5+"])
for lab, col in [("attempts per account (selection-prone)", "attempt_band"), ("DPD bucket", "dpd_bucket"), ("loan type", "loan_type"), ("risk segment", "risk_segment"), ("account status", "status")]:
    test(lab, a, col, "paid")
# ---- digital and field events (screen only; these tables were NOT cleaned: whatsapp_events has 600 exact duplicate rows, removed here)
# Unit = account. For each account take its FIRST event of each type; outcome = SUCCESS payment within 14 days after that event.
# Only events whose 14-day window ends by 8 Aug 2026 are used. CORRELATION ONLY: events are not randomly assigned.
okp = pay[pay.is_success][["account_id", "event_at"]].rename(columns={"event_at": "pay_at"})
def event_screen(label, df, col):
    d = df.drop_duplicates().sort_values("event_at").groupby(["account_id", col]).first().reset_index()
    d = d[d.event_at + pd.Timedelta(days=14) <= pd.Timestamp("2026-08-09")]
    x = d.merge(okp, on="account_id", how="left"); x["hit"] = (x.pay_at >= x.event_at) & (x.pay_at < x.event_at + pd.Timedelta(days=14))
    r = x.groupby(["account_id", col]).hit.max().reset_index()
    ct = pd.crosstab(r[col], r.hit); rates = r.groupby(col).hit.mean() * 100
    rows.append({"driver": label, "outcome": "paid_within_14d_of_first_event", "groups": len(rates), "min_rate_pct": round(rates.min(), 2),
                 "max_rate_pct": round(rates.max(), 2), "chi2_p": round(stats.chi2_contingency(ct)[1], 3)})
R = "collections_30k_dataset/"
event_screen("WhatsApp event type", pd.read_csv(R + "whatsapp_events.csv", parse_dates=["event_at"]), "event_type")
event_screen("SMS event type", pd.read_csv(R + "sms_events.csv", parse_dates=["event_at"]), "event_type")
event_screen("Field visit outcome", pd.read_csv(R + "field_visits.csv", parse_dates=["event_at"]), "outcome")
event_screen("Field visit type", pd.read_csv(R + "field_visits.csv", parse_dates=["event_at"]), "visit_type")
r = pd.DataFrame(rows); r["verdict"] = np.where(r.chi2_p < 0.05, "difference (check multiple testing)", "no evidence of difference")
r.to_csv("reports/driver_screen.csv", index=False); print(r.to_string(index=False))
print("\nTests run:", len(r), "-> with 5% threshold expect ~", round(len(r) * 0.05, 1), "false positives by chance")
H = json.load(open("reports/headline_numbers.json"))
H.update(driver_tests=len(r), driver_hits=int((r.chi2_p < 0.05).sum()), driver_bonferroni=round(0.05 / len(r), 4), driver_expected_false_pos=round(len(r) * 0.05, 1),
         hit_list="; ".join(f"{a} vs {b} (p={p})" for a, b, p in r[r.chi2_p < 0.05][["driver", "outcome", "chi2_p"]].itertuples(index=False)))
json.dump(H, open("reports/headline_numbers.json", "w", encoding="utf-8"), indent=1)
print("Language: NO language field exists in any table, so a language analysis is impossible.")
