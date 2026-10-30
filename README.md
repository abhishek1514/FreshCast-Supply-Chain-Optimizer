# Restaurant Distributor Supply Chain Optimizer

A deployable Streamlit decision-support application for allocating product inventory from candidate warehouses to restaurants. It adapts the original repository's useful **fixed-cost + variable-cost mixed-integer optimization** approach from plant location to warehouse selection and restaurant distribution.

> **Data integrity:** no operational dataset is bundled. Existing original manufacturing Excel files are retained for reference but are not used by this restaurant-distributor app. Public datasets can inform demand analysis; they do not establish real warehouse costs, inventory, capacities or transport rates. Do not use unverified assumptions for live dispatch decisions.

## Features

- CSV/XLSX ingestion for six input tables.
- Structural, numeric, duplicate-key and foreign-key validation.
- Warehouse open/close binary decisions with fixed operating costs.
- Shipment allocation by warehouse, restaurant and SKU.
- Hard constraints for restaurant demand, per-SKU stock and total warehouse capacity.
- Shipping and handling costs, capacity utilization and downloadable CSV outputs.
- Unit policy: quantities for each SKU must be normalized to one declared base unit before upload.
- Automated tests, Docker image and Render deployment configuration.

## Run locally

Python 3.11+ (3.12 recommended).

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Input tables

Download blank templates in the app, or use the CSV headers below. All tables must describe the same planning period and currency.

| File/table | Required columns | Meaning |
|---|---|---|
| `warehouses` | `warehouse_id, warehouse_name, capacity_base_units, fixed_cost_per_period, active` | Total handling/dispatch capacity in normalized units for the period; fixed cost to operate a warehouse for the same period; whether it can be selected |
| `restaurants` | `restaurant_id, restaurant_name, region` | Delivery destinations |
| `products` | `sku, product_name, base_unit` | Product master; e.g. kg, L, piece or case |
| `demand` | `restaurant_id, sku, demand_qty_base_units` | Required quantity by restaurant and SKU |
| `inventory` | `warehouse_id, sku, available_qty_base_units, handling_cost_per_base_unit` | Available stock and handling cost |
| `shipping_costs` | `warehouse_id, restaurant_id, cost_per_base_unit` | Cost to ship one base unit along a warehouse-restaurant lane |

### Mixed inventory units

The model does not guess unit conversions. Normalize quantities before upload. For example, if a SKU's base unit is `kg`, convert 500 g to 0.5 kg; if a SKU's base unit is `piece`, do not upload case counts as pieces unless you have applied the verified pack-size conversion. For the same SKU, inventory and demand must use the same base unit. Currency and cost period must also be consistent.

### Cost objective

`total cost = selected warehouse fixed costs + shipping cost + handling cost`.

The model requires all demand to be met. It cannot silently drop demand. If stock/capacity/shipping lanes make the model infeasible, it reports an actionable error. Current model assumes deterministic demand, known stock/costs, no spoilage, no minimum order quantity, no time windows and no multi-period inventory carry-over.

## Tests

```bash
pytest -q
```

Tests use tiny explicitly artificial fixtures to verify model behavior. They are not operational or public business data.

## Docker

```bash
docker build -t restaurant-supply-chain-optimizer .
docker run --rm -p 8501:8501 restaurant-supply-chain-optimizer
```

Then open `http://localhost:8501`.

## Deploy on Render

1. Push this repository to your Git provider.
2. In Render, create a new **Blueprint** from the repository (or create a Docker web service).
3. Render reads `render.yaml` and builds the Dockerfile.
4. Wait for the `/_stcore/health` health check to pass.
5. Open the service URL and upload all six verified input tables.

The repository contains no secrets. If you later add a database or API key, keep secrets in the host's environment variables, not in Git. This starter app is unauthenticated and should not be exposed as a multi-tenant production service until authentication, authorization, upload limits, persistent audit logs and operational monitoring are added.

## Public data sources

See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). Public historical restaurant orders can support demand analysis, but do not provide a complete verified set of distributor inventory, warehouse capacity, freight and fixed costs. The app therefore accepts public or business data without misrepresenting missing cost data as real.

## Original project

The original `supply_chain_optimization.py`, notebook, and six Excel files are retained as reference material. The original code's manufacturing plant model uses different entities and unit assumptions; it is not called by the new restaurant-distributor app. Reconcile its `/1000` and `*1000` conversions with source units before reusing its original sample results.

## Historical sales → demand estimates

The app has an optional historical-sales conversion workflow and a downloadable `historical_sales_to_demand.csv` template. Required fields are `restaurant_id, sku, observed_sales_qty, base_units_per_sale, observed_period_days, planning_period_days`. The sales-to-base-unit factor must be sourced from a documented recipe/BOM or product mapping. This creates a demand estimate only; it does not make missing operating costs or inventory into real data. Review the output before using it in the optimizer.
