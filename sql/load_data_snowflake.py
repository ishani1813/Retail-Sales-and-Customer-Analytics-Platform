"""
Loads the cleaned CSVs from data/processed/ into Snowflake, and creates the
target tables first if they don't already exist (via sql/01b_schema_snowflake.sql).

Requires a free Snowflake trial account (https://signup.snowflake.com/) --
30 days, no credit card needed. See the "Snowflake setup" section in the
main README for how to find your account identifier.

SECURITY: credentials are read from environment variables, never hardcoded.
Set them before running:

    export SNOWFLAKE_ACCOUNT="your-account-identifier"   # e.g. "abc12345.ap-south-1"
    export SNOWFLAKE_USER="your-username"
    export SNOWFLAKE_PASSWORD="your-password"
    export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"               # default trial warehouse name
    python sql/load_data_snowflake.py

Usage:
    python sql/load_data_snowflake.py
"""

import os
import sys

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

REQUIRED_ENV_VARS = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "01b_schema_snowflake.sql")

TABLES = [
    ("CUSTOMERS", "data/processed/customers.csv"),
    ("PRODUCTS", "data/processed/products.csv"),
    ("ORDERS", "data/processed/orders.csv"),
]


def check_env():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        print("See the docstring at the top of this file for how to set them.")
        sys.exit(1)


def get_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    )


def run_schema_script(conn):
    with open(SCHEMA_FILE) as f:
        raw = f.read()

    # Strip comment-only lines from the WHOLE file first, then split on ';'.
    # (Splitting first and filtering chunks that "start with --" is a bug --
    # a chunk can have a comment block followed by a real statement, and
    # checking only the chunk's start silently drops the real statement too.)
    no_comments = "\n".join(line for line in raw.splitlines() if not line.strip().startswith("--"))
    statements = [s.strip() for s in no_comments.split(";") if s.strip()]

    cur = conn.cursor()
    for stmt in statements:
        cur.execute(stmt)
    cur.close()
    print(f"Schema created ({len(statements)} statements run; database: RETAIL_ANALYTICS, schema: PUBLIC)")


def main():
    check_env()
    conn = get_connection()
    try:
        run_schema_script(conn)
        conn.cursor().execute("USE DATABASE RETAIL_ANALYTICS")
        conn.cursor().execute("USE SCHEMA PUBLIC")

        for table, path in TABLES:
            if not os.path.exists(path):
                print(f"Missing {path} -- run notebooks/01_data_cleaning.ipynb first.")
                sys.exit(1)
            df = pd.read_csv(path)
            # Snowflake convention: unquoted identifiers are upper-cased, so
            # match column names to upper case to avoid quoting headaches
            df.columns = [c.upper() for c in df.columns]
            success, num_chunks, num_rows, _ = write_pandas(conn, df, table)
            status = "OK" if success else "FAILED"
            print(f"[{status}] Loaded {num_rows} rows into {table} ({num_chunks} chunk(s))")

        print("\nDone. The same queries in sql/02_business_queries.sql run unchanged against this schema.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
