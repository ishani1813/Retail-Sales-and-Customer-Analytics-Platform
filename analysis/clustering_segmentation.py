"""
Order Segmentation via K-Means Clustering
==========================================

Why order-level, not customer-level RFM:
In the real ~100K-row dataset, every customer has exactly one order (see
README "Key findings"), so there's no repeat-purchase signal to build
Recency/Frequency/Monetary segments from -- Frequency would be 1 for every
single row, which collapses RFM into a meaningless constant. Instead, this
script segments individual ORDERS by their purchasing-pattern characteristics
(basket size, discount depth, margin, delivery profile, category mix). This
answers a real business question: "are there distinct types of purchase
behavior happening on the platform, regardless of who's buying?" -- useful
for merchandising and discount-strategy decisions even with zero repeat
customers.

If you re-run this against a dataset that DOES have repeat customers, see
the `--mode rfm` flag, which switches to classic customer-level RFM
segmentation instead.

Usage:
    python clustering_segmentation.py --input ../data/processed/orders.csv
    python clustering_segmentation.py --input ../data/processed/orders.csv --mode rfm
"""

import argparse
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import silhouette_score

NUMERIC_FEATURES = ["sales", "quantity", "discount", "profit_margin", "delivery_days"]
CATEGORICAL_FEATURES = ["category", "ship_mode"]

SEGMENT_LABELS = {
    # filled in dynamically after inspecting cluster centers, see label_segments()
}


def build_preprocessor() -> ColumnTransformer:
    """Numeric features get standardized; categorical features get one-hot encoded.
    Both are required for K-means, which only operates on continuous distance,
    so category/ship_mode need numeric encoding before they can contribute."""
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )


def load_order_features(orders_path: str, products_path: str) -> pd.DataFrame:
    orders = pd.read_csv(orders_path)
    products = pd.read_csv(products_path)
    df = orders.merge(products[["product_id", "category", "sub_category"]], on="product_id", how="left")

    # a handful of rows can have nulls in the merge or source data -- drop them
    # rather than silently imputing into a clustering feature, which would
    # distort distances
    before = len(df)
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped} rows with missing cluster features ({dropped/before:.1%})")
    return df


def choose_k(X, k_range=range(2, 9)) -> tuple[int, dict]:
    """Sweep k, score each by silhouette, return the best k plus the full
    sweep so it can be plotted (elbow + silhouette side by side)."""
    scores = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        scores[k] = {
            "inertia": km.inertia_,
            "silhouette": silhouette_score(X, labels, sample_size=min(5000, X.shape[0]), random_state=42),
        }
    best_k = max(scores, key=lambda k: scores[k]["silhouette"])
    return best_k, scores


def label_segments(df: pd.DataFrame, cluster_col="segment_id") -> pd.DataFrame:
    """Turn opaque cluster IDs (0, 1, 2...) into human-readable business labels
    by ranking each cluster's average discount and profit margin against the
    global average. This is what makes the output usable in a dashboard or a
    conversation with a stakeholder, instead of just 'cluster 3'."""
    profile = df.groupby(cluster_col)[["discount", "profit_margin", "sales", "quantity"]].mean()
    global_discount = df["discount"].mean()
    global_margin = df["profit_margin"].mean()

    def name_cluster(row):
        high_discount = row["discount"] > global_discount
        high_margin = row["profit_margin"] > global_margin
        high_value = row["sales"] > df["sales"].mean()
        if high_discount and not high_margin:
            return "Deep-Discount, Thin-Margin"
        if high_margin and not high_discount:
            return "Full-Price, High-Margin"
        if high_value and high_margin:
            return "Premium Basket"
        if not high_value:
            return "Small Basket, Low Engagement"
        return "Mixed / Moderate"

    labels = profile.apply(name_cluster, axis=1)
    df["segment_label"] = df[cluster_col].map(labels)
    return df


def run_order_segmentation(orders_path: str, products_path: str, output_path: str, plot_path: str):
    df = load_order_features(orders_path, products_path)

    preprocessor = build_preprocessor()
    X = preprocessor.fit_transform(df[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    if hasattr(X, "toarray"):
        X = X.toarray()

    best_k, sweep = choose_k(X)
    print("k sweep (silhouette score, higher is better):")
    for k, s in sweep.items():
        marker = "  <-- selected" if k == best_k else ""
        print(f"  k={k}: inertia={s['inertia']:.1f}  silhouette={s['silhouette']:.3f}{marker}")

    final_model = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    df["segment_id"] = final_model.fit_predict(X)
    df = label_segments(df)

    summary = (
        df.groupby("segment_label")
        .agg(orders=("order_id", "count"), avg_sales=("sales", "mean"),
             avg_discount=("discount", "mean"), avg_margin=("profit_margin", "mean"),
             total_profit=("profit", "sum"))
        .sort_values("orders", ascending=False)
        .round(3)
    )
    print("\nSegment summary:")
    print(summary.to_string())

    df.to_csv(output_path, index=False)
    print(f"\nSaved order-level segment assignments to {output_path}")

    # elbow + silhouette plot, saved for the README/dashboard
    ks = list(sweep.keys())
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(ks, [sweep[k]["inertia"] for k in ks], marker="o", color="#0F6E62")
    axes[0].set_title("Elbow method (inertia)")
    axes[0].set_xlabel("k")
    axes[1].plot(ks, [sweep[k]["silhouette"] for k in ks], marker="o", color="#0F6E62")
    axes[1].axvline(best_k, color="gray", linestyle="--", linewidth=1)
    axes[1].set_title(f"Silhouette score (best k={best_k})")
    axes[1].set_xlabel("k")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=110)
    print(f"Saved elbow/silhouette plot to {plot_path}")

    return df, summary


def run_customer_rfm(orders_path: str, output_path: str):
    """Classic Recency/Frequency/Monetary segmentation. Only meaningful if
    your dataset has customers with more than one order -- prints a warning
    and exits if it detects the single-order-per-customer pattern, rather
    than silently producing a degenerate result."""
    orders = pd.read_csv(orders_path, parse_dates=["order_date"])
    order_counts = orders.groupby("customer_id").size()
    if order_counts.max() == 1:
        print(
            "Every customer has exactly one order in this dataset -- RFM "
            "segmentation isn't meaningful here (Frequency would be 1 for "
            "everyone). Use --mode orders instead. Exiting."
        )
        sys.exit(1)

    snapshot_date = orders["order_date"].max() + pd.Timedelta(days=1)
    rfm = orders.groupby("customer_id").agg(
        recency=("order_date", lambda x: (snapshot_date - x.max()).days),
        frequency=("order_id", "count"),
        monetary=("sales", "sum"),
    )
    scaler = StandardScaler()
    X = scaler.fit_transform(rfm)
    best_k, sweep = choose_k(X)
    model = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    rfm["segment_id"] = model.fit_predict(X)
    rfm.to_csv(output_path)
    print(f"Saved RFM segments to {output_path}")
    return rfm


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Segment retail orders or customers via K-means")
    parser.add_argument("--orders", default="../data/processed/orders.csv")
    parser.add_argument("--products", default="../data/processed/products.csv")
    parser.add_argument("--output", default="../data/processed/order_segments.csv")
    parser.add_argument("--plot", default="../dashboard/segmentation_elbow.png")
    parser.add_argument("--mode", choices=["orders", "rfm"], default="orders")
    args = parser.parse_args()

    if args.mode == "orders":
        run_order_segmentation(args.orders, args.products, args.output, args.plot)
    else:
        run_customer_rfm(args.orders, args.output)
