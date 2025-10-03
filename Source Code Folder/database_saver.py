"""
Enhanced Database Saver for Approved Receipt Analysis
Supports dual product names, improved merchant location, and proper case formatting
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("Environment Configuration/.env")

class ReceiptDatabaseSaver:
    """Save approved receipt analysis to PostgreSQL database with enhanced features"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
    
    def save_approved_receipts(self, approved_receipts: List[Dict]) -> Dict:
        """Save all approved receipts to database"""
        results = {
            'saved_count': 0,
            'failed_count': 0,
            'saved_receipts': [],
            'failed_receipts': []
        }
        
        for receipt in approved_receipts:
            try:
                receipt_id = self.save_single_receipt(receipt)
                if receipt_id:
                    results['saved_count'] += 1
                    results['saved_receipts'].append({
                        'filename': receipt['filename'],
                        'receipt_id': receipt_id
                    })
                else:
                    results['failed_count'] += 1
                    results['failed_receipts'].append(receipt['filename'])
            except Exception as e:
                print(f"Failed to save {receipt['filename']}: {e}")
                results['failed_count'] += 1
                results['failed_receipts'].append(receipt['filename'])
        
        return results
    
    def save_single_receipt(self, receipt_analysis: Dict) -> int:
        """Save single receipt analysis to database with enhanced fields"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Extract data from analysis
            data = receipt_analysis['ai_analysis']['data']
            filename = receipt_analysis['filename']
            cloud_path = receipt_analysis.get('cloud_path', '')
            confidence = receipt_analysis.get('confidence', 'medium')
            
            # Step 1: Insert or get merchant with enhanced location data
            merchant_id = self.insert_or_get_enhanced_merchant(cursor, data['merchant'])
            
            # Step 2: Insert receipt record with confidence level
            receipt_id = self.insert_enhanced_receipt(
                cursor, filename, cloud_path, merchant_id, 
                data['transaction'], confidence
            )
            
            # Step 3: Insert receipt items with dual names
            self.insert_enhanced_receipt_items(cursor, receipt_id, data['items'])
            
            # Commit transaction
            conn.commit()
            
            print(f"Successfully saved {filename} to database (Receipt ID: {receipt_id})")
            return receipt_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Database save failed for {receipt_analysis['filename']}: {e}")
            raise
            
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def insert_or_get_enhanced_merchant(self, cursor, merchant_data: Dict) -> int:
        """Insert merchant with enhanced location fields or get existing merchant ID"""
        merchant_name = self.proper_case(merchant_data.get('name', 'Unknown'))
        merchant_address = merchant_data.get('address', '').strip()
        merchant_city = self.proper_case(merchant_data.get('city', ''))
        merchant_state = merchant_data.get('state', '').strip().upper()
        merchant_zip = merchant_data.get('zip_code', '').strip()
        merchant_phone = merchant_data.get('phone', '').strip()
        
        # Check if merchant already exists (by name, city, state)
        cursor.execute("""
            SELECT id FROM merchants 
            WHERE name = %s AND 
            (city = %s OR city IS NULL OR city = '') AND 
            (state = %s OR state IS NULL OR state = '')
        """, (merchant_name, merchant_city, merchant_state))
        
        existing = cursor.fetchone()
        if existing:
            # Update merchant with any new information if it was empty
            cursor.execute("""
                UPDATE merchants SET
                    address = COALESCE(NULLIF(address, ''), %s, address),
                    city = COALESCE(NULLIF(city, ''), %s, city),
                    state = COALESCE(NULLIF(state, ''), %s, state),
                    zip_code = COALESCE(NULLIF(zip_code, ''), %s, zip_code),
                    phone = COALESCE(NULLIF(phone, ''), %s, phone),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (merchant_address, merchant_city, merchant_state, 
                  merchant_zip, merchant_phone, existing['id']))
            
            return existing['id']
        
        # Insert new merchant with all location fields
        cursor.execute("""
            INSERT INTO merchants (name, address, city, state, zip_code, phone, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (merchant_name, merchant_address, merchant_city, 
              merchant_state, merchant_zip, merchant_phone, datetime.now()))
        
        return cursor.fetchone()['id']
    
    def insert_enhanced_receipt(self, cursor, filename: str, cloud_path: str, 
                               merchant_id: int, transaction_data: Dict, 
                               confidence: str) -> int:
        """Insert receipt record with enhanced fields"""
        
        # Parse transaction data
        receipt_date = self.parse_date(transaction_data.get('date'))
        receipt_time = self.parse_time(transaction_data.get('time'))
        subtotal = transaction_data.get('subtotal', 0.0)
        tax_amount = transaction_data.get('tax_amount', 0.0)
        total_amount = transaction_data.get('total_amount', 0.0)
        payment_method = self.proper_case(transaction_data.get('payment_method', ''))
        
        cursor.execute("""
            INSERT INTO receipts (
                merchant_id, filename, cloud_path, receipt_date, receipt_time,
                subtotal, tax_amount, total_amount, payment_method,
                status, confidence_level, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            merchant_id, filename, cloud_path, receipt_date, receipt_time,
            subtotal, tax_amount, total_amount, payment_method,
            'approved', confidence, datetime.now()
        ))
        
        return cursor.fetchone()['id']
    
    def insert_enhanced_receipt_items(self, cursor, receipt_id: int, items_data: List[Dict]):
        """Insert receipt items with dual naming system"""
        for i, item in enumerate(items_data, 1):
            # Get or create category
            category_id = self.get_or_create_category(cursor, item.get('category', 'Other'))
            
            # Get both product names
            receipt_name = self.proper_case(item.get('receipt_name', 
                                          item.get('name', 'Unknown Item')))
            standard_name = self.proper_case(item.get('standard_name', receipt_name))
            
            price = item.get('price', 0.0)
            quantity = item.get('quantity', 1.0)
            
            cursor.execute("""
                INSERT INTO receipt_items (
                    receipt_id, category_id, receipt_name, standard_name,
                    price, quantity, line_order, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                receipt_id, category_id, receipt_name, standard_name,
                price, quantity, i, datetime.now()
            ))
    
    def get_or_create_category(self, cursor, category_name: str) -> int:
        """Get existing category or create new one with proper case"""
        category_name = self.proper_case(category_name)
        
        # Check if category exists
        cursor.execute("""
            SELECT id FROM categories WHERE name = %s
        """, (category_name,))
        
        existing = cursor.fetchone()
        if existing:
            return existing['id']
        
        # Create new category
        cursor.execute("""
            INSERT INTO categories (name, description, is_active)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (category_name, f"Auto-created category for {category_name}", True))
        
        return cursor.fetchone()['id']
    
    def proper_case(self, text: str) -> str:
        """Convert text to proper case format"""
        if not text or str(text).strip() == '':
            return ''
        
        text = str(text).strip()
        
        # Handle special cases for common business names
        special_cases = {
            'TARGET': 'Target',
            'WALMART': 'Walmart', 
            'COSTCO': 'Costco',
            'BESTBUY': 'Best Buy',
            'BEST BUY': 'Best Buy',
            'MCDONALD\'S': 'McDonald\'s',
            'CVS': 'CVS',
            'WALGREENS': 'Walgreens'
        }
        
        if text.upper() in special_cases:
            return special_cases[text.upper()]
        
        # Regular title case
        return text.title()
    
    def parse_date(self, date_str) -> None:
        """Parse date string to database format"""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            from datetime import datetime
            
            # Try YYYY-MM-DD format
            if len(date_str) == 10 and '-' in date_str:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Try MM/DD/YYYY format
            if '/' in date_str and len(date_str) == 10:
                return datetime.strptime(date_str, '%m/%d/%Y').date()
            
            # Try MM/DD/YY format
            if '/' in date_str and len(date_str) == 8:
                return datetime.strptime(date_str, '%m/%d/%y').date()
                
        except Exception:
            pass
        
        return None
    
    def parse_time(self, time_str) -> None:
        """Parse time string to database format"""
        if not time_str:
            return None
        
        try:
            from datetime import datetime
            return datetime.strptime(time_str, '%H:%M:%S').time()
        except Exception:
            pass
        
        return None
    
    def get_database_summary(self) -> Dict:
        """Get enhanced summary of database contents"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get counts
            cursor.execute("SELECT COUNT(*) as count FROM receipts")
            receipts_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM receipt_items")
            items_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM merchants")
            merchants_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM categories")
            categories_count = cursor.fetchone()['count']
            
            # Get total spending
            cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as total FROM receipts")
            total_spending = cursor.fetchone()['total']
            
            # Get spending by location
            cursor.execute("""
                SELECT m.city, m.state, COUNT(r.id) as receipt_count, 
                       SUM(r.total_amount) as total_spent
                FROM merchants m
                JOIN receipts r ON m.id = r.merchant_id
                WHERE m.city IS NOT NULL AND m.city != ''
                GROUP BY m.city, m.state
                ORDER BY total_spent DESC
                LIMIT 5
            """)
            top_locations = cursor.fetchall()
            
            # Get top categories
            cursor.execute("""
                SELECT c.name, COUNT(ri.id) as item_count, 
                       SUM(ri.line_total) as category_total
                FROM categories c
                JOIN receipt_items ri ON c.id = ri.category_id
                GROUP BY c.id, c.name
                ORDER BY category_total DESC
                LIMIT 5
            """)
            top_categories = cursor.fetchall()
            
            # Get recent receipts with enhanced info
            cursor.execute("""
                SELECT r.filename, m.name as merchant, m.city, m.state,
                       r.total_amount, r.confidence_level, r.created_at
                FROM receipts r
                JOIN merchants m ON r.merchant_id = m.id
                ORDER BY r.created_at DESC
                LIMIT 5
            """)
            recent_receipts = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'receipts_count': receipts_count,
                'items_count': items_count,
                'merchants_count': merchants_count,
                'categories_count': categories_count,
                'total_spending': float(total_spending),
                'top_locations': [dict(r) for r in top_locations],
                'top_categories': [dict(r) for r in top_categories],
                'recent_receipts': [dict(r) for r in recent_receipts]
            }
            
        except Exception as e:
            print(f"Failed to get database summary: {e}")
            return {}
    
    def display_save_results(self, results: Dict):
        """Display enhanced save results to user"""
        print("\n" + "="*60)
        print("DATABASE SAVE RESULTS")
        print("="*60)
        
        print(f"Successfully saved: {results['saved_count']} receipts")
        print(f"Failed to save: {results['failed_count']} receipts")
        
        if results['saved_receipts']:
            print(f"\nSaved receipts:")
            for receipt in results['saved_receipts']:
                print(f"  ✓ {receipt['filename']} (ID: {receipt['receipt_id']})")
        
        if results['failed_receipts']:
            print(f"\nFailed receipts:")
            for filename in results['failed_receipts']:
                print(f"  ✗ {filename}")
        
        # Show enhanced database summary
        summary = self.get_database_summary()
        if summary:
            print(f"\nDATABASE SUMMARY:")
            print(f"Total receipts: {summary.get('receipts_count', 0)}")
            print(f"Total items: {summary.get('items_count', 0)}")
            print(f"Total merchants: {summary.get('merchants_count', 0)}")
            print(f"Total categories: {summary.get('categories_count', 0)}")
            print(f"Total spending: ${summary.get('total_spending', 0):.2f}")
            
            # Show top spending locations
            top_locations = summary.get('top_locations', [])
            if top_locations:
                print(f"\nTOP SPENDING LOCATIONS:")
                for loc in top_locations:
                    city_state = f"{loc['city']}, {loc['state']}" if loc['state'] else loc['city']
                    print(f"  {city_state}: ${loc['total_spent']:.2f} ({loc['receipt_count']} receipts)")
            
            # Show top categories
            top_categories = summary.get('top_categories', [])
            if top_categories:
                print(f"\nTOP SPENDING CATEGORIES:")
                for cat in top_categories:
                    print(f"  {cat['name']}: ${cat['category_total']:.2f} ({cat['item_count']} items)")


def test_database_connection():
    """Test enhanced database connection"""
    try:
        saver = ReceiptDatabaseSaver()
        summary = saver.get_database_summary()
        
        print("Enhanced Database Connection Test:")
        print(f"✓ Connected successfully")
        print(f"✓ Current receipts in database: {summary.get('receipts_count', 0)}")
        print(f"✓ Current items in database: {summary.get('items_count', 0)}")
        print(f"✓ Current merchants in database: {summary.get('merchants_count', 0)}")
        print(f"✓ Current categories in database: {summary.get('categories_count', 0)}")
        return True
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_database_connection()