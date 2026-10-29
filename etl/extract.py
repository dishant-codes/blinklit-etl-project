from pathlib import Path
import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {path} \n"
            "Please download the Blinkit dataset"
        )

    df = pd.read_csv(path)
    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        for column in df.columns
    ]
    return df


def extract(products_file: Path, order_file: Path, order_items_file: Path | None = None):
    products = read_csv(products_file)
    orders = read_csv(order_file)

    if order_items_file is not None and Path(order_items_file).exists():
        order_items = read_csv(order_items_file)
        return products, orders, order_items

    return products, orders
