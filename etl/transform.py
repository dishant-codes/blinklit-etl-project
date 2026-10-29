import re

import pandas as pd


aliases = {
    "product_id": ["product_id", "item_id", "productid"],
    "product_name": ["product_name", "item_name", "product", "item"],
    "category": ["category", "item_category", "product_category"],
    "brand": ["brand", "brand_name"],
    "price": ["price", "unit_price", "mrp"],
    "order_id": ["order_id", "orderid", "order_no", "order_number"],
    "order_date": ["order_date", "date", "orderdatetime"],
    "customer_id": ["customer_id", "customerid", "user_id"],
    "quantity": ["quantity", "qty", "units"],
    "status": ["status", "order_status", "delivery_status"],
    "payment_method": ["payment_method", "payment_type"],
    "city": ["city", "customer_city"],
    "delivery_minutes": ["delivery_minutes"],
    "delivery_time": ["delivery_time", "actual_delivery_time", "promised_delivery_time"],
    "unit_price": ["unit_price", "price"],
    "line_revenue": ["line_revenue", "total_price", "order_total"],
}


def find_columns(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column

    normalized_columns = {re.sub(r"[^a-z0-9]", "", column.lower()): column for column in df.columns}

    for column in candidates:
        key = re.sub(r"[^a-z0-9]", "", column.lower())
        if key in normalized_columns:
            return normalized_columns[key]

    return None


def rename_by_alias(df):
    rename_mapping = {}
    for key_name, candidates in aliases.items():
        found_column = find_columns(df, candidates)
        if found_column and found_column != key_name:
            rename_mapping[found_column] = key_name
    return df.rename(columns=rename_mapping)


def add_missing(df, columns):
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def clean_text(series):
    return (
        series.astype("string")
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )


def transform_products(products):
    columns = ["product_id", "product_name", "category", "brand", "price"]
    df = rename_by_alias(products.copy())
    df = add_missing(df, columns)

    for col in columns:
        df[col] = clean_text(df[col])

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.drop_duplicates(subset=["product_id"]).dropna(subset=["product_id"]).reset_index(drop=True)
    return df[columns]


def transform_orders(orders):
    columns = [
        "order_id",
        "order_date",
        "customer_id",
        "quantity",
        "status",
        "payment_method",
        "city",
        "delivery_minutes",
        "delivery_time",
    ]
    df = rename_by_alias(orders.copy())
    df = add_missing(df, columns)

    for col in ["order_id", "customer_id", "status", "payment_method", "city"]:
        df[col] = clean_text(df[col])

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1)
    df["delivery_minutes"] = pd.to_numeric(df["delivery_minutes"], errors="coerce")

    if "actual_delivery_time" in df.columns:
        df["delivery_time"] = pd.to_datetime(df["actual_delivery_time"], errors="coerce")
    elif "promised_delivery_time" in df.columns:
        df["delivery_time"] = pd.to_datetime(df["promised_delivery_time"], errors="coerce")
    else:
        df["delivery_time"] = pd.to_datetime(df["delivery_time"], errors="coerce")

    mask = df["delivery_minutes"].isna() & df["delivery_time"].notna() & df["order_date"].notna()
    if mask.any():
        df.loc[mask, "delivery_minutes"] = (
            (df.loc[mask, "delivery_time"] - df.loc[mask, "order_date"]).dt.total_seconds() / 60
        )

    df = df.dropna(subset=["order_id", "order_date"]).reset_index(drop=True)
    return df[columns]


def build_order_items(order_items, products):
    items = rename_by_alias(order_items.copy())
    items = add_missing(items, ["order_id", "product_id", "quantity", "unit_price"])

    items["order_id"] = clean_text(items["order_id"])
    items["product_id"] = clean_text(items["product_id"])
    items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce").fillna(1)
    items["unit_price"] = pd.to_numeric(items["unit_price"], errors="coerce")

    if "price" in products.columns:
        product_reference = products[["product_id", "price"]].rename(columns={"price": "unit_price"}).dropna(subset=["product_id"])
        items = items.merge(product_reference, on="product_id", how="left", suffixes=("", "_product"))
        items["unit_price"] = items["unit_price"].combine_first(items["unit_price_product"])
        items = items.drop(columns=["unit_price_product"], errors="ignore")

    items["line_revenue"] = items["quantity"] * items["unit_price"]
    items = items.dropna(subset=["order_id", "product_id"]).drop_duplicates().reset_index(drop=True)
    return items[["order_id", "product_id", "quantity", "unit_price", "line_revenue"]]


def build_orders(orders, order_items=None):
    df = rename_by_alias(orders.copy())
    df = add_missing(df, ["order_id", "order_date", "customer_id", "status", "payment_method", "city", "delivery_minutes", "delivery_time"])

    for col in ["order_id", "customer_id", "status", "payment_method", "city"]:
        df[col] = clean_text(df[col])

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["delivery_minutes"] = pd.to_numeric(df["delivery_minutes"], errors="coerce")
    df["delivery_time"] = pd.to_datetime(df["delivery_time"], errors="coerce")

    if order_items is not None and not order_items.empty:
        quantity_by_order = order_items.groupby("order_id", as_index=False)["quantity"].sum()
        quantity_by_order = quantity_by_order.rename(columns={"quantity": "order_item_quantity"})
        df = df.merge(quantity_by_order, on="order_id", how="left")
        if "quantity" in df.columns:
            df["quantity"] = df["quantity"].combine_first(df["order_item_quantity"])
        else:
            df["quantity"] = df["order_item_quantity"]
        df = df.drop(columns=["order_item_quantity"], errors="ignore")

    df = df.dropna(subset=["order_id", "order_date"]).drop_duplicates(subset=["order_id"]).reset_index(drop=True)
    return df[["order_id", "order_date", "customer_id", "quantity", "status", "payment_method", "city", "delivery_minutes", "delivery_time"]]


def transform(products, orders, order_items=None):
    products = transform_products(products)
    orders = transform_orders(orders)

    if order_items is not None:
        order_items = build_order_items(order_items, products)
        orders = build_orders(orders, order_items)
    else:
        orders = build_orders(orders)

    return products, orders, order_items

    