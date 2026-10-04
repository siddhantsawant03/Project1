# Enterprise FP&A Performance & Planning Analytics

A portfolio-grade, local FP&A analytics application built with Python, SQL, Excel, Flask and Plotly.

## What it demonstrates
- ERP-style actuals and management P&L
- Budget vs actual variance analysis
- Rolling forecast vs budget
- Cost-centre and G/L driver analysis
- Scenario planning for revenue, COGS, personnel and Opex
- Data-quality controls
- Reproducible Excel FP&A model

## Data
The primary source is the public **Synthetic SAP-Structured FP&A Dataset with Plan Versions**, version 1.1.x. It contains SAP-style double-entry actuals plus Budget and Rolling Forecast plan versions for FY2022–FY2025. The dataset is explicitly synthetic and contains no real company/client/SAP customer data.

Source: https://zenodo.org/records/22206988

The repository intentionally does not redistribute the source dataset. Run:

```powershell
python scripts/download_data.py
python scripts/build_model.py
python scripts/build_excel.py
python app.py
```

If the source ZIP is not downloaded yet, `build_model.py --demo` creates a deterministic small demo dataset so the dashboard can still be explored locally.

## Dashboard
Open http://127.0.0.1:5000

The dashboard is deliberately restrained: a finance-management layout, practical filters, tables, variance indicators, drilldowns and scenario controls rather than a generic AI-generated chart wall.

## Architecture
`raw source -> normalized model -> analytical outputs -> Flask API -> Plotly dashboard`

## Important limitation
The source data is synthetic. Any business interpretation in the dashboard is analytical illustration, not a statement about a real company's performance.
