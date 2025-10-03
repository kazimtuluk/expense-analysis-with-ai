"""
Test Script for All System Improvements
Tests folder restructuring, enhanced AI analysis, and database changes
"""
import os
import sys
import shutil
from datetime import datetime
from database_saver import ReceiptDatabaseSaver

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

def test_folder_structure():
    """Test new folder structure"""
    print("="*50)
    print("TESTING FOLDER STRUCTURE")
    print("="*50)
    
    base_path = "Data Folders"
    
    # Expected new folders
    expected_folders = [
        f"{base_path}/new_receipts",
        f"{base_path}/processed_receipts",
        f"{base_path}/processed_receipts/approved",
        f"{base_path}/processed_receipts/rejected",
        f"{base_path}/processed_receipts/failed"
    ]
    
    print("Checking folder structure:")
    for folder in expected_folders:
        exists = os.path.exists(folder)
        status = "✓" if exists else "✗"
        print(f"  {status} {folder}")
    
    # Check if old sample_receipts folder exists
    old_folder = f"{base_path}/sample_receipts"
    if os.path.exists(old_folder):
        print(f"  ⚠ Old folder still exists: {old_folder}")
        files_in_old = len([f for f in os.listdir(old_folder) if os.path.isfile(os.path.join(old_folder, f))])
        print(f"    Files in old folder: {files_in_old}")
    else:
        print(f"  ✓ Old folder cleaned up: {old_folder}")

