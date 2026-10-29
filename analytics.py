from datetime import date
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"

REQUIRED_COLUMNS = {
    "products": {"product_id", "product_name", "category", "brand"},
    "orders": {
        "order_id",
        "customer_id",
        "order_date",
        "promised_delivery_time",
        "actual_delivery_time",
        "delivery_status",
        "order_total",
        "payment_method",
    },
    "order_items": {"order_id", "product_id", "quantity", "unit_price"},
}


def _read_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required source file not found: {path}")

    frame = pd.read_csv(path)
    frame.columns = [
        str(column).strip().lower().replace(" ", "_").replace("-", "_")
        for column in frame.columns
    ]
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{path.name} is missing required columns: {missing}")
    return frame


def load_source_data(
    data_dir: Path = DATA_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = _read_csv(data_dir / "blinkit_products.csv", REQUIRED_COLUMNS["products"])
    orders = _read_csv(data_dir / "blinkit_orders.csv", REQUIRED_COLUMNS["orders"])
    order_items = _read_csv(
        data_dir / "blinkit_order_items.csv", REQUIRED_COLUMNS["order_items"]
    )
    return products, orders, order_items


def _require_valid_values(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    invalid = {
        column: int(frame[column].isna().sum())
        for column in columns
        if frame[column].isna().any()
    }
    if invalid:
        details = ", ".join(f"{column}: {count}" for column, count in invalid.items())
        raise ValueError(f"{source} contains invalid or missing values ({details}).")


def prepare_analytics_data(
    products: pd.DataFrame,
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    products = products.copy()
    orders = orders.copy()
    order_items = order_items.copy()

    for frame, columns in (
        (products, ["product_id", "product_name", "category", "brand"]),
        (orders, ["order_id", "customer_id", "delivery_status", "payment_method"]),
        (order_items, ["order_id", "product_id"]),
    ):
        for column in columns:
            frame[column] = frame[column].astype("string").str.strip()
            frame[column] = frame[column].replace("", pd.NA)

    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["promised_delivery_time"] = pd.to_datetime(
        orders["promised_delivery_time"], errors="coerce"
    )
    orders["actual_delivery_time"] = pd.to_datetime(
        orders["actual_delivery_time"], errors="coerce"
    )
    orders["order_total"] = pd.to_numeric(orders["order_total"], errors="coerce")
    order_items["quantity"] = pd.to_numeric(order_items["quantity"], errors="coerce")
    order_items["unit_price"] = pd.to_numeric(order_items["unit_price"], errors="coerce")

    _require_valid_values(
        products, ["product_id", "product_name", "category"], "Products"
    )
    _require_valid_values(
        orders,
        [
            "order_id",
            "customer_id",
            "order_date",
            "promised_delivery_time",
            "actual_delivery_time",
            "delivery_status",
            "payment_method",
            "order_total",
        ],
        "Orders",
    )
    _require_valid_values(
        order_items, ["order_id", "product_id", "quantity", "unit_price"], "Order items"
    )

    if products["product_id"].duplicated().any():
        raise ValueError("Products contains duplicate product IDs.")
    if orders["order_id"].duplicated().any():
        raise ValueError("Orders contains duplicate order IDs.")
    if (orders["order_total"] < 0).any():
        raise ValueError("Orders contains a negative order total.")
    if (order_items["quantity"] <= 0).any():
        raise ValueError("Order items contains a non-positive quantity.")
    if (order_items["unit_price"] < 0).any():
        raise ValueError("Order items contains a negative unit price.")

    missing_orders = ~order_items["order_id"].isin(orders["order_id"])
    if missing_orders.any():
        raise ValueError(
            f"Order items references {int(missing_orders.sum())} unknown order IDs."
        )
    missing_products = ~order_items["product_id"].isin(products["product_id"])
    if missing_products.any():
        raise ValueError(
            f"Order items references {int(missing_products.sum())} unknown product IDs."
        )

    orders["delivery_minutes"] = (
        orders["actual_delivery_time"] - orders["order_date"]
    ).dt.total_seconds() / 60
    orders["delay_minutes"] = (
        orders["actual_delivery_time"] - orders["promised_delivery_time"]
    ).dt.total_seconds() / 60

    product_details = products[["product_id", "product_name", "category", "brand"]]
    items = order_items.merge(
        product_details, on="product_id", how="left", validate="many_to_one"
    )
    items["line_revenue"] = items["quantity"] * items["unit_price"]

    return orders, items


def filter_orders(
    orders: pd.DataFrame,
    start_date: date,
    end_date: date,
    statuses: list[str],
    payment_methods: list[str],
) -> pd.DataFrame:
    start = pd.Timestamp(start_date)
    end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)
    mask = orders["order_date"].ge(start) & orders["order_date"].lt(end_exclusive)
    mask &= orders["delivery_status"].isin(statuses)
    mask &= orders["payment_method"].isin(payment_methods)
    return orders.loc[mask].copy()


def summarize_kpis(orders: pd.DataFrame, items: pd.DataFrame) -> dict[str, float]:
    order_count = len(orders)
    customer_orders = orders["customer_id"].dropna().value_counts()
    customer_count = len(customer_orders)

    return {
        "gross_sales": float(orders["order_total"].sum()),
        "orders": float(order_count),
        "average_order_value": (
            float(orders["order_total"].sum() / order_count) if order_count else 0.0
        ),
        "customers": float(customer_count),
        "repeat_customer_rate": (
            float((customer_orders > 1).sum() / customer_count * 100)
            if customer_count
            else 0.0
        ),
        "units_sold": float(items["quantity"].sum()),
        "on_time_rate": (
            float(
                orders["delivery_status"]
                .str.casefold()
                .eq("on time")
                .mean()
                * 100
            )
            if order_count
            else 0.0
        ),
        "average_delivery_minutes": (
            float(orders["delivery_minutes"].mean()) if order_count else 0.0
        ),
    }
