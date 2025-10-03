-- Updated Database Schema for Enhanced Receipt Tracker
-- Supports dual product names, improved merchant location, and proper case formatting

-- Drop existing tables if recreating
DROP TABLE IF EXISTS receipt_items CASCADE;
DROP TABLE IF EXISTS receipts CASCADE;
DROP TABLE IF EXISTS merchants CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- Categories table (enhanced)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Merchants table (enhanced with location fields)
CREATE TABLE merchants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2), -- US state abbreviation
    zip_code VARCHAR(10),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Add unique constraint to prevent duplicate merchants
    UNIQUE(name, city, state)
);

-- Receipts table (enhanced)
CREATE TABLE receipts (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL REFERENCES merchants(id),
    filename VARCHAR(255) NOT NULL,
    cloud_path VARCHAR(500),
    receipt_date DATE,
    receipt_time TIME,
    subtotal DECIMAL(10,2) DEFAULT 0.00,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50),
    currency VARCHAR(3) DEFAULT 'CAD',
    status VARCHAR(20) DEFAULT 'approved',
    confidence_level VARCHAR(10), -- high, medium, low
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Receipt items table (enhanced with dual naming)
CREATE TABLE receipt_items (
    id SERIAL PRIMARY KEY,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id),
    receipt_name VARCHAR(300) NOT NULL, -- Exact name from receipt
    standard_name VARCHAR(200) NOT NULL, -- Standardized product name
    price DECIMAL(10,2) NOT NULL,
    quantity DECIMAL(8,2) DEFAULT 1.00,
    line_total DECIMAL(10,2) GENERATED ALWAYS AS (price * quantity) STORED,
    line_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_receipts_merchant_id ON receipts(merchant_id);
CREATE INDEX idx_receipts_date ON receipts(receipt_date);
CREATE INDEX idx_receipt_items_receipt_id ON receipt_items(receipt_id);
CREATE INDEX idx_receipt_items_category_id ON receipt_items(category_id);
CREATE INDEX idx_receipt_items_standard_name ON receipt_items(standard_name);
CREATE INDEX idx_merchants_location ON merchants(city, state);

-- Insert default categories with proper case
INSERT INTO categories (name, description) VALUES 
('Electronics', 'Electronic devices and accessories'),
('Groceries', 'Food items and household consumables'),
('Clothing', 'Apparel and fashion items'),
('Home & Garden', 'Home improvement and gardening supplies'),
('Personal Care', 'Health and beauty products'),
('Dining', 'Restaurant meals and takeout'),
('Transportation', 'Fuel, parking, and transit expenses'),
('Entertainment', 'Movies, games, and recreational activities'),
('Health & Beauty', 'Medical and cosmetic products'),
('Office Supplies', 'Business and office materials'),
('Other', 'Miscellaneous items');

-- Function to automatically update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_merchants_updated_at 
    BEFORE UPDATE ON merchants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_receipts_updated_at 
    BEFORE UPDATE ON receipts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_receipt_items_updated_at 
    BEFORE UPDATE ON receipt_items 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at 
    BEFORE UPDATE ON categories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for common queries
CREATE VIEW v_receipt_summary AS
SELECT 
    r.id,
    r.filename,
    m.name as merchant_name,
    m.city,
    m.state,
    r.receipt_date,
    r.total_amount,
    r.status,
    COUNT(ri.id) as item_count,
    r.created_at
FROM receipts r
JOIN merchants m ON r.merchant_id = m.id
LEFT JOIN receipt_items ri ON r.id = ri.receipt_id
GROUP BY r.id, m.name, m.city, m.state;

CREATE VIEW v_spending_by_category AS
SELECT 
    c.name as category_name,
    COUNT(ri.id) as item_count,
    SUM(ri.line_total) as total_spent,
    AVG(ri.price) as avg_item_price
FROM categories c
LEFT JOIN receipt_items ri ON c.id = ri.category_id
GROUP BY c.id, c.name
ORDER BY total_spent DESC;

CREATE VIEW v_merchant_summary AS
SELECT 
    m.name,
    m.city,
    m.state,
    COUNT(r.id) as receipt_count,
    SUM(r.total_amount) as total_spent,
    AVG(r.total_amount) as avg_per_receipt,
    MIN(r.receipt_date) as first_visit,
    MAX(r.receipt_date) as last_visit
FROM merchants m
LEFT JOIN receipts r ON m.id = r.merchant_id
GROUP BY m.id, m.name, m.city, m.state
ORDER BY total_spent DESC;

-- Function to clean and format text to proper case
CREATE OR REPLACE FUNCTION proper_case(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    IF input_text IS NULL OR input_text = '' THEN
        RETURN input_text;
    END IF;
    
    -- Convert to proper case: first letter uppercase, rest lowercase
    RETURN INITCAP(LOWER(TRIM(input_text)));
END;
$$ LANGUAGE plpgsql;

-- Sample data for testing (optional)
-- Uncomment these if you want test data

/*
-- Insert sample merchant
INSERT INTO merchants (name, address, city, state, zip_code, phone) 
VALUES ('Target', '123 Main Street', 'San Francisco', 'CA', '94102', '(415) 555-0123');

-- Insert sample receipt
INSERT INTO receipts (merchant_id, filename, receipt_date, subtotal, tax_amount, total_amount, status, confidence_level)
VALUES (1, 'target_receipt_001.jpg', '2024-01-15', 535.85, 49.59, 585.74, 'approved', 'high');

-- Insert sample items
INSERT INTO receipt_items (receipt_id, category_id, receipt_name, standard_name, price, quantity, line_order)
VALUES 
(1, 1, 'Big 42 Inch Led Tv', 'Television', 533.89, 1, 1),
(1, 1, 'Bluetooth Headphones', 'Headphones', 29.99, 1, 2),
(1, 5, 'Dave Shampoo 16oz', 'Shampoo', 12.98, 1, 3),
(1, 5, 'Dave Conditioner', 'Conditioner', 8.99, 1, 4);
*/

-- Display schema information
SELECT 'Database schema created successfully!' as status;


