"""
Database Explorer for Receipt Analysis System
Shows database structure and content for learning purposes
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from tabulate import tabulate
import os
from dotenv import load_dotenv

load_dotenv("Environment Configuration/.env")

class DatabaseExplorer:
    """Explore and display database structure and content"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
    
    def explore_database(self):
        """Complete database exploration"""
        print("=" * 80)
        print("DATABASE STRUCTURE AND CONTENT EXPLORER")
        print("=" * 80)
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. Show database info
            self.show_database_info(cursor)
            
            # 2. Show all tables
            self.show_tables(cursor)
            
            # 3. Show table structures
            self.show_table_structures(cursor)
            
            # 4. Show table contents
            self.show_table_contents(cursor)
            
            # 5. Show relationships
            self.show_relationships(cursor)
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Database exploration failed: {e}")
    
    def show_database_info(self, cursor):
        """Show basic database information"""
        print("\n1. DATABASE INFORMATION")
        print("-" * 40)
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()['version']
        print(f"PostgreSQL Version: {version}")
        
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()['current_database']
        print(f"Current Database: {db_name}")
        
        cursor.execute("SELECT current_user;")
        user = cursor.fetchone()['current_user']
        print(f"Connected User: {user}")
    
    def show_tables(self, cursor):
        """Show all tables in database"""
        print("\n2. DATABASE TABLES")
        print("-" * 40)
        
        cursor.execute("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        table_data = []
        
        for table in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) as count FROM {table['table_name']};")
            row_count = cursor.fetchone()['count']
            
            table_data.append([
                table['table_name'],
                table['column_count'],
                row_count
            ])
        
        headers = ["Table Name", "Columns", "Rows"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def show_table_structures(self, cursor):
        """Show structure of each table"""
        print("\n3. TABLE STRUCTURES")
        print("-" * 40)
        
        # Get all tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table['table_name']
            print(f"\nTable: {table_name.upper()}")
            print("-" * 20)
            
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default,
                       character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            column_data = []
            
            for col in columns:
                data_type = col['data_type']
                if col['character_maximum_length']:
                    data_type += f"({col['character_maximum_length']})"
                
                column_data.append([
                    col['column_name'],
                    data_type,
                    col['is_nullable'],
                    col['column_default'] or 'None'
                ])
            
            headers = ["Column", "Data Type", "Nullable", "Default"]
            print(tabulate(column_data, headers=headers, tablefmt="grid"))
    
    def show_table_contents(self, cursor):
        """Show sample content from each table"""
        print("\n4. TABLE CONTENTS (Sample Data)")
        print("-" * 40)
        
        # Categories table
        print(f"\nCATEGORIES:")
        cursor.execute("SELECT * FROM categories ORDER BY id;")
        categories = cursor.fetchall()
        if categories:
            print(tabulate([dict(c) for c in categories], headers="keys", tablefmt="grid"))
        else:
            print("No data")
        
        # Merchants table
        print(f"\nMERCHANTS:")
        cursor.execute("SELECT * FROM merchants ORDER BY id;")
        merchants = cursor.fetchall()
        if merchants:
            print(tabulate([dict(m) for m in merchants], headers="keys", tablefmt="grid"))
        else:
            print("No data")
        
        # Receipts table
        print(f"\nRECEIPTS:")
        cursor.execute("""
            SELECT r.id, r.filename, m.name as merchant, r.receipt_date, 
                   r.total_amount, r.status, r.created_at
            FROM receipts r
            LEFT JOIN merchants m ON r.merchant_id = m.id
            ORDER BY r.id;
        """)
        receipts = cursor.fetchall()
        if receipts:
            print(tabulate([dict(r) for r in receipts], headers="keys", tablefmt="grid"))
        else:
            print("No data")
        
        # Receipt items (limited to avoid too much output)
        print(f"\nRECEIPT ITEMS (First 10):")
        cursor.execute("""
            SELECT ri.id, ri.receipt_id, ri.product_name, ri.price,
                   c.name as category, ri.line_order
            FROM receipt_items ri
            LEFT JOIN categories c ON ri.category_id = c.id
            ORDER BY ri.receipt_id, ri.line_order
            LIMIT 10;
        """)
        items = cursor.fetchall()
        if items:
            print(tabulate([dict(i) for i in items], headers="keys", tablefmt="grid"))
        else:
            print("No data")
    
    def show_relationships(self, cursor):
        """Show table relationships"""
        print("\n5. TABLE RELATIONSHIPS")
        print("-" * 40)
        
        cursor.execute("""
            SELECT 
                tc.table_name, 
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name;
        """)
        
        relationships = cursor.fetchall()
        
        if relationships:
            rel_data = []
            for rel in relationships:
                rel_data.append([
                    rel['table_name'],
                    rel['column_name'],
                    '→',
                    rel['foreign_table_name'],
                    rel['foreign_column_name']
                ])
            
            headers = ["Table", "Column", "", "References Table", "References Column"]
            print(tabulate(rel_data, headers=headers, tablefmt="grid"))
        else:
            print("No foreign key relationships found")
    
    def show_analytics(self, cursor):
        """Show business analytics from the data"""
        print("\n6. BUSINESS ANALYTICS")
        print("-" * 40)
        
        # Spending by merchant
        print(f"\nSPENDING BY MERCHANT:")
        cursor.execute("""
            SELECT m.name, COUNT(r.id) as receipt_count, 
                   SUM(r.total_amount) as total_spent,
                   AVG(r.total_amount) as avg_per_receipt
            FROM merchants m
            JOIN receipts r ON m.id = r.merchant_id
            GROUP BY m.id, m.name
            ORDER BY total_spent DESC;
        """)
        
        merchant_stats = cursor.fetchall()
        if merchant_stats:
            formatted_stats = []
            for stat in merchant_stats:
                formatted_stats.append([
                    stat['name'],
                    stat['receipt_count'],
                    f"${stat['total_spent']:.2f}",
                    f"${stat['avg_per_receipt']:.2f}"
                ])
            
            headers = ["Merchant", "Receipts", "Total Spent", "Avg/Receipt"]
            print(tabulate(formatted_stats, headers=headers, tablefmt="grid"))
        
        # Spending by category
        print(f"\nSPENDING BY CATEGORY:")
        cursor.execute("""
            SELECT c.name, COUNT(ri.id) as item_count, 
                   SUM(ri.price) as total_spent,
                   AVG(ri.price) as avg_price
            FROM categories c
            JOIN receipt_items ri ON c.id = ri.category_id
            GROUP BY c.id, c.name
            ORDER BY total_spent DESC;
        """)
        
        category_stats = cursor.fetchall()
        if category_stats:
            formatted_cat_stats = []
            for stat in category_stats:
                formatted_cat_stats.append([
                    stat['name'],
                    stat['item_count'],
                    f"${stat['total_spent']:.2f}",
                    f"${stat['avg_price']:.2f}"
                ])
            
            headers = ["Category", "Items", "Total Spent", "Avg Price"]
            print(tabulate(formatted_cat_stats, headers=headers, tablefmt="grid"))
    
    def export_data_to_csv(self):
        """Export database data to CSV files"""
        import csv
        from datetime import datetime
        
        print("\n7. EXPORTING DATA TO CSV")
        print("-" * 40)
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Create export directory
            export_dir = "Data Folders/database_export"
            os.makedirs(export_dir, exist_ok=True)
            
            # Export each table
            tables = ['categories', 'merchants', 'receipts', 'receipt_items']
            
            for table in tables:
                cursor.execute(f"SELECT * FROM {table};")
                data = cursor.fetchall()
                
                if data:
                    filename = f"{export_dir}/{table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                        writer.writeheader()
                        for row in data:
                            writer.writerow(dict(row))
                    
                    print(f"Exported {table}: {len(data)} rows → {filename}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Export failed: {e}")


def main():
    """Main function to run database exploration"""
    explorer = DatabaseExplorer()
    
    print("Starting database exploration...")
    explorer.explore_database()
    
    # Show analytics
    try:
        conn = psycopg2.connect(**explorer.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        explorer.show_analytics(cursor)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Analytics failed: {e}")
    
    # Ask if user wants to export data
    export_choice = input(f"\nExport database to CSV files? (y/N): ").strip().lower()
    if export_choice == 'y':
        explorer.export_data_to_csv()
    
    print("\nDatabase exploration completed!")


if __name__ == "__main__":
    main()