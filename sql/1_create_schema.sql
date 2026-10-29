CREATE TABLE IF NOT EXISTS dim_products(
    product_id VARCHAR(100) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(150),
    brand VARCHAR(150),
    price DECIMAL(14,2),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_orders(
    order_id VARCHAR(100) PRIMARY KEY,
    order_date DATETIME,
    customer_id VARCHAR(100),
    quantity INT,
    status VARCHAR(50),
    payment_method VARCHAR(100),
    city VARCHAR(150),
    delivery_minutes INT,
    delivery_time DATETIME,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_order_items(
    order_id VARCHAR(100),
    product_id VARCHAR(100),
    quantity DECIMAL(14,3) NOT NULL DEFAULT 1,
    unit_price DECIMAL(14,2),
    line_revenue DECIMAL(16,2),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES fact_orders(order_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
);
