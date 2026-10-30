import pandas as pd

p = "data/public/restaurant_monthly_demand.csv"
d = pd.read_csv(p, parse_dates=["month"])

m = (
    d.groupby("month")["order_count"]
    .sum()
    .sort_index()
    .asfreq("MS")
)

results = []

# Har test month ke liye sirf usse pehle ka data use karo.
for i in range(12, len(m)):
    train = m.iloc[:i]
    actual = m.iloc[i]

    previous = train.iloc[-1]
    rolling3 = train.iloc[-3:].mean()
    historical = train.mean()

    results.append({
        "month": m.index[i],
        "actual": actual,
        "historical_mean": historical,
        "previous_month": previous,
        "rolling_3_month": rolling3,
    })

r = pd.DataFrame(results).set_index("month")

for method in ["historical_mean", "previous_month", "rolling_3_month"]:
    mae = (r["actual"] - r[method]).abs().mean()
    print(f"{method}: MAE = {mae:.2f}")

print("\nEvaluation months:", len(r))
print("Period:", r.index.min().date(), "to", r.index.max().date())
