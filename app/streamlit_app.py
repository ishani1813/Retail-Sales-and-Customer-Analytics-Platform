"""
Interactive Retail Analytics Explorer (Streamlit)
===================================================

A live, filterable companion to the static Tableau dashboard -- lets a
reviewer filter by region/category/date range and see KPIs, the discount-
margin relationship, and (if available) segment and forecast outputs
recompute in real time. Tableau stays the source of truth for the polished
static dashboard; this exists to show backend/interactive-app skills the
Tableau piece can't demonstrate on its own.

Run from the repo root:
    streamlit run app/streamlit_app.py
"""

import os
import subprocess
import sys

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
BUILD_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "build_processed_from_sample.py")

st.set_page_config(page_title="Indian Retail Analytics Explorer", layout="wide")

# data/processed/*.csv is gitignored (real analysis uses the full downloaded
# Kaggle dataset, not something to commit) -- so a fresh clone or a Streamlit
# Cloud deploy has no processed data yet. Same fallback CI already uses:
# build it from the committed synthetic sample instead of crashing.
_using_sample_data = False
if not os.path.exists(os.path.join(DATA_DIR, "orders.csv")):
    _using_sample_data = True
    subprocess.run([sys.executable, BUILD_SCRIPT], check=True)


@st.cache_data
def load_data():
    orders = pd.read_csv(os.path.join(DATA_DIR, "orders.csv"), parse_dates=["order_date"])
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
    df = orders.merge(products, on="product_id", how="left").merge(customers, on="customer_id", how="left")
    return df


if _using_sample_data:
    st.info(
        "Running on the synthetic sample dataset (~3.9K orders), not the full "
        "100K-row Kaggle dataset used for the real analysis and Tableau "
        "dashboard — the full dataset isn't committed to this repo. Numbers "
        "here will differ from the README's reported results; this is here "
        "to demo the app's interactivity, not to reproduce those numbers. "
        "See data/raw/README.md to run this against the real dataset locally.",
        icon="ℹ️",
    )


@st.cache_data
def load_optional(name):
    path = os.path.join(DATA_DIR, name)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def discount_tier(discount):
    if discount == 0:
        return "0%"
    if discount <= 0.10:
        return "1-10%"
    if discount <= 0.20:
        return "11-20%"
    if discount <= 0.30:
        return "21-30%"
    return "30%+"


def main():
    st.title("Indian Retail Sales Analytics — Explorer")
    st.caption(
        "Live filtering companion to the static Tableau dashboard. "
        "Adjust the filters in the sidebar; KPIs and charts recompute immediately."
    )

    df = load_data()

    st.sidebar.header("Filters")
    regions = st.sidebar.multiselect("Region", sorted(df["region"].dropna().unique()), default=None)
    categories = st.sidebar.multiselect("Category", sorted(df["category"].dropna().unique()), default=None)
    city_types = st.sidebar.multiselect("City tier", sorted(df["city_type"].dropna().unique()), default=None)
    date_min, date_max = df["order_date"].min(), df["order_date"].max()
    date_range = st.sidebar.date_input("Order date range", (date_min, date_max), min_value=date_min, max_value=date_max)

    filtered = df.copy()
    if regions:
        filtered = filtered[filtered["region"].isin(regions)]
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if city_types:
        filtered = filtered[filtered["city_type"].isin(city_types)]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        filtered = filtered[(filtered["order_date"] >= start) & (filtered["order_date"] <= end)]

    if filtered.empty:
        st.warning("No orders match the current filters. Widen a filter to see results.")
        return

    # ---------- KPIs ----------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Orders", f"{len(filtered):,}")
    col2.metric("Total Sales", f"₹{filtered['sales'].sum():,.0f}")
    col3.metric("Total Profit", f"₹{filtered['profit'].sum():,.0f}")
    col4.metric("Avg Margin", f"{filtered['profit_margin'].mean():.1%}")

    st.divider()

    left, right = st.columns(2)

    # ---------- discount vs margin (the project's core finding) ----------
    with left:
        st.subheader("Margin by Discount Tier")
        filtered = filtered.copy()
        filtered["discount_tier"] = filtered["discount"].apply(discount_tier)
        tier_order = ["0%", "1-10%", "11-20%", "21-30%", "30%+"]
        tier_summary = (
            filtered.groupby("discount_tier")["profit_margin"].mean().reindex(tier_order).dropna()
        )
        fig, ax = plt.subplots(figsize=(5, 3.5))
        ax.bar(tier_summary.index, tier_summary.values, color="#0F6E62")
        ax.set_ylabel("Avg Profit Margin")
        st.pyplot(fig)

    # ---------- profit by region ----------
    with right:
        st.subheader("Profit by Region")
        region_summary = filtered.groupby("region")["profit"].sum().sort_values()
        fig, ax = plt.subplots(figsize=(5, 3.5))
        ax.barh(region_summary.index, region_summary.values, color="#0F6E62")
        ax.set_xlabel("Total Profit (INR)")
        st.pyplot(fig)

    # ---------- optional: segmentation output, if it's been generated ----------
    segments = load_optional("order_segments.csv")
    if segments is not None:
        st.divider()
        st.subheader("Order Segments (K-Means)")
        seg_summary = segments.groupby("segment_label").agg(
            orders=("order_id", "count"), avg_margin=("profit_margin", "mean")
        ).sort_values("orders", ascending=False)
        st.dataframe(seg_summary.style.format({"avg_margin": "{:.1%}"}))
    else:
        st.caption("Run `analysis/clustering_segmentation.py` to populate the segment breakdown here.")

    # ---------- optional: forecast output, if it's been generated ----------
    forecast = load_optional("sales_forecast.csv")
    if forecast is not None:
        st.divider()
        st.subheader("Sales Forecast (next months)")
        forecast.columns = ["month", "forecast_sales"]
        st.line_chart(forecast.set_index("month"))
    else:
        st.caption("Run `analysis/forecasting.py` to populate the forecast chart here.")

    with st.expander("Show filtered raw data"):
        st.dataframe(filtered.head(500))


if __name__ == "__main__":
    main()
