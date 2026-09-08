"""
Data quality tests for the processed retail tables.

Run from the repo root:
    pytest tests/ -v

"""

import os

import pandas as pd
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


@pytest.fixture(scope="module")
def customers():
    return pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))


@pytest.fixture(scope="module")
def products():
    return pd.read_csv(os.path.join(DATA_DIR, "products.csv"))


@pytest.fixture(scope="module")
def orders():
    return pd.read_csv(os.path.join(DATA_DIR, "orders.csv"), parse_dates=["order_date", "ship_date"])


# ---------- schema ----------

def test_customers_schema(customers):
    expected = {"customer_id", "customer_name", "last_name", "segment", "city_type", "region", "state"}
    assert expected.issubset(set(customers.columns))


def test_products_schema(products):
    expected = {"product_id", "category", "sub_category"}
    assert expected.issubset(set(products.columns))


def test_orders_schema(orders):
    expected = {
        "order_id", "customer_id", "product_id", "order_date", "ship_date", "ship_mode",
        "sales", "quantity", "discount", "profit", "profit_margin", "delivery_days",
        "order_year", "order_month", "order_quarter", "postal_code_missing",
    }
    assert expected.issubset(set(orders.columns))


# ---------- primary keys / uniqueness ----------

def test_customer_id_unique(customers):
    assert customers["customer_id"].is_unique, "customer_id must be unique after dedup in the cleaning notebook"


def test_product_id_unique(products):
    assert products["product_id"].is_unique


def test_order_id_unique(orders):
    assert orders["order_id"].is_unique, "duplicate order_id means the drop_duplicates() step didn't fully dedup"


# ---------- referential integrity ----------

def test_orders_customer_fk(orders, customers):
    orphaned = set(orders["customer_id"]) - set(customers["customer_id"])
    assert not orphaned, f"{len(orphaned)} orders reference a customer_id not present in customers.csv"


def test_orders_product_fk(orders, products):
    orphaned = set(orders["product_id"]) - set(products["product_id"])
    assert not orphaned, f"{len(orphaned)} orders reference a product_id not present in products.csv"


# ---------- value ranges ----------

def test_discount_in_valid_range(orders):
    assert orders["discount"].between(0, 1).all(), "discount should be a 0-1 fraction, not a percentage or negative"


def test_quantity_positive(orders):
    assert (orders["quantity"] > 0).all()


def test_sales_positive(orders):
    assert (orders["sales"] > 0).all()


def test_no_null_core_fields(orders):
    core_fields = ["order_id", "customer_id", "product_id", "sales", "profit", "order_date"]
    nulls = orders[core_fields].isna().sum()
    assert nulls.sum() == 0, f"Unexpected nulls in core fields:\n{nulls[nulls > 0]}"


# ---------- business logic invariants ----------

def test_ship_date_not_before_order_date(orders):
    bad = orders[orders["ship_date"] < orders["order_date"]]
    assert bad.empty, f"{len(bad)} orders have ship_date earlier than order_date"


def test_profit_margin_matches_profit_over_sales(orders):
    recomputed = (orders["profit"] / orders["sales"]).round(4)
    mismatches = (recomputed - orders["profit_margin"]).abs() > 0.001
    assert mismatches.sum() == 0, f"{mismatches.sum()} rows have profit_margin that doesn't match profit/sales"


def test_order_year_matches_order_date(orders):
    assert (orders["order_year"] == orders["order_date"].dt.year).all()


def test_delivery_days_non_negative(orders):
    # a handful of same-day or data-entry edge cases can legitimately be 0,
    # but never negative -- that would mean shipping before ordering
    assert (orders["delivery_days"] >= 0).all(), "negative delivery_days means ship_date precedes order_date"
