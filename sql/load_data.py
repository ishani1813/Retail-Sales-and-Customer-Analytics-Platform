"""
Loads the cleaned CSVs from data/processed/ into PostgreSQL.
Run this AFTER sql/01_schema.sql has created the tables.

Usage:
    python sql/load_data.py
"""
from sqlalchemy import create_engine
import pandas as pd

# Adjust if your Postgres user/password/host/port/db differ
DB_URL = "postgresql://postgres:postgres@localhost:5433/retail_analytics"

engine = create_engine(DB_URL)

# Order matters: customers/products first (orders has foreign keys to both)
for table, filename in [
    ("customers", "data/processed/customers.csv"),
    ("products", "data/processed/products.csv"),
    ("orders", "data/processed/orders.csv"),
]:
    df = pd.read_csv(filename)
    df.to_sql(table, engine, if_exists="append", index=False)
    print(f"Loaded {len(df)} rows into '{table}'")

print("Done. Run sql/02_business_queries.sql next.")
