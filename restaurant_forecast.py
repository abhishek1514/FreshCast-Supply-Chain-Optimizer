from pathlib import Path
import pandas as pd

source = Path("data/public/restaurant_monthly_demand.csv")
output = Path("data/public/restaurant_forecasts.csv")

df = pd.read_csv(source, parse_dates=["month"])
df["month"] = df["month"].dt.to_period("M")

# Aggregate restaurant-level monthly order counts.
monthly = (
    df.groupby(["restaurant_id", "month"], as_index=False)["order_count"]
    .sum()
    .sort_values(["restaurant_id", "month"])
)

# Validate previous-month baseline only where consecutive months exist.
previous = monthly.copy()
previous["month"] = previous["month"] + 1
pairs = monthly.merge(
    previous.rename(columns={"order_count": "forecast"}),
    on=["restaurant_id", "month"],
    how="inner",
)

if len(pairs):
    pairs["absolute_error"] = (pairs["order_count"] - pairs["forecast"]).abs()
    print("RESTAURANT-LEVEL VALIDATION")
    print("Consecutive restaurant-month pairs:", len(pairs))
    print("MAE:", round(pairs["absolute_error"].mean(), 2))
else:
    print("No consecutive-month pairs available for validation.")

# Forecast only for restaurants with observations in the latest dataset month.
latest_month = monthly["month"].max()
next_month = latest_month + 1

latest = monthly[monthly["month"] == latest_month].copy()
latest["forecast_month"] = next_month.to_timestamp()
latest = latest.rename(columns={"order_count": "forecast_orders"})
latest["forecast_method"] = "previous_month_actual"

latest["forecast_month"] = latest["forecast_month"].dt.strftime("%Y-%m-%d")
latest["last_observed_month"] = latest["month"].dt.strftime("%Y-%m-%d")

result = latest[
    ["restaurant_id", "last_observed_month", "forecast_month",
     "forecast_orders", "forecast_method"]
].sort_values("restaurant_id")

output.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(output, index=False)

print("\nFORECAST OUTPUT")
print("Latest dataset month:", str(latest_month))
print("Forecast month:", str(next_month))
print("Restaurants forecast:", len(result))
print("Saved to:", output)
print("\nSample:")
print(result.head(10).to_string(index=False))
