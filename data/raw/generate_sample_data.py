"""
Generates a SYNTHETIC sample dataset that mirrors the schema of the
'Indian Store Data' dataset on Kaggle (abuhumzakhan/store-data):
https://www.kaggle.com/datasets/abuhumzakhan/store-data
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N = 4000  # small sample; real dataset has ~100K rows

states_by_region = {
    "North": ["Delhi", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan"],
    "South": ["Karnataka", "Tamil Nadu", "Telangana", "Kerala", "Andhra Pradesh"],
    "East": ["West Bengal", "Odisha", "Bihar", "Jharkhand"],
    "West": ["Maharashtra", "Gujarat", "Goa", "Madhya Pradesh"],
}
regions = list(states_by_region.keys())

categories = {
    "Electronics": ["Mobiles", "Laptops", "Accessories", "Cameras"],
    "Furniture": ["Chairs", "Tables", "Storage", "Furnishings"],
    "Clothing": ["Menswear", "Womenswear", "Kidswear", "Footwear"],
    "Grocery": ["Staples", "Beverages", "Snacks", "Household"],
}

city_types = ["Tier 1", "Tier 2", "Village"]
segments = ["Consumer", "Corporate", "SMB"]
ship_modes = ["Standard Class", "Second Class", "First Class", "Same Day"]

n_customers = 600
customer_ids = [f"CUST-{i:05d}" for i in range(1, n_customers + 1)]
first_names = ["Aarav","Vivaan","Aditya","Vihaan","Arjun","Sai","Reyansh","Krishna",
               "Ishaan","Rohan","Ananya","Diya","Priya","Isha","Aadhya","Myra",
               "Saanvi","Anika","Kavya","Meera"]
last_names = ["Sharma","Verma","Iyer","Reddy","Nair","Gupta","Patel","Singh",
              "Das","Rao","Menon","Chatterjee","Mukherjee","Joshi","Bose"]

customer_lookup = {
    cid: {
        "Customer Name": rng.choice(first_names),
        "Last Name": rng.choice(last_names),
        "Segment": rng.choice(segments),
        "Region": (region := rng.choice(regions)),
        "State": rng.choice(states_by_region[region]),
        "City Type": rng.choice(city_types, p=[0.45, 0.4, 0.15]),
    }
    for cid in customer_ids
}

rows = []
order_id_counter = 1
date_start = pd.Timestamp("2019-01-01")
date_end = pd.Timestamp("2023-12-31")
date_range_days = (date_end - date_start).days

for _ in range(N):
    cid = rng.choice(customer_ids)
    cust = customer_lookup[cid]
    cat = rng.choice(list(categories.keys()))
    subcat = rng.choice(categories[cat])
    order_date = date_start + pd.Timedelta(days=int(rng.integers(0, date_range_days)))
    ship_days = int(rng.integers(1, 8))
    ship_date = order_date + pd.Timedelta(days=ship_days)

    base_price = {"Electronics": 15000, "Furniture": 6000, "Clothing": 1200, "Grocery": 400}[cat]
    quantity = int(rng.integers(1, 6))
    unit_price = max(50, rng.normal(base_price, base_price * 0.35))
    sales = round(unit_price * quantity, 2)
    discount = round(float(rng.choice([0, 0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5])), 2)
    margin_rate = rng.normal(0.18, 0.08)
    profit = round(sales * (1 - discount) * margin_rate, 2)

    # occasionally inject a missing value / bad row, since real data isn't clean
    postal = rng.integers(100000, 899999)
    if rng.random() < 0.02:
        postal = np.nan
    ship_mode = rng.choice(ship_modes)
    if rng.random() < 0.01:
        ship_mode = None

    rows.append({
        "Order ID": f"ORD-{order_id_counter:06d}",
        "Order Date": order_date.strftime("%d-%m-%Y") if rng.random() > 0.03 else order_date.strftime("%Y/%m/%d"),
        "Ship Date": ship_date.strftime("%d-%m-%Y"),
        "Ship Mode": ship_mode,
        "Customer ID": cid,
        "Customer Name": cust["Customer Name"],
        "Last Name": cust["Last Name"],
        "Segment": cust["Segment"],
        "City Type": cust["City Type"],
        "Region": cust["Region"],
        "State": cust["State"],
        "Postal Code": postal,
        "Category": cat,
        "Sub-Category": subcat,
        "Sales": sales,
        "Quantity": quantity,
        "Discount": discount,
        "Profit": profit,
    })
    order_id_counter += 1

df = pd.DataFrame(rows)
# duplicate a few rows and add a few full-null rows, like real messy exports do
df = pd.concat([df, df.sample(15, random_state=1)], ignore_index=True)
blank_rows = pd.DataFrame([{c: np.nan for c in df.columns} for _ in range(5)])
df = pd.concat([df, blank_rows], ignore_index=True)

df.to_csv("/home/claude/indian-retail-analytics/data/raw/indian_store_data_SAMPLE.csv", index=False)
print(f"Wrote {len(df)} sample rows.")
