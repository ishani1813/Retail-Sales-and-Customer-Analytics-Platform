# Indian Retail Sales Analytics

End-to-end analyst project: raw data → Python cleaning → SQL analysis → Excel summary →
Tableau dashboard → business recommendations. Built to demonstrate the exact toolkit most
requested in Data/BI Analyst screens: **SQL, Excel, Python (Pandas/NumPy), and a BI tool.**

**Dataset:** [Indian Store Data](https://www.kaggle.com/datasets/abuhumzakhan/store-data) (Kaggle)
— ~100,000 retail transactions, 2019–2023, INR, with region/state/city-tier fields.
The full dataset isn't committed to this repo (100K rows of raw data doesn't belong in git
regardless, and it's worth respecting the source's own license) — see
[`data/raw/README.md`](data/raw/README.md) for exact download and setup steps. A small
synthetic sample ships in the repo so the pipeline can be sanity-checked without downloading
anything first.

## Business questions
See [`business_questions.md`](business_questions.md) — six questions a retail operations lead
would actually ask, each mapped to the SQL query that answers it.

## Project structure
```
├── data/
│   ├── raw/              synthetic sample + README with real-dataset download instructions
│   └── processed/        cleaned, normalized tables (customers, products, orders)
├── notebooks/
│   └── 01_data_cleaning.ipynb    load → audit → clean → feature-engineer → normalize
├── sql/
│   ├── 01_schema.sql             PostgreSQL DDL for the normalized tables
│   ├── 02_business_queries.sql   7 queries: joins, window functions, CTEs
│   └── load_data.py              loads the processed CSVs into PostgreSQL
├── excel/
│   ├── regional_performance_summary.xlsx   live SUMIF/SUMIFS formulas, native charts,
│   │                                        and native PivotTables
│   └── update_excel_raw_data.py            refreshes the Raw Data sheet after re-running
│                                            the notebook, without touching the formulas
├── analysis/
│   ├── clustering_segmentation.py   order-level K-means segmentation
│   ├── forecasting.py               Holt-Winters monthly sales forecast
│   └── sparkml_pipeline.py          PySpark/SparkML profit-margin regression
├── tests/
│   └── test_data_quality.py         16 pytest data-quality checks (schema, referential
│                                     integrity, business-logic invariants)
├── app/
│   └── streamlit_app.py             interactive, filterable companion to the Tableau dashboard
├── dashboard/
│   └── BUILD_GUIDE.md    field-by-field spec for the Tableau dashboard
└── business_questions.md
```

## How to run
```bash
# 1. Set up Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Get the real dataset (see data/raw/README.md), save it as
#    data/raw/indian_store_data.csv, then run the cleaning notebook
jupyter nbconvert --to notebook --execute --inplace notebooks/01_data_cleaning.ipynb

# 3. Load it into PostgreSQL (adjust host/port to your own setup)
psql -h localhost -U postgres -d retail_analytics -f sql/01_schema.sql
python sql/load_data.py
psql -h localhost -U postgres -d retail_analytics -f sql/02_business_queries.sql
```
Then:
- Refresh the Excel workbook: `python excel/update_excel_raw_data.py`, then open it in
  Excel or LibreOffice Calc — the SUMIF/SUMIFS formulas and PivotTables recalculate
  automatically against the new data.
- Rebuild the dashboard per [`dashboard/BUILD_GUIDE.md`](dashboard/BUILD_GUIDE.md) — built
  here using Tableau Public's free browser-based Web Authoring, since the Tableau/Power BI
  desktop apps don't run on Linux.
- Explore interactively: `streamlit run app/streamlit_app.py` — filterable KPIs and charts
  alongside the static Tableau dashboard.

## Key findings (from the real ~100K-row dataset)
- **Discounting is eroding margin at real scale.** Average margin drops steadily from 20.0%
  (no discount, 949 orders) to 12.0% (30%+ discount) — a clean, monotonic decline. The 30%+
  tier is also 39% of all orders and generates the single highest total profit (₹118M) of any
  discount bucket, purely on volume.
