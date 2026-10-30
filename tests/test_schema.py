import pandas as pd
from app.schema import validate_tables


def valid_tables():
    return {
        "warehouses": pd.DataFrame([{"warehouse_id":"W1","warehouse_name":"Warehouse 1","capacity_base_units":100,"fixed_cost_per_period":10,"active":True}]),
        "restaurants": pd.DataFrame([{"restaurant_id":"R1","restaurant_name":"Restaurant 1","region":"North"}]),
        "products": pd.DataFrame([{"sku":"SKU1","product_name":"Tomato","base_unit":"kg"}]),
        "demand": pd.DataFrame([{"restaurant_id":"R1","sku":"SKU1","demand_qty_base_units":10}]),
        "inventory": pd.DataFrame([{"warehouse_id":"W1","sku":"SKU1","available_qty_base_units":20,"handling_cost_per_base_unit":1}]),
        "shipping_costs": pd.DataFrame([{"warehouse_id":"W1","restaurant_id":"R1","cost_per_base_unit":2}]),
    }


def test_valid_tables_pass():
    assert validate_tables(valid_tables()).ok


def test_negative_demand_fails():
    tables = valid_tables()
    tables["demand"].loc[0, "demand_qty_base_units"] = -1
    result = validate_tables(tables)
    assert not result.ok
    assert any("negative" in e for e in result.errors)


def test_duplicate_demand_key_fails():
    tables = valid_tables()
    tables["demand"] = pd.concat([tables["demand"], tables["demand"]], ignore_index=True)
    result = validate_tables(tables)
    assert not result.ok
    assert any("duplicate key" in e for e in result.errors)
