"""Convert documented historical SKU sales into planning-period demand.

This module deliberately requires an explicit restaurant/SKU mapping and conversion
factor. It does not infer ingredient quantities from restaurant order counts.
"""
from __future__ import annotations
import pandas as pd

REQUIRED_SALES_COLUMNS = [
    "restaurant_id", "sku", "observed_sales_qty",
    "base_units_per_sale", "observed_period_days", "planning_period_days",
]


def build_demand_from_sales(sales: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_SALES_COLUMNS if c not in sales.columns]
    if missing:
        raise ValueError("Historical sales table missing columns: " + ", ".join(missing))
    df = sales[REQUIRED_SALES_COLUMNS].copy()
    if df.empty:
        raise ValueError("Historical sales table is empty")
    for col in REQUIRED_SALES_COLUMNS[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            raise ValueError(f"{col} must contain numeric values")
        if (df[col] < 0).any():
            raise ValueError(f"{col} cannot be negative")
    if (df["observed_period_days"] <= 0).any() or (df["planning_period_days"] <= 0).any():
        raise ValueError("Observed and planning period days must be greater than zero")
    if (df["base_units_per_sale"] <= 0).any():
        raise ValueError("base_units_per_sale must be greater than zero")
    df["restaurant_id"] = df["restaurant_id"].astype(str).str.strip()
    df["sku"] = df["sku"].astype(str).str.strip()
    if (df["restaurant_id"] == "").any() or (df["sku"] == "").any():
        raise ValueError("restaurant_id and sku cannot be blank")
    if df.duplicated(["restaurant_id", "sku"]).any():
        raise ValueError("Duplicate restaurant_id + sku rows; aggregate them before conversion")
    df["demand_qty_base_units"] = (
        df["observed_sales_qty"]
        * df["base_units_per_sale"]
        * df["planning_period_days"] / df["observed_period_days"]
    )
    return df[["restaurant_id", "sku", "demand_qty_base_units"]]
