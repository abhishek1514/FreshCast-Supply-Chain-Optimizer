from __future__ import annotations
import io
import os
import pandas as pd
import streamlit as st
from app.io import blank_template, read_table
from app.schema import REQUIRED_COLUMNS, validate_tables
from app.optimizer import optimize_distribution, OptimizationError
from app.public_demand import build_demand_from_sales, REQUIRED_SALES_COLUMNS

st.set_page_config(page_title="SupplyChain Optimizer", page_icon="📦", layout="wide")
st.title("📦 Restaurant Distributor · Supply Chain Optimizer")
st.caption("Plan warehouse-to-restaurant allocations using your own operational inputs. Public datasets can inform demand analysis, but they do not provide your verified warehouse costs or capacities.")

with st.sidebar:
    st.header("How it works")
    st.markdown("1. Download the six CSV templates.\n2. Fill them with data for the same planning period.\n3. Upload all six files.\n4. Validate, optimize and download the plan.")
    st.info("All quantities must use each SKU's declared base unit. Convert kg, g, cases, pieces, etc. before upload; do not mix units for the same SKU.")

st.subheader("Optional · Build demand from historical public sales data")
st.caption("Use this only when you have restaurant/SKU-level sales plus a documented recipe/BOM or product conversion. Restaurant order counts alone cannot be converted into ingredient quantities.")
with st.expander("Convert historical sales into demand.csv"):
    st.markdown("Required columns: `restaurant_id`, `sku`, `observed_sales_qty`, `base_units_per_sale`, `observed_period_days`, `planning_period_days`. The conversion factor must come from a documented menu/recipe or product mapping. This tool estimates demand only; it does not supply real inventory, warehouse capacity, fixed costs, or shipping rates.")
    sales_file = st.file_uploader("Upload mapped historical sales CSV/XLSX", type=["csv", "xlsx", "xls"], key="historical_sales")
    if sales_file is not None:
        try:
            sales_df = read_table(sales_file, "historical_sales")
            demand_df = build_demand_from_sales(sales_df)
            st.success(f"Built demand estimates for {len(demand_df)} restaurant-SKU pairs. These are estimates based on your supplied conversion factors, not verified future demand.")
            st.dataframe(demand_df, use_container_width=True, hide_index=True)
            st.download_button("Download generated demand.csv", demand_df.to_csv(index=False).encode("utf-8"), "demand.csv", "text/csv", key="download_generated_demand")
        except Exception as exc:
            st.error(f"Could not build demand: {exc}")
    st.download_button("Download historical sales mapping template", pd.DataFrame(columns=REQUIRED_SALES_COLUMNS).to_csv(index=False).encode("utf-8"), "historical_sales_to_demand.csv", "text/csv", key="historical_sales_template")


st.subheader("Public Data Forecast - Historical Demonstration")
forecast_path = "data/public/restaurant_forecasts.csv"

if os.path.exists(forecast_path):
    forecasts = pd.read_csv(forecast_path)

    if not forecasts.empty:
        st.warning(
            "This public dataset ends in June 2021. "
            "The forecast below is a historical demonstration, "
            "not a live forecast for the current date."
        )

        a, b, c = st.columns(3)
        a.metric("Restaurants forecast", len(forecasts))
        b.metric("Total forecast orders", f"{forecasts['forecast_orders'].sum():,.0f}")
        c.metric("Forecast month", str(forecasts["forecast_month"].iloc[0])[:7])

        st.dataframe(forecasts, use_container_width=True, hide_index=True)

        st.download_button(
            "Download restaurant forecasts (CSV)",
            forecasts.to_csv(index=False).encode("utf-8"),
            "restaurant_forecasts.csv",
            "text/csv",
            key="download_public_forecasts",
        )
    else:
        st.info("The forecast CSV exists but contains no rows.")
else:
    st.info(
        "Forecast file not found. Run `python restaurant_forecast.py` "
        "to generate the public-data demonstration forecast."
    )


