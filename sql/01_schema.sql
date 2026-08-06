-- Indian Retail Sales Analytics — Schema
-- Run this first to create the normalized tables, then load the CSVs from data/processed/

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    customer_id     VARCHAR(20) PRIMARY KEY,
    customer_name   VARCHAR(100),
    last_name       VARCHAR(100),
    segment         VARCHAR(30),
    city_type       VARCHAR(20),
    region          VARCHAR(20),
    state           VARCHAR(50)
);

CREATE TABLE products (
    product_id      VARCHAR(20) PRIMARY KEY,
    category        VARCHAR(50),
    sub_category    VARCHAR(50)
);

CREATE TABLE orders (
    order_id            VARCHAR(20) PRIMARY KEY,
    customer_id         VARCHAR(20) REFERENCES customers(customer_id),
    product_id          VARCHAR(20) REFERENCES products(product_id),
    order_date           DATE,
    ship_date             DATE,
    ship_mode             VARCHAR(30),
    sales                 NUMERIC(12, 2),
    quantity               INTEGER,
    discount               NUMERIC(4, 2),
    profit                 NUMERIC(12, 2),
    profit_margin          NUMERIC(6, 4),
    delivery_days           INTEGER,
    order_year               INTEGER,
    order_month               INTEGER,
    order_quarter               VARCHAR(10),
    postal_code_missing         BOOLEAN
);

-- Loading from psql (adjust paths as needed):
-- \copy customers FROM 'data/processed/customers.csv' WITH (FORMAT csv, HEADER true);
-- \copy products  FROM 'data/processed/products.csv'  WITH (FORMAT csv, HEADER true);
-- \copy orders    FROM 'data/processed/orders.csv'    WITH (FORMAT csv, HEADER true);
--
-- Or from Python:
-- import pandas as pd, sqlalchemy as sa
-- engine = sa.create_engine("postgresql://user:pass@localhost:5432/retail_analytics")
-- pd.read_csv("data/processed/customers.csv").to_sql("customers", engine, if_exists="append", index=False)
-- (repeat for products, orders — load customers and products before orders, for the FK constraints)
