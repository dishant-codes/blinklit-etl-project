from datetime import date
import unittest

import pandas as pd

from analytics import filter_orders, prepare_analytics_data, summarize_kpis


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        products = pd.DataFrame(
            [
                {
                    "product_id": "p1",
                    "product_name": "Apples",
                    "category": "Produce",
                    "brand": "Fresh",
                },
                {
                    "product_id": "p2",
                    "product_name": "Milk",
                    "category": "Dairy",
                    "brand": "Farm",
                },
            ]
        )
        orders = pd.DataFrame(
            [
                {
                    "order_id": "o1",
                    "customer_id": "c1",
                    "order_date": "2024-01-01 10:00:00",
                    "promised_delivery_time": "2024-01-01 10:20:00",
                    "actual_delivery_time": "2024-01-01 10:18:00",
                    "delivery_status": "On Time",
                    "order_total": 30.0,
                    "payment_method": "UPI",
                },
                {
                    "order_id": "o2",
                    "customer_id": "c1",
                    "order_date": "2024-01-02 10:00:00",
                    "promised_delivery_time": "2024-01-02 10:20:00",
                    "actual_delivery_time": "2024-01-02 10:25:00",
                    "delivery_status": "Delayed",
                    "order_total": 70.0,
                    "payment_method": "Card",
                },
                {
                    "order_id": "o3",
                    "customer_id": "c2",
                    "order_date": "2024-01-03 10:00:00",
                    "promised_delivery_time": "2024-01-03 10:20:00",
                    "actual_delivery_time": "2024-01-03 10:19:00",
                    "delivery_status": "On Time",
                    "order_total": 50.0,
                    "payment_method": "UPI",
                },
            ]
        )
        order_items = pd.DataFrame(
            [
                {"order_id": "o1", "product_id": "p1", "quantity": 2, "unit_price": 5},
                {"order_id": "o2", "product_id": "p2", "quantity": 3, "unit_price": 10},
                {"order_id": "o3", "product_id": "p1", "quantity": 1, "unit_price": 5},
            ]
        )
        self.orders, self.items = prepare_analytics_data(
            products, orders, order_items
        )

    def test_kpis_use_order_totals_and_item_quantities(self):
        kpis = summarize_kpis(self.orders, self.items)

        self.assertEqual(kpis["gross_sales"], 150.0)
        self.assertEqual(kpis["average_order_value"], 50.0)
        self.assertEqual(kpis["orders"], 3.0)
        self.assertEqual(kpis["customers"], 2.0)
        self.assertEqual(kpis["repeat_customer_rate"], 50.0)
        self.assertEqual(kpis["units_sold"], 6.0)
        self.assertAlmostEqual(kpis["on_time_rate"], 200 / 3)
        self.assertAlmostEqual(kpis["average_delivery_minutes"], 62 / 3)
        self.assertEqual(self.items["line_revenue"].tolist(), [10, 30, 5])

    def test_filters_include_both_endpoint_dates(self):
        filtered = filter_orders(
            self.orders,
            date(2024, 1, 2),
            date(2024, 1, 3),
            ["Delayed", "On Time"],
            ["Card", "UPI"],
        )

        self.assertEqual(filtered["order_id"].tolist(), ["o2", "o3"])

    def test_empty_filters_return_no_orders(self):
        filtered = filter_orders(
            self.orders, date(2024, 1, 1), date(2024, 1, 3), [], ["Card", "UPI"]
        )

        self.assertTrue(filtered.empty)


if __name__ == "__main__":
    unittest.main()
