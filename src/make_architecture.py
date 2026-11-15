"""Draws docs/architecture.png and docs/architecture.svg (production design). Run from repo root: python src/make_architecture.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(17, 11.6))
ax.set_xlim(0, 170); ax.set_ylim(0, 116); ax.axis("off")
INK, MUT, LINE = "#1f2933", "#52606d", "#9aa5b1"
COL = {"raw": "#f1f3f5", "stg": "#e7f0fb", "cln": "#e3f4ea", "gld": "#fff4d6", "ftr": "#f1e8fb", "met": "#fde8e4", "dsh": "#d9f2f1"}

def box(x, y, w, h, fc, title, lines, tsize=12, lsize=8.1, ec=LINE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6", fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="top", fontsize=tsize, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 7.4, "\n".join(lines), ha="center", va="top", fontsize=lsize, color=INK, linespacing=1.45)

ax.text(85, 113.5, "CredResolve collections analytics: production design", ha="center", fontsize=16, fontweight="bold", color=INK)
ax.text(85, 110, "Raw → Staging → Clean → Golden → Feature → Metrics → Dashboard   (daily batch, payments hourly)", ha="center", fontsize=10.5, color=MUT)

# sources
ax.add_patch(FancyBboxPatch((1, 70), 17, 30, boxstyle="round,pad=0.4,rounding_size=1.6", fc="white", ec=LINE, lw=1.3, ls="--"))
ax.text(9.5, 98.2, "Sources", ha="center", va="top", fontsize=12, fontweight="bold", color=INK)
ax.text(9.5, 93.5, "Telephony vendors\nCRM: accounts,\nborrowers, agents\nPayment gateway\nWhatsApp / SMS\nField app", ha="center", va="top", fontsize=9, color=INK, linespacing=1.5)

W, H, Y = 19.2, 30, 70
xs = [21 + i * 21.2 for i in range(7)]
stages = [
    ("RAW", "raw", ["append-only, immutable", "+ ingested_at, source,", "batch_id", "", "PK: (source, batch_id,", "row_no)"]),
    ("STAGING", "stg", ["typed columns", "schema_version resolved", "contract check on load", "", "PK: source business key", "(payment_id, call_id…)"]),
    ("CLEAN", "cln", ["exact + conflicting-ID", "de-duplication", "timestamps → UTC", "disposition code map", "rejects table with reason", "PK enforced"]),
    ("GOLDEN", "gld", ["entity resolution", "(borrower_key, agent_key", "crosswalks)", "valid payments only", "(status = SUCCESS)", "unresolved rows labelled"]),
    ("FEATURE", "ftr", ["account-day, agent-day", "calls, answered, PTP,", "paid flags", "", "PK: (account_id, date)", "built incrementally"]),
    ("METRICS", "met", ["versioned definitions:", "recovery per calendar day,", "paying-account share,", "validated PTP range,", "contact rate", "PK: (metric, grain, date)"]),
    ("DASHBOARD", "dsh", ["one screen, per-day", "recovery (never month", "totals), data-quality", "status, alerts", "", "reads Metrics only"]),
]
for (t, k, ls), x in zip(stages, xs):
    box(x, Y, W, H, COL[k], t, ls)
for i in range(6):
    ax.add_patch(FancyArrowPatch((xs[i] + W + 0.5, Y + H / 2), (xs[i + 1] - 0.5, Y + H / 2), arrowstyle="-|>", mutation_scale=16, lw=1.8, color=INK))
ax.add_patch(FancyArrowPatch((18.6, Y + H / 2), (xs[0] - 0.5, Y + H / 2), arrowstyle="-|>", mutation_scale=16, lw=1.8, color=INK))

# data-quality branch from CLEAN
ax.add_patch(FancyArrowPatch((xs[2] + W / 2, Y - 0.6), (xs[2] + W / 2, 60), arrowstyle="-|>", mutation_scale=13, lw=1.4, color="#c0392b"))
ax.text(xs[2] + W / 2 + 1.2, 64, "rejects", fontsize=8.5, color="#c0392b", va="center")

# cross-cutting band
ax.text(2, 54.5, "Cross-cutting controls (apply to every layer)", fontsize=12, fontweight="bold", color=INK, va="center")
ax.plot([2, 168], [52.2, 52.2], color=LINE, lw=1)
cw, ch, cy1, cy2 = 54.5, 24, 26, 0.5
cx = [2, 57.5, 113]
cross = [
    (cx[0], cy1, "#eef2f6", "Data contracts", ["Each source publishes: schema, primary key, timezone,", "allowed enum values, SLA, owner.", "A breaking change (new column type, new disposition", "code, new schema_version) FAILS ingestion into Staging", "and alerts the owner. It never flows silently."]),
    (cx[1], cy1, "#eef2f6", "Metric definitions + lineage", ["One governed definition per metric: numerator, denominator,", "exclusions, version (reports/metric_definitions.md).", "Every golden row keeps source_table, batch_id, rule_version;", "every metric value keeps definition_version.", "Dashboard number → metric → feature → golden → raw row."]),
    (cx[2], cy1, "#eef2f6", "Data-quality checks", ["Key uniqueness; duplicate rate per batch (alert > 2%);", "status / disposition enums; amount > 0; null-rate of", "payment_reference and agent_id; orphan account_id = 0;", "timezone present; PTP still OPEN after promised_date;", "row counts vs source; freshness per source."]),
    (cx[0], cy2, "#eef2f6", "Incremental processing + late-arriving data", ["Daily batch (payments hourly): merge on business key,", "watermark = max(ingested_at). Re-process the trailing", "35 days every run (reversals, late dispositions).", "Closed days are restated and flagged restated = true."]),
    (cx[1], cy2, "#eef2f6", "Backfills", ["Replay from RAW with a pinned rule_version.", "Write outputs to a NEW version, validate against the", "previous one (row counts, totals), then swap atomically.", "Raw is never edited; rejects are never deleted."]),
    (cx[2], cy2, "#fdf0ee", "Monitoring + anomaly detection", ["Alert on calendar-ADJUSTED values (recovery per day), not", "month totals: rolling 28-day median ± 3 robust SD with a", "day-of-week baseline. A month-length adjustment would have", "prevented the false '+11%' alert. Plus freshness, volume,", "DQ failures → on-call alert."]),
]
for x, y, fc, t, ls in cross:
    ax.add_patch(FancyBboxPatch((x, y), cw, ch, boxstyle="round,pad=0.4,rounding_size=1.4", fc=fc, ec=LINE, lw=1.1))
    ax.text(x + 1.8, y + ch - 1.8, t, fontsize=10.6, fontweight="bold", color=INK, va="top")
    ax.text(x + 1.8, y + ch - 7, "\n".join(ls), fontsize=8.2, color=INK, va="top", linespacing=1.5)

# dashed links from monitoring to Metrics / Dashboard
ax.add_patch(FancyArrowPatch((xs[5] + W / 2, 52.0), (xs[5] + W / 2, Y - 0.6), arrowstyle="<|-|>", mutation_scale=11, lw=1.2, color="#c0392b", ls="--"))
ax.text(xs[5] + W / 2 + 1.2, 61, "anomaly\nchecks", fontsize=8.2, color="#c0392b", va="center")
ax.add_patch(FancyArrowPatch((xs[3] + W / 2, 52.0), (xs[3] + W / 2, Y - 0.6), arrowstyle="<|-|>", mutation_scale=11, lw=1.2, color="#52606d", ls="--"))
ax.text(xs[3] + W / 2 + 1.2, 61, "DQ gate", fontsize=8.2, color="#52606d", va="center")
fig.savefig("docs/architecture.png", dpi=170, bbox_inches="tight", facecolor="white")
fig.savefig("docs/architecture.svg", bbox_inches="tight", facecolor="white")
print("saved docs/architecture.png / .svg")
