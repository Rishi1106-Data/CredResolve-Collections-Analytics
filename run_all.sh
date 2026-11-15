#!/usr/bin/env bash
# Reproduce everything from the repository root:  bash run_all.sh   (about 1-2 minutes)
set -e
python src/clean.py              # raw -> golden/, rejects/, reports/cleaning_summary.*
python src/ptp_validation.py     # reports/ptp_validation.md/.csv (maturity-filtered, one-to-one, placebo)
python src/metrics.py            # reports/monthly_metrics.csv, statistical_tests.md, feb_mar_decomposition.csv, headline_numbers.json
python src/denominators.py       # reports/denominator_audit.md, denominator_by_status.csv
python src/validate.py           # re-compute from RAW with SQL, compare (reports/metric_validation.csv)
python src/investigate.py        # attribution / channel / PTP checks (printed)
python src/drivers.py            # reports/driver_screen.csv (incl. WhatsApp/SMS/field screens)
python src/investment_sizing.py  # reports/investment_sizing.md, experiment_design.md, investment_recommendation.md
python src/make_dashboard.py     # dashboard/dashboard.html
python src/make_architecture.py  # docs/architecture.png/.svg
python src/check_consistency.py  # fails if a deliverable disagrees with reports/headline_numbers.json