st.subheader("Forecast to Ingredient Demand (Demo)")
st.caption(
    "Provide restaurant-specific ingredient usage per order. "
    "These conversion factors must come from recipes/BOM or be clearly labelled demo assumptions."
)

forecast_path = "data/public/restaurant_forecasts.csv"

if os.path.exists(forecast_path):
    forecast_df = pd.read_csv(forecast_path)
    st.info(
        "The bundled public forecast is historical (July 2021). "
        "This is a demonstration workflow, not a current live forecast."
    )

    st.markdown(
        "Upload a CSV with columns: `restaurant_id`, `sku`, "
        "`base_units_per_order`. Use one row per restaurant and ingredient SKU."
    )
    bom_file = st.file_uploader(
        "Upload recipe/BOM mapping CSV",
        type=["csv"],
        key="forecast_bom_mapping",
    )

    if bom_file is not None:
        try:
            bom = pd.read_csv(bom_file)
            required_bom = {"restaurant_id", "sku", "base_units_per_order"}
            missing_bom = required_bom - set(bom.columns)

            if missing_bom:
                st.error("Missing BOM columns: " + ", ".join(sorted(missing_bom)))
            elif bom.empty:
                st.error("The BOM mapping file is empty.")
            else:
                bom["restaurant_id"] = bom["restaurant_id"].astype(str).str.strip()
                bom["sku"] = bom["sku"].astype(str).str.strip()
                bom["base_units_per_order"] = pd.to_numeric(
                    bom["base_units_per_order"], errors="coerce"
                )

                if bom[["restaurant_id", "sku", "base_units_per_order"]].isna().any().any():
                    st.error("BOM mapping contains blank IDs or invalid quantities.")
                elif (bom["base_units_per_order"] < 0).any():
                    st.error("Ingredient quantities cannot be negative.")
                elif bom.duplicated(["restaurant_id", "sku"]).any():
                    st.error("Each restaurant_id + sku pair must appear only once.")
                else:
                    forecasts_clean = forecast_df.copy()
                    forecasts_clean["restaurant_id"] = (
                        forecasts_clean["restaurant_id"].astype(str).str.strip()
                    )

                    merged = forecasts_clean.merge(
                        bom,
                        on="restaurant_id",
                        how="left",
                        validate="one_to_many",
                        indicator=True,
                    )
                    unmatched = merged.loc[
                        merged["_merge"] == "left_only", "restaurant_id"
                    ].drop_duplicates()

                    if not unmatched.empty:
                        st.warning(
                            "No BOM mapping for forecast restaurants: "
                            + ", ".join(unmatched.head(10).tolist())
                        )

                    matched = merged[merged["_merge"] == "both"].copy()
                    if matched.empty:
                        st.error("No forecast restaurants matched the BOM mapping.")
                    else:
                        matched["demand_qty_base_units"] = (
                            pd.to_numeric(matched["forecast_orders"], errors="coerce")
                            * matched["base_units_per_order"]
                        )
                        demand_output = (
                            matched.groupby(
                                ["restaurant_id", "sku"], as_index=False
                            )["demand_qty_base_units"]
                            .sum()
                        )

                        st.success(
                            f"Generated estimated demand for {len(demand_output)} "
                            "restaurant-SKU pairs."
                        )
                        st.dataframe(
                            demand_output, use_container_width=True, hide_index=True
                        )
                        st.download_button(
                            "Download generated demand.csv",
                            demand_output.to_csv(index=False).encode("utf-8"),
                            "demand.csv",
                            "text/csv",
                            key="download_forecast_demand",
                        )
                        st.caption(
                            "Next: upload this downloaded file as demand.csv in the "
                            "optimizer. Verify units and planning period before use."
                        )
        except Exception as exc:
            st.error(f"Could not process BOM mapping: {exc}")
else:
    st.warning(
        "Forecast file not found. Run `python restaurant_forecast.py` first."
    )

