"""
Builds data/processed/*.csv from the synthetic SAMPLE file, using the exact
same logic as notebooks/01_data_cleaning.ipynb. Used by CI (which doesn't
have the real 100K dataset) and available locally as a quick sanity check
without needing the real Kaggle download.

For real analysis, always prefer running the actual notebook against the
real dataset (see data/raw/README.md) -- this script's output is for
pipeline-testing only.
"""

import os
import pandas as pd

RAW_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "indian_store_data_SAMPLE.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def main():
    df = pd.read_csv(RAW_PATH)
    df = df.rename(columns={"Category of Goods": "Category"})
    df = df.dropna(how="all").drop_duplicates().reset_index(drop=True)

    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True, errors="coerce")
    df["Ship Mode"] = df["Ship Mode"].fillna(df["Ship Mode"].mode()[0])
    df["Postal Code Missing"] = df["Postal Code"].isna()
    df = df.dropna(subset=["Order Date", "Ship Date", "Sales", "Profit", "Region"])

    df["Profit Margin"] = (df["Profit"] / df["Sales"]).round(4)
    df["Delivery Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Order Year"] = df["Order Date"].dt.year
    df["Order Month"] = df["Order Date"].dt.month
    df["Order Quarter"] = df["Order Date"].dt.to_period("Q").astype(str)

    customers = (
        df[["Customer ID", "Customer Name", "Last Name", "Segment", "City Type", "Region", "State"]]
        .drop_duplicates(subset="Customer ID")
        .reset_index(drop=True)
    )
    products = df[["Category", "Sub-Category"]].drop_duplicates().reset_index(drop=True)
    products.insert(0, "Product ID", ["PROD-%04d" % i for i in range(1, len(products) + 1)])

    df = df.drop(columns=["Product ID", "Product Name"], errors="ignore")
    orders = df.merge(products, on=["Category", "Sub-Category"], how="left")[[
        "Order ID", "Customer ID", "Product ID", "Order Date", "Ship Date", "Ship Mode",
        "Sales", "Quantity", "Discount", "Profit", "Profit Margin", "Delivery Days",
        "Order Year", "Order Month", "Order Quarter", "Postal Code Missing",
    ]]

    def to_snake_case(cols):
        return [c.strip().lower().replace(" ", "_").replace("-", "_") for c in cols]

    customers.columns = to_snake_case(customers.columns)
    products.columns = to_snake_case(products.columns)
    orders.columns = to_snake_case(orders.columns)

    os.makedirs(OUT_DIR, exist_ok=True)
    customers.to_csv(os.path.join(OUT_DIR, "customers.csv"), index=False)
    products.to_csv(os.path.join(OUT_DIR, "products.csv"), index=False)
    orders.to_csv(os.path.join(OUT_DIR, "orders.csv"), index=False)
    print(f"customers: {customers.shape}, products: {products.shape}, orders: {orders.shape}")


if __name__ == "__main__":
    main()