- **Region, category, and city-tier performance are all essentially flat.** Margin sits in a
  tight ~14.8%–15.2% band everywhere, with no standout or underperforming segment. The
  meaningful variance in this dataset is in discounting behavior, not geography or product mix.
- **Every customer in this dataset has exactly one order** (100,000 orders, 100,000 unique
  customer IDs) — there's no repeat-purchase signal to analyze here, which is itself worth
  calling out rather than glossing over.
- **Data quality flag:** ship-mode analysis shows ~4 days average delivery time across *all
  four* modes, including "Same Day" — almost certainly a labeling artifact in the source data
  rather than a real operational finding. Flagged rather than reported as fact.

## Business recommendations

1. **Segment the discount strategy instead of cutting discounts broadly.** Total profit
   follows a U-shape across discount depth: ₹93M (1–10%) drops to ₹74M (21–30%) before
   jumping to ₹118M (30%+). The 11–30% range is the genuinely worst trade-off — lower margin
   than light discounting, without the volume payoff of deep discounting — and is the range
   worth testing tighter limits on, rather than discounting broadly.
2. **Audit the "Same Day" delivery labeling before using ship-mode data operationally.**
   All four ship modes show ~4 days average delivery time, including Same Day — a same-day
   service that takes 4 days isn't actually same-day. This points to either a data-entry
   error or a fulfillment promise that isn't being met, and should be resolved before any
   customer-facing delivery commitments or ship-mode analysis are built on this data.
3. **Zero repeat-purchase behavior across 100,000 orders means growth is currently 100%
   dependent on new-customer acquisition.** Average order value is ~₹25,000; even a modest
   10% repeat-purchase rate among existing customers would generate ~10,000 additional
   orders, or roughly ₹37.5M in incremental profit at the dataset's ~15% average margin —
   an untapped lever with no execution cost beyond the incentive program itself.

## Extended analysis: segmentation, forecasting, SparkML

Three additional analyses on top of the core pipeline, plus a test suite and an interactive
app — see [`analysis/`](analysis/), [`tests/`](tests/), and [`app/`](app/).

**Order segmentation (K-means).** Segments orders by discount depth, basket size, and margin
rather than customer-level RFM — every customer here has exactly one order, so RFM would be
degenerate (Frequency = 1 for all 100,000 customers). Best k = 2, silhouette 0.149:
"Deep-Discount, Thin-Margin" (53,210 orders, 35.9% avg discount, 11.6% avg margin) vs.
"Full-Price, High-Margin" (46,790 orders, 12.9% avg discount, 18.7% avg margin).

![Segmentation elbow and silhouette](dashboard/segmentation_elbow.png)

**Monthly sales forecasting (Holt-Winters).** 1.4% backtest MAPE on 5 years of real
transaction data, holding out the last 6 months to validate before forecasting forward.

![Sales forecast](dashboard/sales_forecast.png)

**SparkML profit-margin prediction.** Feature engineering reprocessed in PySpark DataFrames;
a GBTRegressor predicts profit margin from order characteristics (RMSE 0.0441, R² 0.29 on
held-out data). Runs on a local Spark session (`local[*]`) — not a real multi-node cluster,
worth saying plainly if asked.

**Data quality tests.** 16 pytest tests covering schema, referential integrity (orders →
customers/products), value ranges, and business-logic invariants (e.g. ship_date ≥
order_date, profit_margin actually equals profit/sales). All 16 pass against the production
dataset.

**Interactive explorer.** `app/streamlit_app.py` — a filterable companion to the static
Tableau dashboard: region/category/city-tier/date filters with KPIs and charts recomputed
live.

Run any of these yourself:
```bash
cd analysis
python clustering_segmentation.py
python forecasting.py --periods 6
python sparkml_pipeline.py
cd ..
pytest tests/ -v
streamlit run app/streamlit_app.py
```

## Dashboard
[Indian Retail Sales Analytics — live on Tableau Public](https://public.tableau.com/app/profile/ishani.sarkar2749/viz/IndianRetailSalesAnalytics_17859999640720/Dashboard1)