st.subheader("1 · Download blank data templates")
cols = st.columns(3)
for idx, name in enumerate(REQUIRED_COLUMNS):
    with cols[idx % 3]:
        df = blank_template(name)
        st.download_button(f"Download {name}.csv", df.to_csv(index=False).encode("utf-8"), file_name=f"{name}.csv", mime="text/csv", key=f"template_{name}")

st.subheader("2 · Upload your data")
help_text = {
    "warehouses": "Warehouse list, available capacity and fixed operating cost for the planning period.",
    "restaurants": "Restaurant destinations and optional region labels.",
    "products": "Product/SKU master. Declare one canonical base unit per SKU.",
    "demand": "Demand for each restaurant and SKU over one common planning period.",
    "inventory": "Available stock by warehouse and SKU, plus handling cost per base unit.",
    "shipping_costs": "Outbound cost per base unit for each warehouse-to-restaurant lane.",
}
cols = st.columns(3)
uploaded = {}
for idx, name in enumerate(REQUIRED_COLUMNS):
    with cols[idx % 3]:
        st.markdown(f"**{name}.csv**")
        st.caption(help_text[name])
        f = st.file_uploader(f"Upload {name}", type=["csv", "xlsx", "xls"], key=f"upload_{name}", label_visibility="collapsed")
        if f is not None:
            try:
                uploaded[name] = read_table(f, name)
            except Exception as exc:
                st.error(f"Could not read {name}: {exc}")

if len(uploaded) == len(REQUIRED_COLUMNS):
    validation = validate_tables(uploaded)
    st.subheader("3 · Data validation")
    if validation.errors:
        st.error("Fix these issues before optimization:\n\n" + "\n".join(f"• {e}" for e in validation.errors))
    else:
        st.success("All required tables passed structural and referential validation.")
    for warning in validation.warnings:
        st.warning(warning)
    with st.expander("Preview uploaded data"):
        for name, df in validation.tables.items():
            st.markdown(f"**{name}** · {len(df):,} rows")
            st.dataframe(df.head(20), use_container_width=True)
    time_limit = st.number_input("Solver time limit (seconds)", min_value=1, max_value=300, value=30, step=5)
    if st.button("Run optimization", type="primary", disabled=not validation.ok, use_container_width=True):
        try:
            with st.spinner("Solving the distribution model..."):
                result = optimize_distribution(validation.tables, int(time_limit))
            st.subheader("4 · Optimized plan")
            a, b, c, d = st.columns(4)
            a.metric("Total modeled cost", f"{result['objective_cost']:,.2f}")
            b.metric("Fixed warehouse cost", f"{result['fixed_cost']:,.2f}")
            c.metric("Shipping cost", f"{result['shipping_cost']:,.2f}")
            d.metric("Handling cost", f"{result['handling_cost']:,.2f}")
            st.caption(f"Solver status: {result['status']} · Total demand: {result['demand_base_units']:,.3f} base units · Costs are in the same currency and period as your uploaded data.")
            st.markdown("**Warehouses selected**")
            st.write(", ".join(result["opened_warehouses"]) if result["opened_warehouses"] else "No warehouses opened")
            st.markdown("**Warehouse capacity utilization**")
            st.dataframe(result["warehouse_summary"], use_container_width=True, hide_index=True)
            st.markdown("**Shipment allocations**")
            st.dataframe(result["allocations"], use_container_width=True, hide_index=True)
            st.download_button("Download allocation plan (CSV)", result["allocations"].to_csv(index=False).encode("utf-8"), "optimized_allocations.csv", "text/csv")
            st.download_button("Download warehouse summary (CSV)", result["warehouse_summary"].to_csv(index=False).encode("utf-8"), "warehouse_summary.csv", "text/csv")
            st.success("Optimization completed. Validate the plan with your operations team before using it for live dispatch.")
        except (ValueError, OptimizationError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)
else:
    st.info(f"Upload all six required tables to continue. {len(uploaded)}/{len(REQUIRED_COLUMNS)} uploaded.")

st.divider()
st.caption("Decision-support prototype · No company data is bundled. No public dataset values are silently converted into real operating costs.")
