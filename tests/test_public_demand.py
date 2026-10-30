import pandas as pd
import pytest
from app.public_demand import build_demand_from_sales


def test_build_demand_scales_sales_to_planning_period():
    df = pd.DataFrame([{
        "restaurant_id": "R1", "sku": "P1", "observed_sales_qty": 10,
        "base_units_per_sale": 2, "observed_period_days": 7, "planning_period_days": 14,
    }])
    out = build_demand_from_sales(df)
    assert out.iloc[0]["demand_qty_base_units"] == 40


def test_rejects_missing_conversion_columns():
    with pytest.raises(ValueError, match="missing columns"):
        build_demand_from_sales(pd.DataFrame({"restaurant_id": ["R1"]}))


def test_rejects_duplicate_restaurant_sku():
    row = {"restaurant_id": "R1", "sku": "P1", "observed_sales_qty": 10,
           "base_units_per_sale": 1, "observed_period_days": 7, "planning_period_days": 7}
    with pytest.raises(ValueError, match="Duplicate"):
        build_demand_from_sales(pd.DataFrame([row, row]))
