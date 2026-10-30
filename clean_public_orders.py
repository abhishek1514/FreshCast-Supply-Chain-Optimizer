from pathlib import Path
import pandas as pd
import re

source = Path(
    r"data\public\extracted\Dataset of Number of Orders of Clients and Restaurants from a Delivery Food Application\encalientes_data.xlsx"
)
output = Path("data/public/restaurant_monthly_orders.csv")

raw = pd.read_excel(source, header=None)
header_restaurants = raw.iloc[0]
header_months = raw.iloc[1]

records = []
current_restaurant = None

for col in range(1, raw.shape[1]):
    restaurant_header = header_restaurants.iloc[col]
    month_header = header_months.iloc[col]

    if pd.notna(restaurant_header):
        label = str(restaurant_header).strip()

        if label.startswith("Total "):
            continue

        if re.fullmatch(r"\d+(?:\.0)?", label):
            current_restaurant = str(int(float(label)))

    if current_restaurant is None:
        continue

    month = str(month_header).strip()

    # Skip non-month columns, including blank and total columns.
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        continue

    for row in range(2, raw.shape[0]):
        client = raw.iloc[row, 0]
        value = raw.iloc[row, col]

        if pd.isna(client) or pd.isna(value):
            continue

        if str(client).strip().lower() == "total general":
            continue

        try:
            count = float(value)
        except (TypeError, ValueError):
            continue

        records.append({
            "restaurant_id": current_restaurant,
            "client_id": str(client).strip(),
            "month": month,
            "order_count": count,
        })

result = pd.DataFrame(records)

if result.empty:
    raise ValueError("No monthly observations extracted; inspect the workbook layout.")

result = result.drop_duplicates()
result["month"] = pd.to_datetime(result["month"], format="%Y-%m")
result = result.sort_values(["restaurant_id", "month", "client_id"])

output.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(output, index=False)

print("Output:", output)
print("Records:", len(result))
print("Restaurants:", result["restaurant_id"].nunique())
print("Clients:", result["client_id"].nunique())
print("Months:", result["month"].min(), "to", result["month"].max())
print("Sample:")
print(result.head(10).to_string(index=False))
