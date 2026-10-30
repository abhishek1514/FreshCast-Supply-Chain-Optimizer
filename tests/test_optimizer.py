import pandas as pd
import pytest
from app.optimizer import optimize_distribution, OptimizationError


def tables():
    return {
        "warehouses": pd.DataFrame([
            {"warehouse_id":"W1","warehouse_name":"Near","capacity_base_units":100,"fixed_cost_per_period":5,"active":True},
            {"warehouse_id":"W2","warehouse_name":"Far","capacity_base_units":100,"fixed_cost_per_period":50,"active":True},
        ]),
        "restaurants": pd.DataFrame([{"restaurant_id":"R1","restaurant_name":"Cafe","region":"North"}]),
        "products": pd.DataFrame([{"sku":"MILK","product_name":"Milk","base_unit":"L"}]),
        "demand": pd.DataFrame([{"restaurant_id":"R1","sku":"MILK","demand_qty_base_units":10}]),
        "inventory": pd.DataFrame([
            {"warehouse_id":"W1","sku":"MILK","available_qty_base_units":20,"handling_cost_per_base_unit":1},
            {"warehouse_id":"W2","sku":"MILK","available_qty_base_units":20,"handling_cost_per_base_unit":1},
        ]),
        "shipping_costs": pd.DataFrame([
            {"warehouse_id":"W1","restaurant_id":"R1","cost_per_base_unit":2},
            {"warehouse_id":"W2","restaurant_id":"R1","cost_per_base_unit":1},
        ]),
    }


def test_optimizer_fulfills_demand_and_selects_low_total_cost():
    result = optimize_distribution(tables())
    assert result["status"] == "Optimal"
    assert result["demand_base_units"] == pytest.approx(10)
    assert result["allocations"]["quantity_base_units"].sum() == pytest.approx(10)
    assert result["opened_warehouses"] == ["W1"]
    assert result["objective_cost"] == pytest.approx(35)


def test_infeasible_demand_raises_actionable_error():
    data = tables()
    data["demand"].loc[0, "demand_qty_base_units"] = 1000
    with pytest.raises(OptimizationError, match="infeasible"):
        optimize_distribution(data)
