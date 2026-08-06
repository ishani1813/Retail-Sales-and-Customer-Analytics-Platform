# Power BI / Tableau Dashboard — Build Guide

I can't generate an actual `.pbix` or `.twbx` file from here — those are proprietary binary
formats owned by Desktop apps, not something a script can output directly. This is the exact
spec to build it yourself in Power BI Desktop or Tableau Public (both free), in under an hour.

## Connect
- **Power BI**: Get Data → Text/CSV → `data/processed/orders.csv`, `customers.csv`, `products.csv`
  → in Power Query, set relationships: `orders.customer_id → customers.customer_id`,
  `orders.product_id → products.product_id` (or just connect directly to Postgres if you've
  loaded the SQL tables — Get Data → PostgreSQL database, cleaner than three CSVs).
- **Tableau Public**: Connect → Text File → same three CSVs → Tableau usually auto-detects
  the relationships from matching column names; verify them in the Data Source tab.

## Suggested KPI cards (top of dashboard)
- Total Sales (₹) · Total Profit (₹) · Avg Profit Margin (%) · Total Orders

## Suggested visuals (answering business_questions.md directly)
1. **Bar chart** — Total Profit by Region (Q1 at a glance)
2. **Line chart** — Profit Margin trend by Region over Order Year (Q1 in detail) — this is the
   one that should look different from a plain sales line; that gap *is* the insight
3. **Scatter or bar** — Sales vs. Avg Profit Margin by Category/Sub-Category (Q2) — plot sales
   on one axis and margin on the other so the "high sales, low margin" outliers jump out visually
4. **Table with rank** — Top 3 customers by profit, per region (Q3)
5. **Area chart with cumulative total** — Running Sales Total by Quarter (Q4)
6. **Bar chart** — Avg Profit Margin by Discount Bucket (Q5) — this one usually produces the
   single most quotable finding, make it prominent
7. **Heatmap or clustered bar** — Profit by City Type × Region (Q6)

## Filters / slicers to add
- Region, Order Year, Segment, Category — let a reviewer click into any region and have
  every visual respond. That interactivity is the actual point of using Power BI/Tableau
  over a static chart; don't skip it.

## Publishing (so it's actually clickable from your resume/GitHub)
- **Tableau Public**: File → Save to Tableau Public → get a shareable public link
- **Power BI**: Publish → Power BI Service (free tier) → Share → copy the link (or File →
  Export → PDF/image as a fallback if you'd rather not use the cloud service)

Add the finished link to the main `README.md` and to your resume project entry.
