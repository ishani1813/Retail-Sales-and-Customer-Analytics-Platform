# Business Questions

Framed as if reporting to a Head of Retail Operations at a multi-region Indian retail chain.

1. **Which regions have declining profit margins — not just declining sales?**
   Sales staying flat or growing can mask margin erosion underneath. Region leadership needs
   to know where profitability is quietly slipping, not just where revenue is down.

2. **Which product categories sell well but are quietly unprofitable?**
   High-volume categories can still be low-margin. This flags where the catalog/pricing
   strategy may need a second look, independent of raw sales volume.

3. **Who are the highest-value customers in each region, and are we treating them like it?**
   A single global "top customers" list hides strong regional customers. Per-region ranking
   is what a regional sales lead can actually act on.

4. **What does the sales trajectory look like over time, on a cumulative basis?**
   Quarter-over-quarter swings are noisy; a running total shows the real growth trend
   leadership should be planning around.

5. **Is discounting actually growing profit, or just eroding it?**
   Discounting is often used reflexively. This tests whether deeper discounts are
   correlated with healthier or weaker margins.

6. **Which city tier (Tier 1 / Tier 2 / Village) is most profitable, per region — where
   should the business expand next?**
   Expansion budget is finite. This ranks where the return has actually been strongest,
   not just where the most stores already are.

## Answering these

- Q1, Q3, Q6 → `sql/02_business_queries.sql`, using JOINs + window functions (`LAG`, `ROW_NUMBER`)
- Q2 → SQL, using a CTE + `RANK()`
- Q4 → SQL, using a windowed running `SUM()`
- Q5 → SQL, using a `CASE`-bucketed aggregation
- All six are also summarized in `excel/regional_performance_summary.xlsx` and should
  anchor the KPIs/visuals in the Power BI or Tableau dashboard — see `dashboard/BUILD_GUIDE.md`
