from etl.config import BASE_DIR, ORDER_ITEMS_FILE, ORDER_FILE, PRODUCT_FILE, execute_sql_file, get_db_connection
from etl.extract import extract
from etl.load import get_engine, load_data
from etl.transform import transform


def main():
    print("1. Extracting data from CSV files...")
    products, orders, order_items = extract(PRODUCT_FILE, ORDER_FILE, ORDER_ITEMS_FILE)

    print(f" Products extracted: {len(products)} rows")
    print(f" Orders extracted: {len(orders)} rows")
    print(f" Order items extracted: {len(order_items)} rows")

    print("2. Transforming data...")
    transformed_products, transformed_orders, transformed_order_items = transform(products, orders, order_items)

    print(f" Products transformed: {len(transformed_products)} rows")
    print(f" Orders transformed: {len(transformed_orders)} rows")
    print(f" Order items transformed: {len(transformed_order_items)} rows")

    print("3. Connecting to the database...")
    connection = get_db_connection()

    print("4. Creating Schema and Tables...")
    execute_sql_file(connection, BASE_DIR / "sql" / "1_create_schema.sql")

    print("5. Loading data into database...")
    engine = get_engine()
    load_data(engine, transformed_products, transformed_orders, transformed_order_items)

    print("ETL process completed successfully.")


if __name__ == "__main__":
    main()