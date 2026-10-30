# Public restaurant data: responsible integration path

The app's core optimizer is SKU-level. Public restaurant-order data is not automatically equivalent to distributor demand: restaurant sales counts do not tell us the ingredients consumed, recipe yields, waste, inventory on hand, pack sizes, delivery lead times or supplier prices.

## Suggested initial public source

Mendeley Data's *Dataset of Number of Orders of Clients and Restaurants from a Delivery Food Application* describes real platform sales at 642 restaurants in Aguascalientes, Mexico from January 2019 to June 2021. See https://data.mendeley.com/datasets/2h5v92w5hm/1 and DOI 10.17632/2h5v92w5hm.1.

Use it for a separate exploratory notebook: inspect the workbook, identify its month/customer/restaurant matrix, document missing cells, and calculate restaurant-level historical order counts. Do not directly load these counts into the SKU-level optimizer as food ingredient quantities. To create defensible SKU demand, a documented menu/recipe/BOM conversion and unit yield data are required; those may not be available in the public source.

## What is needed for a valid end-to-end public-data experiment

- Public sales/orders: restaurant demand signal only.
- SKU/product mapping and recipe/BOM: quantity of each ingredient/product required per sale.
- Opening inventory: warehouse-SKU stock in a normalized base unit.
- Warehouse capacity and fixed operating cost: source-backed, or explicitly marked scenario assumptions.
- Warehouse-to-restaurant lane costs: published rate source or explicitly marked scenario assumptions.

If the latter inputs are not published, run sensitivity scenarios with clearly labelled assumptions, not a claimed real-cost optimization. The app currently keeps these inputs operator-supplied and does not fabricate them.

## Implemented demand conversion workflow

The Streamlit app now includes an optional historical-sales conversion panel. Upload a CSV/XLSX with `restaurant_id`, `sku`, `observed_sales_qty`, `base_units_per_sale`, `observed_period_days`, and `planning_period_days`. It scales observed sales to the chosen planning horizon and converts each sale to the product's normalized base units. `base_units_per_sale` must come from a documented recipe/BOM or product mapping; do not invent it. This feature does not download third-party datasets automatically and does not derive warehouse inventory, capacity, fixed costs, or shipping rates.
