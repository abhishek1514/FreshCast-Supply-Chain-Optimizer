# Public data sources and what they can (and cannot) support

This repository intentionally ships **no fabricated operational dataset**. The upload templates are empty. The optimizer requires the operator to provide verified warehouse capacity, stock, demand, shipping costs, handling costs and fixed costs for one common planning period.

## Public restaurant demand data

- **Dataset of Number of Orders of Clients and Restaurants from a Delivery Food Application** — real historical sales from the Encalientes delivery platform, covering January 2019–June 2021, 642 restaurants and 100 top users. Dataset page: https://data.mendeley.com/datasets/2h5v92w5hm/1. DOI: https://doi.org/10.17632/2h5v92w5hm.1. The publisher lists CC BY 4.0. It can inform restaurant-level historical demand analysis, but it is not warehouse inventory, wholesale purchasing, unit cost, route cost or capacity data.
- **FreshRetailNet-50K** — food-retail hourly demand benchmark covering 50,000 item time series, 898 stores and 18 cities. Dataset overview: https://www.innovatiana.com/en/datasets/freshretailnet-50k. Check the original publisher's terms and download instructions before redistribution or production use. This dataset is a forecasting benchmark, not a complete restaurant-distributor operating dataset.

## Data integration policy

1. Public order/sales data may be used to estimate historical demand only after understanding its columns, time aggregation, missing-value meaning, licensing and geographic scope.
2. Never treat sales as unconstrained demand without checking stockouts, cancellations, coverage and observation bias.
3. Never infer actual warehouse capacities, fixed operating costs, inventory balances or shipping rates from a demand dataset.
4. Any estimates entered for a prototype must be explicitly labelled as assumptions and must not be presented as verified business facts.
5. Before live deployment, replace assumptions with business-approved operational data and reconcile costs/units with finance and logistics teams.
