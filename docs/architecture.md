# Architecture

1. `scripts/download_data.py` retrieves the public source archive.
2. `src/model.py` extracts and normalizes ERP actuals and plan versions.
3. Analytical outputs are written to `data/processed` and `outputs`.
4. Flask exposes the analytical model through JSON endpoints.
5. Plotly renders the management dashboard locally.
6. `scripts/build_excel.py` creates the reproducible Excel FP&A workbook.

No cloud service or AI service is required to run the application.
