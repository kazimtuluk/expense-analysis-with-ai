"""
Table Preview System for Receipt Analysis Results
Shows AI analysis in user-friendly table format and gets approval
"""
import os
from typing import Dict, List, Optional
from tabulate import tabulate

class ReceiptTablePreview:
    """Display receipt analysis results in table format for user review"""
    
    def __init__(self):
        self.current_receipt = None
        self.approved_receipts = []
    
    def display_receipt_analysis(self, analysis_result: Dict) -> bool:
        """Display receipt analysis in table format and get user approval"""
        
        if analysis_result['ai_analysis']['status'] != 'success':
            print("Cannot display preview - AI analysis failed")
            return False
        
        self.current_receipt = analysis_result
        data = analysis_result['ai_analysis']['data']
        
        # Clear screen for better display
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print("RECEIPT ANALYSIS PREVIEW")
        print("=" * 80)
        
        # Display file info
        print(f"File: {analysis_result['filename']}")
        print(f"Status: {analysis_result['ai_analysis']['status'].title()}")
        print(f"Confidence: {analysis_result['confidence'].title()}")
        print()
        
        # Display merchant information
        self.display_merchant_info(data['merchant'])
        print()
        
        # Display transaction summary
        self.display_transaction_summary(data['transaction'])
        print()
        
        # Display items table
        self.display_items_table(data['items'])
        print()
        
        # Get user decision
        return self.get_user_approval()
    
    def display_merchant_info(self, merchant_data: Dict):
        """Display merchant information"""
        print("MERCHANT INFORMATION")
        print("-" * 40)
        
        merchant_table = [
            ["Name", merchant_data.get('name', 'Unknown')],
            ["Address", merchant_data.get('address', 'Not available')],
            ["Phone", merchant_data.get('phone', 'Not available')]
        ]
        
        print(tabulate(merchant_table, headers=["Field", "Value"], tablefmt="grid"))
    
    def display_transaction_summary(self, transaction_data: Dict):
        """Display transaction summary"""
        print("TRANSACTION SUMMARY")
        print("-" * 40)
        
        transaction_table = [
            ["Date", transaction_data.get('date', 'Not found')],
            ["Time", transaction_data.get('time', 'Not found')],
            ["Subtotal", f"${transaction_data.get('subtotal', 0.0):.2f}"],
            ["Tax", f"${transaction_data.get('tax_amount', 0.0):.2f}"],
            ["Total Amount", f"${transaction_data.get('total_amount', 0.0):.2f}"],
            ["Payment Method", transaction_data.get('payment_method', 'Not specified')]
        ]
        
        print(tabulate(transaction_table, headers=["Field", "Value"], tablefmt="grid"))
    
    def display_items_table(self, items_data: List[Dict]):
        """Display items in a formatted table"""
        print("ITEMIZED PURCHASES")
        print("-" * 40)
        
        if not items_data:
            print("No items found in analysis")
            return
        
        # Prepare items table
        items_table = []
        total_calculated = 0.0
        
        for i, item in enumerate(items_data, 1):
            name = item.get('name', 'Unknown Item')
            price = item.get('price', 0.0)
            quantity = item.get('quantity', 1)
            category = item.get('category', 'Other')
            
            line_total = price * quantity
            total_calculated += line_total
            
            items_table.append([
                i,
                name[:40] + "..." if len(name) > 40 else name,
                f"{quantity:.1f}",
                f"${price:.2f}",
                f"${line_total:.2f}",
                category
            ])
        
        headers = ["#", "Product Name", "Qty", "Price", "Total", "Category"]
        print(tabulate(items_table, headers=headers, tablefmt="grid"))
        
        # Display summary
        print()
        print(f"Items Count: {len(items_data)}")
        print(f"Calculated Total: ${total_calculated:.2f}")
    
    def get_user_approval(self) -> bool:
        """Get user approval for the analysis"""
        print()
        print("=" * 80)
        print("REVIEW OPTIONS")
        print("=" * 80)
        
        while True:
            print("\nWhat would you like to do?")
            print("  [A]pprove - Save this analysis to database")
            print("  [E]dit - Modify the analysis (coming soon)")
            print("  [R]eject - Skip saving this receipt")
            print("  [V]iew Raw Text - See original OCR text")
            print("  [Q]uit - Exit without saving")
            
            choice = input("\nEnter your choice (A/E/R/V/Q): ").strip().upper()
            
            if choice == 'A':
                print("\n✅ Analysis approved! Ready to save to database.")
                return True
            
            elif choice == 'E':
                print("\n⚠️ Edit functionality coming in next version.")
                print("For now, you can approve or reject the analysis.")
                continue
            
            elif choice == 'R':
                print("\n❌ Analysis rejected. Receipt will not be saved.")
                return False
            
            elif choice == 'V':
                self.display_raw_text()
                input("\nPress Enter to continue...")
                continue
            
            elif choice == 'Q':
                print("\n🚪 Exiting without saving.")
                return False
            
            else:
                print(f"\n❌ Invalid choice: '{choice}'. Please try again.")
    
    def display_raw_text(self):
        """Display the raw OCR text for review"""
        if not self.current_receipt:
            print("No receipt data available")
            return
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 80)
        print("RAW OCR TEXT")
        print("=" * 80)
        print()
        print(self.current_receipt.get('text', 'No text available'))
        print()
        print("=" * 80)
    
    def process_multiple_receipts(self, analysis_results: List[Dict]) -> List[Dict]:
        """Process multiple receipt analyses with user review"""
        approved_receipts = []
        
        print(f"\n🔍 Found {len(analysis_results)} receipt(s) to review")
        
        for i, result in enumerate(analysis_results, 1):
            print(f"\n📄 Reviewing receipt {i} of {len(analysis_results)}")
            
            if self.display_receipt_analysis(result):
                approved_receipts.append(result)
                print(f"✅ Receipt {i} approved")
            else:
                print(f"❌ Receipt {i} rejected")
            
            # Ask if user wants to continue if there are more receipts
            if i < len(analysis_results):
                continue_choice = input(f"\nContinue to next receipt? (Y/n): ").strip().upper()
                if continue_choice == 'N':
                    print(f"⏹️ Stopped processing. Remaining {len(analysis_results) - i} receipts skipped.")
                    break
        
        return approved_receipts
    
    def display_final_summary(self, approved_receipts: List[Dict]):
        """Display final summary of approved receipts"""
        if not approved_receipts:
            print("\n📋 No receipts approved for database save.")
            return
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 80)
        print("FINAL APPROVAL SUMMARY")
        print("=" * 80)
        
        summary_table = []
        total_amount = 0.0
        total_items = 0
        
        for receipt in approved_receipts:
            data = receipt['ai_analysis']['data']
            merchant = data['merchant']['name']
            amount = data['transaction']['total_amount']
            items_count = len(data['items'])
            
            summary_table.append([
                receipt['filename'],
                merchant,
                f"${amount:.2f}",
                f"{items_count} items"
            ])
            
            total_amount += amount
            total_items += items_count
        
        headers = ["Receipt File", "Merchant", "Amount", "Items"]
        print(tabulate(summary_table, headers=headers, tablefmt="grid"))
        
        print(f"\n📊 Summary: {len(approved_receipts)} receipts approved")
        print(f"💰 Total Amount: ${total_amount:.2f}")
        print(f"📦 Total Items: {total_items}")
        print("\n🎯 Ready to save to database!")


