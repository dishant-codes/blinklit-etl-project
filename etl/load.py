from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from etl.config import get_database_url


def get_engine() -> Engine:
    return create_engine(get_database_url(), future=True)


def load_data(engine: Engine, products, orders, order_items):
    if engine.url.get_backend_name() == "sqlite":
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys = OFF;"))
            conn.execute(text("DELETE FROM fact_order_items;"))
            conn.execute(text("DELETE FROM fact_orders;"))
            conn.execute(text("DELETE FROM dim_products;"))
            conn.execute(text("PRAGMA foreign_keys = ON;"))
    else:
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            conn.execute(text("DELETE FROM fact_order_items;"))
            conn.execute(text("DELETE FROM fact_orders;"))
            conn.execute(text("DELETE FROM dim_products;"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

    products.to_sql("dim_products", engine, if_exists="append", index=False, chunksize=1000)
    orders.to_sql("fact_orders", engine, if_exists="append", index=False, chunksize=1000)

    if order_items is not None and not order_items.empty:
        order_items.to_sql("fact_order_items", engine, if_exists="append", index=False, chunksize=1000)