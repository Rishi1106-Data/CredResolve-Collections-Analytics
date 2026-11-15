"""Builds dashboard/dashboard.html (one screen, no external libraries). Run from repo root: python src/make_dashboard.py"""
import json
import pandas as pd
H = json.load(open("reports/headline_numbers.json"))
m = pd.read_csv("reports/monthly_metrics.csv", index_col="month").drop("2026-08")
mom_total = pd.Series(H['mom_total_pct'], index=m.index[1:]); mom_day = pd.Series(H['mom_per_day_pct'], index=m.index[1:])   # precise values from metrics.py
months = [pd.Period(x).strftime("%b") for x in mom_total.index]
W, H_, base, scale = 560, 230, 120, 6.0           # 6 px per 1 %
bars = ""
for i, (mo, a, b) in enumerate(zip(months, mom_total, mom_day)):
    x = 40 + i * 88
    for off, v, cls in [(0, a, "tot"), (30, b, "day")]:
        h = abs(v) * scale; y = base - h if v >= 0 else base
        bars += f'<rect class="{cls}" x="{x+off}" y="{y:.1f}" width="26" height="{h:.1f}"/><text x="{x+off+13}" y="{(y-4 if v>=0 else y+h+12):.1f}" text-anchor="middle" class="v">{v:+.1f}</text>'
    bars += f'<text x="{x+28}" y="{H_-8}" text-anchor="middle" class="lab">{mo}</text>'
tot_jan_jul = m.recovery_cr.sum()
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Collections – is recovery really up 11%?</title><style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--card:#f4f5f7;--tot:#c0392b;--day:#1f6feb;--ok:#1a7f37}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14161a;--fg:#eee;--mut:#9aa;--card:#1f2228;--tot:#ff7b6b;--day:#6ea8ff;--ok:#56d364}}}}
body{{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--fg)}}
.wrap{{max-width:1000px;margin:0 auto;padding:16px}}h1{{font-size:20px;margin:0 0 4px}}.sub{{color:var(--mut);font-size:13px;margin-bottom:12px}}
.hero{{background:var(--card);border-radius:10px;padding:14px;display:flex;gap:24px;align-items:center;flex-wrap:wrap}}
.big{{font-size:40px;font-weight:700}}.red{{color:var(--tot)}}.blue{{color:var(--day)}}.lbl{{font-size:12px;color:var(--mut)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:12px 0}}.k{{background:var(--card);border-radius:10px;padding:10px}}.k b{{font-size:22px}}
.row{{display:grid;grid-template-columns:1.3fr 1fr;gap:12px}}@media(max-width:760px){{.row{{grid-template-columns:1fr}}}}
.box{{background:var(--card);border-radius:10px;padding:12px;font-size:14px}}.box h2{{font-size:15px;margin:0 0 6px}}ul{{margin:6px 0 0 18px;padding:0}}
svg{{width:100%;height:auto}}.tot{{fill:var(--tot)}}.day{{fill:var(--day)}}.v{{font-size:10px;fill:var(--fg)}}.lab{{font-size:11px;fill:var(--mut)}}
.dec{{border-left:4px solid var(--ok)}}.foot{{font-size:11px;color:var(--mut);margin-top:10px}}</style></head><body><div class="wrap">
<h1>Is recovery really up 11% month-on-month?</h1><div class="sub">Data: 1 Jan – 8 Aug 2026 (≈7.2 months, not 12). Recovery = SUCCESS payments, de-duplicated. Statistical tests are exploratory.</div>
<div class="hero"><div><div class="big red">+{H['total_change_pct']:.1f}%</div><div class="lbl">Reported: Feb→Mar total recovery (₹{H['feb_cr']} Cr → ₹{H['mar_cr']} Cr)</div></div>
<div><div class="big blue">{H['per_day_change_pct']:+.1f}%</div><div class="lbl">Per calendar day: ₹{H['feb_lakh_per_day']} → ₹{H['mar_lakh_per_day']} lakh/day<br>95% CI {H['block_ci_lo']:+.1f}% to {H['block_ci_hi']:+.1f}% (block bootstrap), p={H['welch_p']}</div></div>
<div style="flex:1;min-width:220px">Verdict: <b>the 11% is a month-length effect, not demonstrated growth</b>. February has 28 days, March 31: calendar days explain about {H['days_share_of_change_pct']:.0f}% of the change. Per-day recovery shows <b>no statistically detectable change</b> (this does not prove it is unchanged).</div></div>
<div class="grid">
<div class="k"><div class="lbl">Recovery Jan–Jul</div><b>₹{tot_jan_jul:.1f} Cr</b><div class="lbl">≈ ₹{H['jan_jul_cr_per_day']} Cr/day; no statistically detectable trend (HAC p={H['trend_hac_p']})</div></div>
<div class="k"><div class="lbl">Contact rate (calls answered)</div><b>{m.contact_rate_call_pct.min():.1f}–{m.contact_rate_call_pct.max():.1f}%</b><div class="lbl">no detectable vendor / channel / hour effect</div></div>
<div class="k"><div class="lbl">PTP kept: recorded vs payment-checked</div><b>{H['ptp_recorded_kept_of_kept_broken_pct']:.0f}% vs {H['ptp_one_to_one_pct']}–{H['ptp_upper_pct']}%</b><div class="lbl">matured promises only; payment in promise window (range)</div></div>
<div class="k"><div class="lbl">Overstatement if mis-counted</div><b>+{H['dup_inflation_pct']:.0f}% / +{H['all_status_inflation_pct']:.0f}%</b><div class="lbl">duplicate rows / all payment statuses</div></div></div>
<div class="row"><div class="box"><h2>Month-on-month change: total vs per day (%)</h2>
<svg viewBox="0 0 {W} {H_}">{bars}<line x1="30" x2="{W-10}" y1="{base}" y2="{base}" stroke="#888" stroke-width="1"/></svg>
<div class="lbl"><span class="blue">■</span> per day &nbsp; <span class="red">■</span> total (as reported). Swings in the total follow month length.</div></div>
<div class="box dec"><h2>Decision</h2><b>Do not commit ₹10 Cr to one option yet.</b> No cost data, no payment-to-campaign link and no measured effect for any option, so no reliable ROI exists.
<ul><li>Fix measurement: IDs, payment-campaign link, timezones, costs</li><li>Run a randomised holdout: ≈{H['n_arm_20']:,} unique accounts per arm to detect +20%, ≈{H['n_arm_50']:,} for +50%</li><li>Report recovery <b>per day</b>, not monthly totals</li></ul>
<div class="lbl" style="margin-top:6px">Break-even (hypothetical keep-rate c): needs ₹10 Cr ÷ c extra recovery = {10/H['annualised_cr']*100:.1f}% of the ₹{H['annualised_cr']} Cr annualised run-rate at c=100%. c is unknown.</div></div></div>
<div class="foot">Recovery ÷ static outstanding is an index (≈{H['den_recovery_pct_static']}% Jan–Jul), not a collection rate: an eligible balance cannot be established ({H['den_nonactive_share_accts_pct']}% of accounts are PAID/CLOSED/WRITEOFF yet receive {H['den_nonactive_share_rs_pct']}% of recovery). Data is synthetic. Details: reports/.</div>
</div></body></html>"""
open("dashboard/dashboard.html", "w", encoding="utf-8").write(html); print("dashboard written")
