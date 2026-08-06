-- Indian Retail Sales Analytics — Business Queries
-- Each query answers one of the questions in business_questions.md

-- =====================================================================
-- Q1. Which regions have declining margins, not just declining sales?
--     (Sales can look fine while margin quietly erodes — this catches that.)
-- =====================================================================
SELECT
    region,
    order_year,
    ROUND(SUM(sales)::numeric, 0)                       AS total_sales,
    ROUND(SUM(profit)::numeric, 0)                       AS total_profit,
    ROUND(AVG(profit_margin)::numeric, 4)                 AS avg_profit_margin,
    ROUND(
        AVG(profit_margin) - LAG(AVG(profit_margin)) OVER (
            PARTITION BY region ORDER BY order_year
        ), 4
    )                                                      AS margin_change_vs_prior_year
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY region, order_year
ORDER BY region, order_year;


-- =====================================================================
-- Q2. Which category / sub-category combinations sell well but are
--     quietly unprofitable? (high sales rank, low margin rank)
-- =====================================================================
WITH category_perf AS (
    SELECT
        p.category,
        p.sub_category,
        SUM(o.sales)                           AS total_sales,
        SUM(o.profit)                          AS total_profit,
        AVG(o.profit_margin)                   AS avg_margin
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    GROUP BY p.category, p.sub_category
)
SELECT
    category,
    sub_category,
    ROUND(total_sales::numeric, 0)   AS total_sales,
    ROUND(total_profit::numeric, 0)  AS total_profit,
    ROUND(avg_margin::numeric, 4)    AS avg_margin,
    RANK() OVER (ORDER BY total_sales DESC)  AS sales_rank,
    RANK() OVER (ORDER BY avg_margin ASC)    AS margin_rank_worst_first
FROM category_perf
ORDER BY sales_rank;


-- =====================================================================
-- Q3. Who are the top 3 customers by profit, within each region?
--     (per-region ranking, not just a single global top-N)
-- =====================================================================
WITH customer_profit AS (
    SELECT
        c.region,
        c.customer_id,
        c.customer_name || ' ' || c.last_name  AS customer,
        SUM(o.profit)                           AS total_profit
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.region, c.customer_id, c.customer_name, c.last_name
),
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY region ORDER BY total_profit DESC) AS rn
    FROM customer_profit
)
SELECT region, customer, ROUND(total_profit::numeric, 0) AS total_profit
FROM ranked
WHERE rn <= 3
ORDER BY region, total_profit DESC;


-- =====================================================================
-- Q4. What's the sales trend, and what's the running (cumulative) total
--     by quarter? (shows growth trajectory, not just period snapshots)
-- =====================================================================
SELECT
    order_quarter,
    ROUND(SUM(sales)::numeric, 0) AS quarterly_sales,
    ROUND(SUM(SUM(sales)) OVER (ORDER BY order_quarter)::numeric, 0) AS running_total_sales
FROM orders
GROUP BY order_quarter
ORDER BY order_quarter;


-- =====================================================================
-- Q5. Does discounting actually grow profit, or just erode it?
--     (bucket discounts, compare average margin per bucket)
-- =====================================================================
SELECT
    CASE
        WHEN discount = 0 THEN '0% (no discount)'
        WHEN discount <= 0.10 THEN '1-10%'
        WHEN discount <= 0.20 THEN '11-20%'
        WHEN discount <= 0.30 THEN '21-30%'
        ELSE '30%+'
    END                                     AS discount_bucket,
    COUNT(*)                                AS num_orders,
    ROUND(AVG(profit_margin)::numeric, 4)   AS avg_profit_margin,
    ROUND(SUM(profit)::numeric, 0)          AS total_profit
FROM orders
GROUP BY 1
ORDER BY MIN(discount);


-- =====================================================================
-- Q6. Which city tier (Tier 1 / Tier 2 / Village) is most profitable
--     per region — where should the business expand next?
-- =====================================================================
SELECT
    c.region,
    c.city_type,
    ROUND(SUM(o.sales)::numeric, 0)   AS total_sales,
    ROUND(SUM(o.profit)::numeric, 0)  AS total_profit,
    ROUND(AVG(o.profit_margin)::numeric, 4) AS avg_margin,
    COUNT(DISTINCT c.customer_id)     AS customers
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.region, c.city_type
ORDER BY c.region, total_profit DESC;


-- =====================================================================
-- Q7. Does shipping speed (Ship Mode) affect delivery time and,
--     indirectly, customer segments served?
-- =====================================================================
SELECT
    ship_mode,
    ROUND(AVG(delivery_days)::numeric, 1) AS avg_delivery_days,
    COUNT(*)                              AS num_orders,
    ROUND(AVG(sales)::numeric, 0)         AS avg_order_value
FROM orders
GROUP BY ship_mode
ORDER BY avg_delivery_days;
