"""
Database Setup Script in Python
Creates enhanced receipt tracker database schema programmatically
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv("Environment Configuration/.env")

class DatabaseSetup:
    """Setup enhanced database schema for receipt tracking system"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
    
    def create_enhanced_schema(self, drop_existing=False):
        """Create complete enhanced database schema"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            print("Creating enhanced receipt tracker database schema...")
            
            if drop_existing:
                print("Dropping existing tables...")
                self.drop_tables(cursor)
            
            print("Creating tables...")
            self.create_tables(cursor)
            
            print("Creating indexes...")
            self.create_indexes(cursor)
            
            print("Creating triggers and functions...")
            self.create_triggers_and_functions(cursor)
            
            print("Creating views...")
            self.create_views(cursor)
            
            print("Inserting default data...")
            self.insert_default_data(cursor)
            
            conn.commit()
            print("Database schema created successfully!")
            
            # Show summary
            self.show_schema_summary(cursor)
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error creating schema: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def drop_tables(self, cursor):
        """Drop existing tables if they exist"""
        drop_statements = [
            "DROP TABLE IF EXISTS receipt_items CASCADE;",
            "DROP TABLE IF EXISTS receipts CASCADE;", 
            "DROP TABLE IF EXISTS merchants CASCADE;",
            "DROP TABLE IF EXISTS categories CASCADE;"
        ]
        
        for statement in drop_statements:
            cursor.execute(statement)
            print(f"  Executed: {statement}")
    
    def create_tables(self, cursor):
        """Create all tables with enhanced structure"""
        
        # Categories table
        cursor.execute("""
            CREATE TABLE categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                parent_category_id INTEGER REFERENCES categories(id),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("  Created: categories table")
        
        # Merchants table with enhanced location fields
        cursor.execute("""
            CREATE TABLE merchants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(2),
                zip_code VARCHAR(10),
                phone VARCHAR(20),
                website VARCHAR(255),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, city, state)
            );
        """)
        print("  Created: merchants table")
        
        # Receipts table with enhanced fields
        cursor.execute("""
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
                currency VARCHAR(3) DEFAULT 'USD',
                status VARCHAR(20) DEFAULT 'approved',
                confidence_level VARCHAR(10),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("  Created: receipts table")
        
        # Receipt items table with dual naming
        cursor.execute("""
            CREATE TABLE receipt_items (
                id SERIAL PRIMARY KEY,
                receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES categories(id),
                receipt_name VARCHAR(300) NOT NULL,
                standard_name VARCHAR(200) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                quantity DECIMAL(8,2) DEFAULT 1.00,
                line_total DECIMAL(10,2) GENERATED ALWAYS AS (price * quantity) STORED,
                line_order INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("  Created: receipt_items table")
    
    def create_indexes(self, cursor):
        """Create performance indexes"""
        indexes = [
            "CREATE INDEX idx_receipts_merchant_id ON receipts(merchant_id);",
            "CREATE INDEX idx_receipts_date ON receipts(receipt_date);",
            "CREATE INDEX idx_receipt_items_receipt_id ON receipt_items(receipt_id);",
            "CREATE INDEX idx_receipt_items_category_id ON receipt_items(category_id);", 
            "CREATE INDEX idx_receipt_items_standard_name ON receipt_items(standard_name);",
            "CREATE INDEX idx_merchants_location ON merchants(city, state);"
        ]
        
        for index in indexes:
            cursor.execute(index)
            print(f"  Created index: {index.split('ON')[0].split('INDEX')[1].strip()}")
    
    def create_triggers_and_functions(self, cursor):
        """Create automatic timestamp update triggers"""
        
        # Function for updating timestamps
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        print("  Created: update_updated_at_column function")
        
        # Triggers for each table
        triggers = [
            ("merchants", "update_merchants_updated_at"),
            ("receipts", "update_receipts_updated_at"),
            ("receipt_items", "update_receipt_items_updated_at"),
            ("categories", "update_categories_updated_at")
        ]
        
        for table, trigger_name in triggers:
            cursor.execute(f"""
                CREATE TRIGGER {trigger_name}
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """)
            print(f"  Created trigger: {trigger_name}")
        
        # Proper case function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION proper_case(input_text TEXT)
            RETURNS TEXT AS $$
            BEGIN
                IF input_text IS NULL OR input_text = '' THEN
                    RETURN input_text;
                END IF;
                RETURN INITCAP(LOWER(TRIM(input_text)));
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("  Created: proper_case function")
    
    def create_views(self, cursor):
        """Create useful views for common queries"""
        
        # Receipt summary view
        cursor.execute("""
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
                r.confidence_level,
                COUNT(ri.id) as item_count,
                r.created_at
            FROM receipts r
            JOIN merchants m ON r.merchant_id = m.id
            LEFT JOIN receipt_items ri ON r.id = ri.receipt_id
            GROUP BY r.id, m.name, m.city, m.state;
        """)
        print("  Created view: v_receipt_summary")
        
        # Spending by category view
        cursor.execute("""
            CREATE VIEW v_spending_by_category AS
            SELECT 
                c.name as category_name,
                COUNT(ri.id) as item_count,
                SUM(ri.line_total) as total_spent,
                AVG(ri.price) as avg_item_price
            FROM categories c
            LEFT JOIN receipt_items ri ON c.id = ri.category_id
            GROUP BY c.id, c.name
            ORDER BY total_spent DESC NULLS LAST;
        """)
        print("  Created view: v_spending_by_category")
        
        # Merchant summary view
        cursor.execute("""
            CREATE VIEW v_merchant_summary AS
            SELECT 
                m.name,
                m.city,
                m.state,
                COUNT(r.id) as receipt_count,
                COALESCE(SUM(r.total_amount), 0) as total_spent,
                COALESCE(AVG(r.total_amount), 0) as avg_per_receipt,
                MIN(r.receipt_date) as first_visit,
                MAX(r.receipt_date) as last_visit
            FROM merchants m
            LEFT JOIN receipts r ON m.id = r.merchant_id
            GROUP BY m.id, m.name, m.city, m.state
            ORDER BY total_spent DESC;
        """)
        print("  Created view: v_merchant_summary")
    
    def insert_default_data(self, cursor):
        """Insert default categories and sample data"""
        
        # Default categories
        categories = [
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
            ('Other', 'Miscellaneous items')
        ]
        
        for name, description in categories:
            cursor.execute("""
                INSERT INTO categories (name, description) 
                VALUES (%s, %s) ON CONFLICT (name) DO NOTHING
            """, (name, description))
        
        print(f"  Inserted {len(categories)} default categories")
    
    def show_schema_summary(self, cursor):
        """Show summary of created schema"""
        print("\nDatabase Schema Summary:")
        print("=" * 40)
        
        # Count tables
        cursor.execute("""
            SELECT COUNT(*) as table_count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]
        
        # Count views
        cursor.execute("""
            SELECT COUNT(*) as view_count 
            FROM information_schema.views 
            WHERE table_schema = 'public'
        """)
        view_count = cursor.fetchone()[0]
        
        # Count indexes
        cursor.execute("""
            SELECT COUNT(*) as index_count 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        index_count = cursor.fetchone()[0]
        
        # Count categories
        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]
        
        print(f"Tables created: {table_count}")
        print(f"Views created: {view_count}")
        print(f"Indexes created: {index_count}")
        print(f"Default categories: {category_count}")
        
        # Show table details
        print(f"\nTable Structure:")
        tables = ['categories', 'merchants', 'receipts', 'receipt_items']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            
            cursor.execute(f"""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            col_count = cursor.fetchone()[0]
            
            print(f"  {table}: {col_count} columns, {row_count} rows")

def main():
    """Main function to setup database"""
    print("Enhanced Receipt Tracker Database Setup")
    print("=" * 50)
    
    try:
        setup = DatabaseSetup()
        
        # Ask user if they want to drop existing tables
        print("This will create the enhanced database schema.")
        drop_existing = input("Drop existing tables? (y/N): ").lower().strip() == 'y'
        
        if drop_existing:
            print("WARNING: This will delete all existing data!")
            confirm = input("Are you sure? Type 'YES' to confirm: ").strip()
            if confirm != 'YES':
                print("Setup cancelled.")
                return
        
        setup.create_enhanced_schema(drop_existing=drop_existing)
        
        print("\nSetup completed successfully!")
        print("You can now run your receipt processing system.")
        
    except Exception as e:
        print(f"Setup failed: {e}")

if __name__ == "__main__":
    main()