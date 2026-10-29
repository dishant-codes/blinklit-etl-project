import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import (
    DATA_DIR,
    filter_orders,
    load_source_data,
    prepare_analytics_data,
    summarize_kpis,
)


st.set_page_config(
    page_title="Blinkit Business Analytics",
    page_icon="🛒",
    layout="wide",
)


@st.cache_data(show_spinner="Loading Blinkit data...")
def get_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    products, orders, order_items = load_source_data(DATA_DIR)
    return prepare_analytics_data(products, orders, order_items)


st.title("Blinkit Business Analytics")
st.caption("Sales, customer, product, and delivery performance from the supplied data.")

try:
    all_orders, all_items = get_dashboard_data()
except (FileNotFoundError, ValueError) as exc:
    st.error(f"Unable to load dashboard data: {exc}")
    st.stop()

min_date = all_orders["order_date"].min().date()
max_date = all_orders["order_date"].max().date()

with st.sidebar:
    st.header("Filters")
    selected_dates = st.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_dates, tuple):
        start_date = selected_dates[0] or min_date
        end_date = (selected_dates[-1] if len(selected_dates) > 1 else start_date)
        end_date = end_date or max_date
    else:
        start_date = end_date = selected_dates or max_date

    status_options = sorted(all_orders["delivery_status"].dropna().unique().tolist())
    selected_statuses = st.multiselect(
        "Delivery status", status_options, default=status_options
    )
    payment_options = sorted(all_orders["payment_method"].dropna().unique().tolist())
    selected_payments = st.multiselect(
        "Payment method", payment_options, default=payment_options
    )

filtered_orders = filter_orders(
    all_orders,
    start_date,
    end_date,
    selected_statuses,
    selected_payments,
)
filtered_order_ids = set(filtered_orders["order_id"])
filtered_items = all_items.loc[all_items["order_id"].isin(filtered_order_ids)].copy()

category_options = sorted(filtered_items["category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Product categories", category_options, default=category_options
)
category_items = filtered_items.loc[
    filtered_items["category"].isin(selected_categories)
].copy()

kpis = summarize_kpis(filtered_orders, filtered_items)
st.subheader("Business overview")
metric_rows = [
    [
        ("Gross sales", f"₹{kpis['gross_sales']:,.2f}", "Sum of source order totals"),
        ("Orders", f"{int(kpis['orders']):,}", "Unique orders in the selected period"),
        (
            "Average order value",
            f"₹{kpis['average_order_value']:,.2f}",
            "Gross sales divided by orders",
        ),
        ("Customers", f"{int(kpis['customers']):,}", "Unique customers with orders"),
    ],
    [
        ("Units sold", f"{kpis['units_sold']:,.0f}", "Sum of order-item quantities"),
        (
            "Repeat customer rate",
            f"{kpis['repeat_customer_rate']:.1f}%",
            "Customers with more than one selected order",
        ),
        (
            "On-time delivery",
            f"{kpis['on_time_rate']:.1f}%",
            "Orders marked On Time by the source data",
        ),
        (
            "Average delivery time",
            f"{kpis['average_delivery_minutes']:.1f} min",
            "Actual delivery timestamp minus order timestamp",
        ),
    ],
]

for row in metric_rows:
    columns = st.columns(4)
    for column, (label, value, help_text) in zip(columns, row):
        column.metric(label, value, help=help_text)

st.divider()
if filtered_orders.empty:
    st.info("No orders match the selected date, delivery, and payment filters.")
    st.stop()

st.subheader("Sales and delivery trends")
monthly = filtered_orders.assign(
    month=filtered_orders["order_date"].dt.to_period("M").dt.to_timestamp()
)
monthly = (
    monthly.groupby("month", as_index=False)
    .agg(gross_sales=("order_total", "sum"), orders=("order_id", "nunique"))
    .sort_values("month")
)

trend_column, delivery_column = st.columns((2, 1))
with trend_column:
    trend = px.line(
        monthly,
        x="month",
        y="gross_sales",
        markers=True,
        title="Monthly gross sales",
        labels={"month": "Month", "gross_sales": "Gross sales (INR)"},
    )
    trend.update_layout(margin=dict(l=12, r=12, t=55, b=12))
    st.plotly_chart(trend, width="stretch")

with delivery_column:
    delivery = (
        filtered_orders.groupby("delivery_status", as_index=False)
        .agg(orders=("order_id", "nunique"))
        .sort_values("orders", ascending=False)
    )
    status_chart = px.pie(
        delivery,
        names="delivery_status",
        values="orders",
        hole=0.55,
        title="Delivery status mix",
    )
    status_chart.update_layout(margin=dict(l=12, r=12, t=55, b=12))
    st.plotly_chart(status_chart, width="stretch")

st.subheader("Product performance")
st.caption(
    "Product and category sales use item quantity × unit price. "
    "Category selection affects this section only; order totals remain whole-order sales."
)
if category_items.empty:
    st.info("Select at least one product category to see product performance.")
else:
    category_sales = (
        category_items.groupby("category", as_index=False)
        .agg(item_sales=("line_revenue", "sum"), units=("quantity", "sum"))
        .sort_values("item_sales", ascending=False)
    )
    product_sales = (
        category_items.groupby(
            ["product_id", "product_name", "category", "brand"], as_index=False
        )
        .agg(item_sales=("line_revenue", "sum"), units=("quantity", "sum"))
        .sort_values("item_sales", ascending=False)
        .head(10)
    )

    category_column, product_column = st.columns(2)
    with category_column:
        category_chart = px.bar(
            category_sales,
            x="category",
            y="item_sales",
            title="Item sales by category",
            labels={"category": "Category", "item_sales": "Item sales (INR)"},
            text_auto=".2s",
        )
        category_chart.update_layout(
            margin=dict(l=12, r=12, t=55, b=12), xaxis_tickangle=-30
        )
        st.plotly_chart(category_chart, width="stretch")

    with product_column:
        product_chart = px.bar(
            product_sales.sort_values("item_sales"),
            x="item_sales",
            y="product_name",
            orientation="h",
            title="Top 10 products by item sales",
            labels={"product_name": "Product", "item_sales": "Item sales (INR)"},
            text_auto=".2s",
        )
        product_chart.update_layout(margin=dict(l=12, r=12, t=55, b=12))
        st.plotly_chart(product_chart, width="stretch")

    st.dataframe(
        product_sales.rename(
            columns={
                "product_id": "Product ID",
                "product_name": "Product",
                "category": "Category",
                "brand": "Brand",
                "units": "Units sold",
                "item_sales": "Item sales (INR)",
            }
        ),
        hide_index=True,
        width="stretch",
    )

st.subheader("Payment performance")
payment_sales = (
    filtered_orders.groupby("payment_method", as_index=False)
    .agg(gross_sales=("order_total", "sum"), orders=("order_id", "nunique"))
    .sort_values("gross_sales", ascending=False)
)
payment_chart = px.bar(
    payment_sales,
    x="payment_method",
    y="gross_sales",
    title="Gross sales by payment method",
    labels={"payment_method": "Payment method", "gross_sales": "Gross sales (INR)"},
    text_auto=".2s",
)
payment_chart.update_layout(margin=dict(l=12, r=12, t=55, b=12))
st.plotly_chart(payment_chart, width="stretch")

st.download_button(
    "Download filtered orders",
    data=filtered_orders.to_csv(index=False).encode("utf-8"),
    file_name="blinkit_filtered_orders.csv",
    mime="text/csv",
)