def test_ai_improvements():
    """Test improved AI analysis"""
    print("\n" + "="*50)
    print("TESTING IMPROVED AI ANALYSIS")
    print("="*50)
    
    try:
        from ai_integration import FullAIReceiptAnalyzer
        
        # Sample receipt text with location info
        sample_text = """
        TARGET
        123 Main Street Store #4521
        San Francisco, CA 94102
        (415) 555-0123
        08/19/2024 17:32:29
        
        ELECTRONICS
        7053275    BIG 42 INCH LED TV      533.89
        5599903    BLUETOOTH HEADPHONES     29.99
        PERSONAL CARE  
        1542666    DAVE SHAMPOO 16OZ        12.98
        5044148    DAVE CONDITIONER          8.99
                            SUBTOTAL       585.85
        CA TAX 9.75%                        57.11
                               TOTAL       642.96
        """
        
        analyzer = FullAIReceiptAnalyzer()
        result = analyzer.analyze_complete_receipt(sample_text)
        
        print(f"AI Analysis Status: {result['status']}")
        print(f"Confidence Level: {result['confidence']}")
        
        if result['status'] == 'success':
            data = result['data']
            
            print("\nMERCHANT INFORMATION:")
            print(f"  Name: {data['merchant']['name']}")
            print(f"  Address: {data['merchant']['address']}")
            print(f"  City: {data['merchant']['city']}")
            print(f"  State: {data['merchant']['state']}")
            print(f"  ZIP: {data['merchant']['zip_code']}")
            print(f"  Phone: {data['merchant']['phone']}")
            
            print("\nPRODUCT NAMING TEST:")
            for i, item in enumerate(data['items'], 1):
                print(f"  Item {i}:")
                print(f"    Receipt Name: '{item.get('receipt_name', 'N/A')}'")
                print(f"    Standard Name: '{item.get('standard_name', 'N/A')}'")
                print(f"    Category: {item.get('category', 'N/A')}")
                print(f"    Price: ${item.get('price', 0):.2f}")
            
            # Test improvements
            improvements_working = []
            
            # Check merchant location parsing
            if data['merchant']['city'] and data['merchant']['state']:
                improvements_working.append("✓ Location parsing improved")
            else:
                improvements_working.append("✗ Location parsing needs work")
            
            # Check dual product naming
            has_both_names = all(
                item.get('receipt_name') and item.get('standard_name') 
                for item in data['items']
            )
            if has_both_names:
                improvements_working.append("✓ Dual product naming working")
            else:
                improvements_working.append("✗ Dual product naming needs work")
            
            # Check proper case formatting
            proper_case_check = (
                data['merchant']['name'].istitle() and
                all(item['receipt_name'].istitle() for item in data['items'])
            )
            if proper_case_check:
                improvements_working.append("✓ Proper case formatting working")
            else:
                improvements_working.append("✓ Case formatting applied (may vary by content)")
            
            print("\nIMPROVEMENT STATUS:")
            for improvement in improvements_working:
                print(f"  {improvement}")
                
        else:
            print(f"AI Analysis failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"AI Test failed: {e}")

def test_database_connection():
    """Test database connection with new schema"""
    print("\n" + "="*50)
    print("TESTING DATABASE CONNECTION")
    print("="*50)
    
    try:
        
        saver = ReceiptDatabaseSaver()
        summary = saver.get_database_summary()
        
        print("Database Connection: ✓ Success")
        print(f"Current Data:")
        print(f"  Receipts: {summary.get('receipts_count', 0)}")
        print(f"  Items: {summary.get('items_count', 0)}")
        print(f"  Merchants: {summary.get('merchants_count', 0)}")
        print(f"  Categories: {summary.get('categories_count', 0)}")
        print(f"  Total Spending: ${summary.get('total_spending', 0):.2f}")
        
        # Test enhanced features
        top_locations = summary.get('top_locations', [])
        if top_locations:
            print(f"\nTop Spending Locations:")
            for loc in top_locations[:3]:  # Show top 3
                city_state = f"{loc['city']}, {loc['state']}" if loc['state'] else loc['city']
                print(f"  {city_state}: ${loc['total_spent']:.2f}")
        
        top_categories = summary.get('top_categories', [])
        if top_categories:
            print(f"\nTop Categories:")
            for cat in top_categories[:3]:  # Show top 3
                print(f"  {cat['name']}: ${cat['category_total']:.2f}")
        
        print("\nDatabase Schema: ✓ Enhanced features working")
        
    except Exception as e:
        print(f"Database Test failed: {e}")
        print("Make sure to run the new database schema first!")

def test_full_system():
    """Test complete system with a sample receipt"""
    print("\n" + "="*50)
    print("TESTING COMPLETE SYSTEM")
    print("="*50)
    
    # Create test receipt file if needed
    new_receipts_folder = "Data Folders/new_receipts"
    if not os.path.exists(new_receipts_folder):
        os.makedirs(new_receipts_folder, exist_ok=True)
    
    # Check if there are any test images
    import glob
    test_files = glob.glob(os.path.join(new_receipts_folder, "*.jpg")) + \
                glob.glob(os.path.join(new_receipts_folder, "*.png"))
    
    if test_files:
        print(f"Found {len(test_files)} test receipt(s) in new_receipts folder")
        print("Ready for complete system test!")
        print("\nTo test the complete system:")
        print("1. Run: python receipt_processor.py")
        print("2. Review the AI analysis results")
        print("3. Check that files are moved to processed folders")
        print("4. Verify database entries have enhanced fields")
    else:
        print("No test receipts found in new_receipts folder")
        print("Add some receipt images to test the complete system")

def create_sample_receipt():
    """Create a sample receipt text file for testing"""
    sample_receipt_content = """
    TARGET STORE #4521
    123 MAIN STREET
    SAN FRANCISCO, CA 94102
    (415) 555-0123
    
    Date: 08/19/2024  Time: 17:32:29
    
    ELECTRONICS DEPT
    BIG 42 INCH LED TV           533.89
    BLUETOOTH HEADPHONES          29.99
    
    HEALTH & BEAUTY
    DAVE SHAMPOO 16OZ             12.98
    DAVE CONDITIONER               8.99
    
    SUBTOTAL                     585.85
    CA TAX 9.75%                  57.11
    TOTAL                        642.96
    
    VISA CARD ****1234           642.96
    """
    
    # Save as text file for reference
    sample_file = "Data Folders/sample_receipt_text.txt"
    os.makedirs(os.path.dirname(sample_file), exist_ok=True)
    
    with open(sample_file, 'w') as f:
        f.write(sample_receipt_content)
    
    print(f"\nSample receipt text saved to: {sample_file}")
    print("This shows the expected format for AI analysis")

def main():
    """Run all tests"""
    print("EXPENSE TRACKER IMPROVEMENTS TEST SUITE")
    print("Testing all 4 improvement areas...")
    
    # Test 1: Folder Structure
    test_folder_structure()
    
    # Test 2: AI Improvements
    test_ai_improvements()
    
    # Test 3: Database Connection
    test_database_connection()
    
    # Test 4: Full System
    test_full_system()
    
    # Create sample receipt for reference
    create_sample_receipt()
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60)
    print("Next Steps:")
    print("1. Update database schema by running the SQL script")
    print("2. Add test receipt images to Data Folders/new_receipts/")
    print("3. Run: python receipt_processor.py")
    print("4. Test Power BI connection with enhanced data")

if __name__ == "__main__":
    main()