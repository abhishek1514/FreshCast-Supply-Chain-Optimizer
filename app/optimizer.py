"""Mixed-integer optimization for warehouse-to-restaurant distribution."""
from __future__ import annotations
import pandas as pd
import pulp

from app.schema import validate_tables

class OptimizationError(RuntimeError):
    pass


def optimize_distribution(tables: dict[str, pd.DataFrame], time_limit_seconds: int = 30) -> dict:
    """Minimize warehouse fixed costs + handling + outbound shipping costs.

    All quantities must be converted to the product's declared base unit before upload.
    Demand must be fully met; stock and total warehouse capacity are hard constraints.
    """
    validation = validate_tables(tables)
    if not validation.ok:
        raise ValueError("Input validation failed:\n- " + "\n- ".join(validation.errors))
    t = validation.tables
    warehouses = t["warehouses"].set_index("warehouse_id")
    restaurants = t["restaurants"].set_index("restaurant_id")
    products = t["products"].set_index("sku")
    demand = t["demand"].set_index(["restaurant_id", "sku"])["demand_qty_base_units"].to_dict()
    inventory = t["inventory"].set_index(["warehouse_id", "sku"])["available_qty_base_units"].to_dict()
    handling = t["inventory"].set_index(["warehouse_id", "sku"])["handling_cost_per_base_unit"].to_dict()
    ship = t["shipping_costs"].set_index(["warehouse_id", "restaurant_id"])["cost_per_base_unit"].to_dict()
    active = [w for w in warehouses.index if bool(warehouses.loc[w, "active"])]
    skus = list(products.index)
    rest_ids = list(restaurants.index)

    model = pulp.LpProblem("Restaurant_Distributor_Network_Optimization", pulp.LpMinimize)
    use = {w: pulp.LpVariable(f"open_{w}", cat=pulp.LpBinary) for w in active}
    x = {}
    for w in active:
        for r in rest_ids:
            if (w, r) not in ship:
                continue
            for sku in skus:
                if (w, sku) in inventory and (r, sku) in demand:
                    x[(w, r, sku)] = pulp.LpVariable(f"ship_{w}_{r}_{sku}", lowBound=0, cat=pulp.LpContinuous)

    fixed = pulp.lpSum(float(warehouses.loc[w, "fixed_cost_per_period"]) * use[w] for w in active)
    variable = pulp.lpSum(
        (float(ship[(w, r)]) + float(handling[(w, sku)])) * var
        for (w, r, sku), var in x.items()
    )
    model += fixed + variable

    for (r, sku), qty in demand.items():
        eligible = [x[k] for k in x if k[1] == r and k[2] == sku]
        model += pulp.lpSum(eligible) == float(qty), f"demand_{r}_{sku}"

    for (w, sku), qty in inventory.items():
        relevant = [x[k] for k in x if k[0] == w and k[2] == sku]
        if relevant:
            model += pulp.lpSum(relevant) <= float(qty) * use[w], f"stock_{w}_{sku}"

    for w in active:
        outgoing = [x[k] for k in x if k[0] == w]
        model += pulp.lpSum(outgoing) <= float(warehouses.loc[w, "capacity_base_units"]) * use[w], f"capacity_{w}"

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=max(1, int(time_limit_seconds)))
    model.solve(solver)
    status = pulp.LpStatus.get(model.status, str(model.status))
    if status != "Optimal":
        if status == "Infeasible":
            raise OptimizationError("The model is infeasible: demand cannot be met with the supplied inventory, capacities, active warehouses and shipping lanes. Check the validation report and input quantities.")
        raise OptimizationError(f"Solver did not prove an optimal solution. Status: {status}. Try a longer time limit or smaller input.")

    allocations = []
    for (w, r, sku), var in x.items():
        qty = float(var.value() or 0)
        if qty > 1e-7:
            allocations.append({
                "warehouse_id": w, "warehouse_name": warehouses.loc[w, "warehouse_name"],
                "restaurant_id": r, "restaurant_name": restaurants.loc[r, "restaurant_name"],
                "sku": sku, "product_name": products.loc[sku, "product_name"],
                "quantity_base_units": qty, "base_unit": products.loc[sku, "base_unit"],
                "shipping_cost": qty * float(ship[(w, r)]),
                "handling_cost": qty * float(handling[(w, sku)]),
            })
    allocation_df = pd.DataFrame(allocations, columns=[
        "warehouse_id", "warehouse_name", "restaurant_id", "restaurant_name", "sku", "product_name",
        "quantity_base_units", "base_unit", "shipping_cost", "handling_cost"])
    opened = [w for w in active if (use[w].value() or 0) > 0.5]
    fixed_cost_total = sum(float(warehouses.loc[w, "fixed_cost_per_period"]) for w in opened)
    shipping_total = float(allocation_df["shipping_cost"].sum()) if not allocation_df.empty else 0.0
    handling_total = float(allocation_df["handling_cost"].sum()) if not allocation_df.empty else 0.0
    demand_total = float(t["demand"]["demand_qty_base_units"].sum())
    capacity_used = allocation_df.groupby("warehouse_id")["quantity_base_units"].sum().to_dict() if not allocation_df.empty else {}
    warehouse_summary = []
    for w in active:
        used = float(capacity_used.get(w, 0.0))
        cap = float(warehouses.loc[w, "capacity_base_units"])
        warehouse_summary.append({"warehouse_id": w, "warehouse_name": warehouses.loc[w, "warehouse_name"],
                                  "opened": w in opened, "capacity_base_units": cap,
                                  "allocated_base_units": used,
                                  "capacity_utilization_pct": (100 * used / cap) if cap > 0 and w in opened else 0.0,
                                  "fixed_cost_per_period": float(warehouses.loc[w, "fixed_cost_per_period"]) if w in opened else 0.0})
    return {
        "status": status, "objective_cost": float(pulp.value(model.objective) or 0),
        "fixed_cost": fixed_cost_total, "shipping_cost": shipping_total, "handling_cost": handling_total,
        "demand_base_units": demand_total, "opened_warehouses": opened,
        "allocations": allocation_df, "warehouse_summary": pd.DataFrame(warehouse_summary),
        "warnings": validation.warnings,
    }
