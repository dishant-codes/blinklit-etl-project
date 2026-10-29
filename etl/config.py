import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

PRODUCT_FILE = BASE_DIR / "data" / "raw" / "blinkit_products.csv"
ORDER_FILE = BASE_DIR / "data" / "raw" / "blinkit_orders.csv"
ORDER_ITEMS_FILE = BASE_DIR / "data" / "raw" / "blinkit_order_items.csv"
SQLITE_DB_PATH = BASE_DIR / "blinkit_analytics.db"


def execute_sql_file(connection, sql_file_path: Path):
    cursor = connection.cursor()
    try:
        sql_statements = sql_file_path.read_text(encoding="utf-8").split(";")
        for statement in sql_statements:
            statement = statement.strip()
            if not statement:
                continue
            normalized = statement.upper()
            if normalized.startswith("CREATE DATABASE") or normalized.startswith("USE "):
                continue
            cursor.execute(statement)
        connection.commit()
    finally:
        cursor.close()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "blinkit_analytics"),
    "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
    "autocommit": True,
}


def get_database_url():
    use_sqlite = os.getenv("USE_SQLITE", "true").strip().lower() in {"1", "true", "yes", "y"}
    if use_sqlite:
        return f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

    try:
        mysql.connector.connect(**DB_CONFIG).close()
    except Error:
        return f"sqlite:///{SQLITE_DB_PATH.as_posix()}"

    return (
        "mysql+mysqlconnector://"
        f"{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}"
        f"/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
    )


def get_db_connection():
    if os.getenv("USE_SQLITE", "true").strip().lower() in {"1", "true", "yes", "y"}:
        connection = sqlite3.connect(SQLITE_DB_PATH)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as exc:
        connection = sqlite3.connect(SQLITE_DB_PATH)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