def test_table_preview():
    """Test function for table preview system"""
    # Sample analysis result for testing
    sample_analysis = {
        'filename': 'test_receipt.png',
        'ai_analysis': {
            'status': 'success',
            'confidence': 'high',
            'data': {
                'merchant': {
                    'name': 'TARGET',
                    'address': 'Greenwood City, CA, 34343-343343',
                    'phone': '888-888-8888'
                },
                'transaction': {
                    'date': '2021-08-19',
                    'time': '17:32:29',
                    'subtotal': 535.85,
                    'tax_amount': 49.59,
                    'total_amount': 585.74,
                    'payment_method': 'VISA'
                },
                'items': [
                    {'name': '42 Inch LED TV', 'price': 533.89, 'quantity': 1, 'category': 'Electronics'},
                    {'name': 'Bluetooth Headphones', 'price': 29.99, 'quantity': 1, 'category': 'Electronics'},
                    {'name': 'Dave Shampoo', 'price': 12.98, 'quantity': 1, 'category': 'Personal Care'},
                    {'name': 'Dave Conditioner', 'price': 8.99, 'quantity': 1, 'category': 'Personal Care'}
                ]
            }
        },
        'text': 'TARGET\nGreenwood City - 888 -888-8888\n42 Inch LED TV $533.89\nBluetooth $29.99\nTOTAL $585.74',
        'confidence': 'high'
    }
    
    preview = ReceiptTablePreview()
    approved = preview.display_receipt_analysis(sample_analysis)
    
    if approved:
        print("\n✅ Test receipt approved!")
    else:
        print("\n❌ Test receipt rejected!")


if __name__ == "__main__":
    test_table_preview()