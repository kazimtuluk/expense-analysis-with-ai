"""
Complete Receipt Processor with Full AI Integration
Processes receipts: OCR → Full AI Analysis → Structured Data
Updated with new folder structure and file management
"""
import os
import sys
import glob
import shutil
from datetime import datetime
from google.cloud import storage, vision
from dotenv import load_dotenv
import json

# Ensure we can import ai_integration from same directory
sys.path.append(os.path.dirname(__file__))
from ai_integration import FullAIReceiptAnalyzer
from table_preview import ReceiptTablePreview
from database_saver import ReceiptDatabaseSaver

# Load environment variables
load_dotenv("Environment Configuration/.env")

class CompleteReceiptProcessor:
    """Complete receipt processing with Full AI integration and improved file management"""
    
    def __init__(self):
        self.storage_client = storage.Client()
        self.vision_client = vision.ImageAnnotatorClient()
        self.bucket_name = os.getenv('STORAGE_BUCKET_NAME')
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        # Updated folder structure
        self.new_receipts_folder = "Data Folders/new_receipts"
        self.processed_receipts_folder = "Data Folders/processed_receipts"
        
        # Create folders if they don't exist
        self.setup_folders()
        
        # Initialize Full AI analyzer, Table Preview, and Database Saver
        try:
            self.ai_analyzer = FullAIReceiptAnalyzer()
            self.table_preview = ReceiptTablePreview()
            self.database_saver = ReceiptDatabaseSaver()
            self.ai_available = True
            print("All system components initialized successfully")
        except Exception as e:
            print(f"Warning: System components not available: {e}")
            self.ai_available = False
        
    def setup_folders(self):
        """Create necessary folders for receipt processing"""
        folders_to_create = [
            self.new_receipts_folder,
            self.processed_receipts_folder,
            f"{self.processed_receipts_folder}/approved",
            f"{self.processed_receipts_folder}/rejected",
            f"{self.processed_receipts_folder}/failed"
        ]
        
        for folder in folders_to_create:
            if not os.path.exists(folder):
                print(f"Creating folder: {folder}")
                os.makedirs(folder, exist_ok=True)
    
    def find_all_receipts(self):
        """Find all receipts in new_receipts folder"""
        if not os.path.exists(self.new_receipts_folder):
            print(f"Creating folder: {self.new_receipts_folder}")
            os.makedirs(self.new_receipts_folder, exist_ok=True)
            return []
            
        # Find image files
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp']
        receipt_files = []
        
        for ext in image_extensions:
            receipt_files.extend(glob.glob(os.path.join(self.new_receipts_folder, ext)))
            receipt_files.extend(glob.glob(os.path.join(self.new_receipts_folder, ext.upper())))
        
        if len(receipt_files) == 0:
            print(f"No receipts found in {self.new_receipts_folder}")
            print("Please add receipt images to the new_receipts folder")
            return []
        else:
            print(f"Found {len(receipt_files)} receipt(s) in new_receipts folder:")
            for f in receipt_files:
                print(f"  - {os.path.basename(f)}")
            return receipt_files
    
    def move_processed_receipt(self, receipt_path: str, status: str):
        """Move processed receipt to appropriate subfolder"""
        filename = os.path.basename(receipt_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create timestamped filename to avoid conflicts
        name, ext = os.path.splitext(filename)
        new_filename = f"{timestamp}_{name}{ext}"
        
        # Determine destination folder based on status
        status_folders = {
            'approved': f"{self.processed_receipts_folder}/approved",
            'rejected': f"{self.processed_receipts_folder}/rejected", 
            'failed': f"{self.processed_receipts_folder}/failed"
        }
        
        destination_folder = status_folders.get(status, f"{self.processed_receipts_folder}/failed")
        destination_path = os.path.join(destination_folder, new_filename)
        
        try:
            shutil.move(receipt_path, destination_path)
            print(f"Moved {filename} to {status} folder as {new_filename}")
            return destination_path
        except Exception as e:
            print(f"Failed to move {filename}: {e}")
            return receipt_path
    
    def upload_to_cloud(self, local_path):
        """Upload receipt to Google Cloud Storage"""
        try:
            filename = os.path.basename(local_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            cloud_filename = f"receipts/{timestamp}_{filename}"
            
            blob = self.bucket.blob(cloud_filename)
            blob.upload_from_filename(local_path)
            
            print(f"Uploaded to cloud: {cloud_filename}")
            return cloud_filename
            
        except Exception as e:
            print(f"Upload failed: {e}")
            return None
    
    def extract_text_with_ocr(self, image_path):
        """Extract text using Google Vision API"""
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations
            
            if response.error.message:
                raise Exception(f'Vision API error: {response.error.message}')
            
            if texts:
                full_text = texts[0].description
                return full_text
            else:
                return ""
                
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""
    
    def is_already_processed(self, filename):
        """Check if receipt was already uploaded to cloud storage"""
        try:
            # List blobs in receipts folder
            blobs = list(self.bucket.list_blobs(prefix="receipts/"))
            
            for blob in blobs:
                # Extract original filename from cloud filename
                # Format: receipts/20231222_143045_costco_receipt.jpg
                if blob.name.endswith(filename):
                    return True
            return False
            
        except Exception as e:
            print(f"Error checking if already processed: {e}")
            return False
    
    def process_all_receipts(self):
        """Process all receipts in the folder with user approval and file management"""
        print("=" * 60)
        print("RECEIPT PROCESSOR WITH IMPROVED FILE MANAGEMENT")
        print("=" * 60)
        
        # Find all receipts in new folder
        receipt_files = self.find_all_receipts()
        if not receipt_files:
            return []
        
        # Process receipts (OCR + AI analysis)
        analysis_results = []
        failed_receipts = []
        
        for receipt_path in receipt_files:
            filename = os.path.basename(receipt_path)
            print(f"\nProcessing: {filename}")
            
            # Check if already processed in cloud
            if self.is_already_processed(filename):
                print(f"Skipping {filename} - already processed in cloud")
                # Move to processed folder as already done
                self.move_processed_receipt(receipt_path, 'approved')
                continue
            
            # Process this receipt
            result = self.process_single_file(receipt_path)
            if result:
                if result['ai_analysis']['status'] == 'success':
                    analysis_results.append(result)
                else:
                    failed_receipts.append(receipt_path)
            else:
                failed_receipts.append(receipt_path)
        
        # Move failed receipts
        for failed_path in failed_receipts:
            self.move_processed_receipt(failed_path, 'failed')
        
        if not analysis_results:
            print(f"\nNo new receipts to review. {len(failed_receipts)} receipts failed processing.")
            return []
        
        print(f"\n{len(analysis_results)} receipt(s) analyzed and ready for review")
        
        # Show table preview and get user approval
        if not self.ai_available:
            print("Table preview not available - AI system not initialized")
            # Move remaining receipts to failed
            for result in analysis_results:
                self.move_processed_receipt(result['local_path'], 'failed')
            return analysis_results
        
        approved_receipts = self.table_preview.process_multiple_receipts(analysis_results)
        rejected_receipts = [r for r in analysis_results if r not in approved_receipts]
        
        # Move rejected receipts
        for rejected in rejected_receipts:
            self.move_processed_receipt(rejected['local_path'], 'rejected')
        
        if approved_receipts:
            self.table_preview.display_final_summary(approved_receipts)
            
            # Ask for final confirmation before database save
            final_confirm = input(f"\nSave {len(approved_receipts)} approved receipt(s) to database? (Y/n): ").strip().upper()
            if final_confirm != 'N':
                print(f"\nSaving {len(approved_receipts)} receipt(s) to database...")
                
                # Save to database
                save_results = self.database_saver.save_approved_receipts(approved_receipts)
                
                # Move approved receipts after successful database save
                for approved in approved_receipts:
                    self.move_processed_receipt(approved['local_path'], 'approved')
                
                # Display results
                self.database_saver.display_save_results(save_results)
                
                return approved_receipts
            else:
                print("Database save cancelled by user")
                # Move to rejected since user cancelled
                for cancelled in approved_receipts:
                    self.move_processed_receipt(cancelled['local_path'], 'rejected')
                return []
        else:
            print("No receipts approved for database save")
            return []
    
    def process_single_file(self, receipt_path):
        """Process a single receipt file with Full AI analysis"""
        filename = os.path.basename(receipt_path)
        
        print(f"Step 1: Uploading {filename} to cloud...")
        # Upload to cloud
        cloud_path = self.upload_to_cloud(receipt_path)
        if not cloud_path:
            print(f"Failed to upload {filename}")
            return None
        
        print("Step 2: Extracting text with OCR...")
        # Extract text with OCR
        receipt_text = self.extract_text_with_ocr(receipt_path)
        if not receipt_text:
            print(f"OCR failed for {filename}")
            return None
        
        print(f"OCR extracted {len(receipt_text)} characters")
        
        print("Step 3: Full AI analysis...")
        # Full AI analysis
        analysis_result = {'status': 'failed', 'confidence': 'failed', 'data': None}
        
        if self.ai_available:
            try:
                analysis_result = self.ai_analyzer.analyze_complete_receipt(receipt_text)
                
                if analysis_result['status'] == 'success':
                    data = analysis_result['data']
                    print(f"AI Analysis successful!")
                    print(f"  Merchant: {data['merchant']['name']}")
                    print(f"  Total: ${data['transaction']['total_amount']}")
                    print(f"  Items found: {len(data['items'])}")
                    print(f"  Confidence: {analysis_result['confidence']}")
                else:
                    print(f"AI Analysis failed: {analysis_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"AI analysis error: {e}")
                analysis_result['error'] = str(e)
        else:
            print("AI analyzer not available")
        
        # Combine all data
        result = {
            'local_path': receipt_path,
            'cloud_path': cloud_path,
            'filename': filename,
            'text': receipt_text,
            'ai_analysis': analysis_result,
            'status': 'analysis_completed'
        }
        
        if analysis_result['status'] == 'success':
            # Extract key info for easy access
            data = analysis_result['data']
            result['merchant_name'] = data['merchant']['name']
            result['total_amount'] = data['transaction']['total_amount']
            result['items_count'] = len(data['items'])
            result['confidence'] = analysis_result['confidence']
            
            print(f"Successfully processed {filename}")
            print(f"Final result: {data['merchant']['name']}, ${data['transaction']['total_amount']}, {len(data['items'])} items")
        else:
            result['merchant_name'] = 'Unknown'
            result['total_amount'] = 0.0
            result['items_count'] = 0
            result['confidence'] = 'failed'
            print(f"Processing completed with errors for {filename}")
        
        return result
    
    def clean_old_folders(self):
        """Clean up old sample_receipts folder if it exists"""
        old_folder = "Data Folders/sample_receipts"
        if os.path.exists(old_folder):
            print(f"\nFound old sample_receipts folder")
            
            # Check if there are files in old folder
            old_files = glob.glob(os.path.join(old_folder, "*.*"))
            if old_files:
                print(f"Moving {len(old_files)} files from sample_receipts to new_receipts...")
                for old_file in old_files:
                    filename = os.path.basename(old_file)
                    new_path = os.path.join(self.new_receipts_folder, filename)
                    
                    # Avoid overwriting existing files
                    if os.path.exists(new_path):
                        name, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(new_path):
                            new_filename = f"{name}_{counter}{ext}"
                            new_path = os.path.join(self.new_receipts_folder, new_filename)
                            counter += 1
                    
                    shutil.move(old_file, new_path)
                    print(f"  Moved: {filename} -> new_receipts/")
                
                # Remove empty old folder
                try:
                    os.rmdir(old_folder)
                    print(f"Removed empty folder: {old_folder}")
                except:
                    print(f"Could not remove folder: {old_folder} (may not be empty)")
            else:
                print("Old folder is empty")

if __name__ == "__main__":
    processor = CompleteReceiptProcessor()
    
    # Clean up old folders first
    processor.clean_old_folders()
    
    # Process receipts
    results = processor.process_all_receipts()