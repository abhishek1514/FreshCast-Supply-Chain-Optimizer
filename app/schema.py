"""Input schema and validation for restaurant distributor optimization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import pandas as pd

REQUIRED_COLUMNS: Mapping[str, list[str]] = {
    "warehouses": ["warehouse_id", "warehouse_name", "capacity_base_units", "fixed_cost_per_period", "active"],
    "restaurants": ["restaurant_id", "restaurant_name", "region"],
    "products": ["sku", "product_name", "base_unit"],
    "demand": ["restaurant_id", "sku", "demand_qty_base_units"],
    "inventory": ["warehouse_id", "sku", "available_qty_base_units", "handling_cost_per_base_unit"],
    "shipping_costs": ["warehouse_id", "restaurant_id", "cost_per_base_unit"],
}

NUMERIC_NONNEGATIVE = {
    "warehouses": ["capacity_base_units", "fixed_cost_per_period"],
    "demand": ["demand_qty_base_units"],
    "inventory": ["available_qty_base_units", "handling_cost_per_base_unit"],
    "shipping_costs": ["cost_per_base_unit"],
}

@dataclass
class ValidationResult:
    tables: dict[str, pd.DataFrame]
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_tables(tables: dict[str, pd.DataFrame]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    cleaned: dict[str, pd.DataFrame] = {}

    for name, required in REQUIRED_COLUMNS.items():
        if name not in tables:
            errors.append(f"Missing table: {name}")
            continue
        df = tables[name].copy()
        missing = [c for c in required if c not in df.columns]
        if missing:
            errors.append(f"{name}: missing required columns: {', '.join(missing)}")
            continue
        df = df[required].copy()
        if df.empty:
            errors.append(f"{name}: table is empty")
        for col in required:
            if df[col].isna().any():
                errors.append(f"{name}.{col}: contains blank/null values")
        id_cols = {
            "warehouses": ["warehouse_id"], "restaurants": ["restaurant_id"],
            "products": ["sku"], "demand": ["restaurant_id", "sku"],
            "inventory": ["warehouse_id", "sku"],
            "shipping_costs": ["warehouse_id", "restaurant_id"],
        }[name]
        if all(c in df for c in id_cols) and df.duplicated(id_cols).any():
            errors.append(f"{name}: duplicate key rows for {', '.join(id_cols)}")
        for col in NUMERIC_NONNEGATIVE.get(name, []):
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if df[col].isna().any():
                errors.append(f"{name}.{col}: must contain numeric values")
            elif (df[col] < 0).any():
                errors.append(f"{name}.{col}: negative values are not allowed")
        if name == "warehouses":
            valid_active = df["active"].astype(str).str.strip().str.lower().isin(["true", "false", "1", "0", "yes", "no"])
            if not valid_active.all():
                errors.append("warehouses.active: use true/false, yes/no, or 1/0")
            df["active"] = df["active"].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
        for col in id_cols:
            df[col] = df[col].astype(str).str.strip()
            if (df[col] == "").any():
                errors.append(f"{name}.{col}: blank identifiers are not allowed")
        cleaned[name] = df

    if errors:
        return ValidationResult(cleaned, errors, warnings)

    wh = set(cleaned["warehouses"]["warehouse_id"])
    restaurants = set(cleaned["restaurants"]["restaurant_id"])
    skus = set(cleaned["products"]["sku"])
    for name, cols, valid_sets in [
        ("demand", ["restaurant_id", "sku"], [restaurants, skus]),
        ("inventory", ["warehouse_id", "sku"], [wh, skus]),
        ("shipping_costs", ["warehouse_id", "restaurant_id"], [wh, restaurants]),
    ]:
        for col, valid in zip(cols, valid_sets):
            unknown = sorted(set(cleaned[name][col]) - valid)
            if unknown:
                errors.append(f"{name}.{col}: unknown IDs: {', '.join(unknown[:10])}")

    demand_keys = set(zip(cleaned["demand"]["restaurant_id"], cleaned["demand"]["sku"]))
    inventory_keys = set(zip(cleaned["inventory"]["warehouse_id"], cleaned["inventory"]["sku"]))
    cost_pairs = set(zip(cleaned["shipping_costs"]["warehouse_id"], cleaned["shipping_costs"]["restaurant_id"]))
    active_wh = set(cleaned["warehouses"].loc[cleaned["warehouses"]["active"], "warehouse_id"])
    if not active_wh:
        errors.append("At least one warehouse must be active")
    if cleaned["demand"]["demand_qty_base_units"].sum() <= 0:
        warnings.append("Total demand is zero; the optimizer may return a zero-cost plan")
    for r, sku in demand_keys:
        possible = any((w, sku) in inventory_keys and (w, r) in cost_pairs for w in active_wh)
        if not possible and cleaned["demand"].set_index(["restaurant_id", "sku"]).loc[(r, sku), "demand_qty_base_units"] > 0:
            errors.append(f"No active warehouse has both inventory for SKU {sku} and a shipping-cost row to restaurant {r}")
    return ValidationResult(cleaned, errors, warnings)
