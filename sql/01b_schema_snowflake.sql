-- Indian Retail Sales Analytics — Snowflake Schema
-- Same normalized structure as sql/01_schema.sql (PostgreSQL), adapted for Snowflake.
-- Run this in a Snowflake worksheet (or via load_data_snowflake.py, which creates
-- these automatically) before loading the CSVs from data/processed/.
--
-- One real difference worth knowing if asked in an interview: Snowflake accepts
-- PRIMARY KEY / FOREIGN KEY / UNIQUE constraints syntactically, but does NOT
-- enforce them at write time the way Postgres does -- they're metadata/documentation
-- only, used by the query optimizer as hints. Data quality has to be enforced
-- upstream (which is exactly what tests/test_data_quality.py does here) rather
-- than relying on the database to reject bad rows.

CREATE DATABASE IF NOT EXISTS retail_analytics;
USE DATABASE retail_analytics;
CREATE SCHEMA IF NOT EXISTS public;
USE SCHEMA public;

CREATE OR REPLACE TABLE customers (
    customer_id     VARCHAR(20) PRIMARY KEY,
    customer_name   VARCHAR(100),
    last_name       VARCHAR(100),
    segment         VARCHAR(30),
    city_type       VARCHAR(20),
    region          VARCHAR(20),
    state           VARCHAR(50)
);

CREATE OR REPLACE TABLE products (
    product_id      VARCHAR(20) PRIMARY KEY,
    category        VARCHAR(50),
    sub_category    VARCHAR(50)
);

CREATE OR REPLACE TABLE orders (
    order_id                VARCHAR(20) PRIMARY KEY,
    customer_id             VARCHAR(20) REFERENCES customers(customer_id),
    product_id              VARCHAR(20) REFERENCES products(product_id),
    order_date               DATE,
    ship_date                 DATE,
    ship_mode                 VARCHAR(30),
    sales                     NUMERIC(12, 2),
    quantity                   INTEGER,
    discount                   NUMERIC(4, 2),
    profit                     NUMERIC(12, 2),
    profit_margin               NUMERIC(6, 4),
    delivery_days                 INTEGER,
    order_year                     INTEGER,
    order_month                     INTEGER,
    order_quarter                     VARCHAR(10),
    postal_code_missing                 BOOLEAN
);

-- The same 7 business queries in sql/02_business_queries.sql run against this
-- schema with no changes needed -- window functions, CTEs, ::numeric casts,
-- and || concatenation are all supported the same way in Snowflake.
