"""Re-compute key metrics from RAW CSVs with SQL (SQLite) and compare to reports/monthly_metrics.csv.
Run from repo root:  python src/validate.py"""
import sqlite3, re, pandas as pd, numpy as np
con = sqlite3.connect(":memory:")
for t in ["payments", "calls", "promises_to_pay"]:
    pd.read_csv(f"collections_30k_dataset/{t}.csv", dtype=str).assign().pipe(
        lambda d: d.astype({c: float for c in ["amount"] if c in d}) if "amount" in d else d
    ).to_sql(t, con, index=False)
sql = open("SQL/metric_validation.sql").read()
queries = dict(re.findall(r"-- name: (\w+)\n(.*?)(?=\n-- name:|\Z)", sql, re.S))
m = pd.read_csv("reports/monthly_metrics.csv", index_col="month")
rows = []
for name, q in queries.items():
    r = pd.read_sql(q, con).set_index("month")
    for col in r.columns:
        for mo in r.index:
            if mo in m.index:
                a, b = float(r.loc[mo, col]), float(m.loc[mo, col])
                rows.append({"query": name, "metric": col, "month": mo, "sql_raw": round(a, 4), "python_golden": round(b, 4), "match": bool(abs(a - b) <= 0.0006)})  # CSV is rounded to 3 decimals
out = pd.DataFrame(rows); out.to_csv("reports/metric_validation.csv", index=False)
print(out.groupby(["query", "metric"]).match.agg(["sum", "count"]).to_string())
print("ALL MATCH" if out.match.all() else "MISMATCHES:\n" + out[~out.match].to_string())
