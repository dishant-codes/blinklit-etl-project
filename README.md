# Blinkit Business Analytics

An interactive Streamlit dashboard for sales, customers, products, payments, and delivery performance. The app reads the CSVs in `data/raw` directly, so it does not depend on a prebuilt SQLite database.

## Run locally

On Windows, use a short virtual-environment path to avoid package extraction path-length limits:

```powershell
python -m venv C:\blinkit-venv
C:\blinkit-venv\Scripts\python.exe -m pip install -r requirements.txt
C:\blinkit-venv\Scripts\python.exe -m streamlit run app.py
```

On macOS or Linux:

```shell
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Use the public repository [dishant-codes/blinklit-etl-project](https://github.com/dishant-codes/blinklit-etl-project), which contains `app.py`, `analytics.py`, `requirements.txt`, and the three CSV files in `data/raw`.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), sign in with GitHub and create an app from that repository.
3. Select the `main` branch, set the entry point to `app.py`, and deploy.

The dashboard does not need `.env` or database credentials. Do not commit `.env`.

## Business metric definitions

- Gross sales and average order value use the source `order_total` for each order.
- Product and category sales use order-item `quantity × unit_price`; category selection only filters product analytics, not whole-order sales.
- Delivery duration is actual delivery time minus order time. On-time rate counts orders whose source status is `On Time`.
- Repeat customer rate is the share of customers with more than one order in the active date, delivery-status, and payment filters.
- Date, delivery-status, and payment filters apply across the dashboard.
