"""
Improved Full AI Receipt Analysis Module
Enhanced with better merchant location parsing and product name standardization
"""
import google.generativeai as genai
import json
import re
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv("Environment Configuration/.env")

class FullAIReceiptAnalyzer:
    """Complete AI-powered receipt analysis using Gemini with improved merchant and product parsing"""
    
    def __init__(self):
        # Configure Gemini AI
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def analyze_complete_receipt(self, receipt_text: str) -> Dict:
        """Complete receipt analysis using AI with enhanced parsing"""
        
        prompt = f"""
Analyze this receipt text and extract ALL information in JSON format with improved accuracy, especially DATES and TIMES.

Receipt text:
{receipt_text}

Extract and return ONLY a JSON object with this exact structure:
{{
    "merchant": {{
        "name": "Store Name (clean, proper case)",
        "address": "Full address if available",
        "city": "City name if found",
        "state": "State/Province code (US: CA, TX, NY, etc. | Canada: ON, BC, QC, etc.) if found", 
        "zip_code": "Zip/Postal code if found",
        "phone": "Phone number if available"
    }},
    "transaction": {{
        "date": "YYYY-MM-DD format if found (CRITICAL: Look for patterns like MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, Month DD YYYY)",
        "time": "HH:MM:SS format if found (Look for patterns like HH:MM:SS, HH:MM AM/PM)",
        "subtotal": 0.00,
        "tax_amount": 0.00,
        "total_amount": 0.00,
        "payment_method": "cash/debit/credit if found"
    }},
    "items": [
        {{
            "receipt_name": "Exact name as written on receipt",
            "standard_name": "Simplified, standardized product name",
            "price": 0.00,
            "quantity": 1,
            "category": "Auto-assigned category"
        }}
    ]
}}

CRITICAL DATE/TIME EXTRACTION RULES:

1. DATE PATTERNS - Look for these formats:
   - MM/DD/YYYY (08/19/2024)
   - MM/DD/YY (08/19/24)
   - DD/MM/YYYY (19/08/2024)
   - YYYY-MM-DD (2024-08-19)
   - Month DD, YYYY (August 19, 2024)
   - DD-MM-YYYY or DD.MM.YYYY
   - Look near: "Date:", "Receipt Date:", timestamp lines

2. TIME PATTERNS - Look for these formats:
   - HH:MM:SS (17:32:29)
   - HH:MM (17:32)
   - HH:MM AM/PM (5:32 PM)
   - Look near: "Time:", timestamps, after dates

3. MERCHANT INFORMATION:
   - Extract business name without extra words like "STORE #123"
   - Look for city names in address lines
   - Identify state/province codes:
     * US States: CA, TX, NY, FL, etc. (2 letters)
     * Canadian Provinces: ON, BC, QC, AB, etc. (2 letters)
   - Find ZIP codes (US: 5 digit or 5+4) or Postal codes (Canada: A1A 1A1 format)
   - Clean phone numbers to standard format

4. LOCATION PARSING PATTERNS:
   - US: "City, State ZIP" (San Francisco, CA 94102)
   - Canada: "City, Province Postal" (Toronto, ON M6J 1X5)
   - Look for province names: Ontario→ON, Quebec→QC, British Columbia→BC

5. PRODUCT NAMES:
   - receipt_name: Keep the exact text from receipt
   - standard_name: Create a clean, simple product name
   - Examples:
     * "7053275 BIG 42 Inch LED TV N" → receipt_name: "BIG 42 Inch LED TV", standard_name: "LED TV"
     * "Dave Shampoo 16oz" → receipt_name: "Dave Shampoo 16oz", standard_name: "Shampoo"

6. CATEGORIES:
   Choose from: Electronics, Groceries, Clothing, Home & Garden, Personal Care, 
   Dining, Transportation, Entertainment, Health & Beauty, Office Supplies, Other

7. DATA CLEANING:
   - All text should be in proper case (first letter capital, rest lowercase)
   - Remove item codes, SKUs, and unnecessary characters
   - Ensure all amounts are numbers (0.00 format)
   - Use "Unknown" for missing critical information
   - For dates: MUST return in YYYY-MM-DD format
   - For times: MUST return in HH:MM:SS format
"""

        try:
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            json_text = self.extract_json_from_response(response.text)
            ai_data = json.loads(json_text)
            
            # Validate and clean the response
            validated_data = self.validate_and_clean_response(ai_data)
            
            return {
                'status': 'success',
                'confidence': self.calculate_confidence(validated_data),
                'data': validated_data
            }
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return {
                'status': 'error',
                'confidence': 'failed',
                'data': self.create_fallback_response(receipt_text),
                'error': str(e)
            }
    
    def extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from AI response text"""
        # Look for JSON block between curly braces
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        else:
            raise ValueError("No valid JSON found in AI response")
    
    def validate_and_clean_response(self, ai_data: Dict) -> Dict:
        """Validate and clean AI response structure with improved merchant parsing"""
        cleaned = {
            "merchant": {
                "name": "Unknown",
                "address": "",
                "city": "",
                "state": "",
                "zip_code": "",
                "phone": ""
            },
            "transaction": {
                "date": None,
                "time": None,
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "total_amount": 0.0,
                "payment_method": ""
            },
            "items": []
        }
        
        if not isinstance(ai_data, dict):
            return cleaned
        
        # Extract and clean merchant info
        if "merchant" in ai_data and isinstance(ai_data["merchant"], dict):
            merchant = ai_data["merchant"]
            cleaned["merchant"]["name"] = self.clean_text(merchant.get("name", "Unknown"))
            cleaned["merchant"]["address"] = self.clean_text(merchant.get("address", ""))
            cleaned["merchant"]["city"] = self.clean_text(merchant.get("city", ""))
            cleaned["merchant"]["state"] = self.clean_state(merchant.get("state", ""))
            cleaned["merchant"]["zip_code"] = self.clean_zip_code(merchant.get("zip_code", ""))
            cleaned["merchant"]["phone"] = self.clean_phone(merchant.get("phone", ""))
            
            # If city/state/zip not found, try to parse from address
            if cleaned["merchant"]["address"] and not all([
                cleaned["merchant"]["city"],
                cleaned["merchant"]["state"],
                cleaned["merchant"]["zip_code"]
            ]):
                parsed_location = self.parse_location_from_address(cleaned["merchant"]["address"])
                if parsed_location["city"] and not cleaned["merchant"]["city"]:
                    cleaned["merchant"]["city"] = parsed_location["city"]
                if parsed_location["state"] and not cleaned["merchant"]["state"]:
                    cleaned["merchant"]["state"] = parsed_location["state"]
                if parsed_location["zip_code"] and not cleaned["merchant"]["zip_code"]:
                    cleaned["merchant"]["zip_code"] = parsed_location["zip_code"]
        
        # Extract transaction info
        if "transaction" in ai_data and isinstance(ai_data["transaction"], dict):
            transaction = ai_data["transaction"]
            cleaned["transaction"]["date"] = self.parse_date(transaction.get("date"))
            cleaned["transaction"]["time"] = self.parse_time(transaction.get("time"))
            cleaned["transaction"]["subtotal"] = self.parse_amount(transaction.get("subtotal"))
            cleaned["transaction"]["tax_amount"] = self.parse_amount(transaction.get("tax_amount"))
            cleaned["transaction"]["total_amount"] = self.parse_amount(transaction.get("total_amount"))
            cleaned["transaction"]["payment_method"] = self.clean_text(transaction.get("payment_method", ""))
        
        # Extract and validate items with improved naming
        if "items" in ai_data and isinstance(ai_data["items"], list):
            for item in ai_data["items"]:
                if isinstance(item, dict):
                    clean_item = self.validate_improved_item(item)
                    if clean_item:
                        cleaned["items"].append(clean_item)
        
        # Validate totals
        cleaned = self.validate_totals(cleaned)
        
        return cleaned
    
    def validate_improved_item(self, item: Dict) -> Optional[Dict]:
        """Validate and clean individual item with dual naming"""
        receipt_name = self.clean_text(item.get("receipt_name", ""))
        standard_name = self.clean_text(item.get("standard_name", ""))
        
        # Fallback: if only one name provided, use it for both
        if not receipt_name and not standard_name:
            name = self.clean_text(item.get("name", ""))
            if name:
                receipt_name = name
                standard_name = self.standardize_product_name(name)
        elif receipt_name and not standard_name:
            standard_name = self.standardize_product_name(receipt_name)
        elif not receipt_name and standard_name:
            receipt_name = standard_name
        
        price = self.parse_amount(item.get("price"))
        quantity = self.parse_quantity(item.get("quantity", 1))
        category = self.clean_text(item.get("category", "Other"))
        
        # Must have names and valid price
        if not receipt_name or not standard_name or price <= 0:
            return None
        
        # Validate category
        valid_categories = [
            "Electronics", "Groceries", "Clothing", "Home & Garden", 
            "Personal Care", "Dining", "Transportation", "Entertainment",
            "Health & Beauty", "Office Supplies", "Other"
        ]
        if category not in valid_categories:
            category = "Other"
        
        return {
            "receipt_name": receipt_name,
            "standard_name": standard_name,
            "price": price,
            "quantity": quantity,
            "category": category
        }
    
    def clean_text(self, text: str) -> str:
        """Clean text to proper case format"""
        if not text or str(text).strip().lower() in ['', 'unknown', 'none', 'null']:
            return ""
        
        text = str(text).strip()
        
        # Handle special cases for business names
        if text.upper() in ['TARGET', 'WALMART', 'COSTCO', 'BESTBUY', 'BEST BUY']:
            return text.title()
        
        # Regular proper case
        return text.title()
    
    def clean_state(self, state: str) -> str:
        """Clean and validate state/province abbreviation for US and Canada"""
        if not state:
            return ""
        
        state = str(state).strip().upper()
        
        # Valid US state abbreviations
        us_states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        ]
        
        # Valid Canadian province/territory abbreviations
        canadian_provinces = [
            'AB', 'BC', 'MB', 'NB', 'NL', 'NT', 'NS', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'
        ]
        
        valid_states = us_states + canadian_provinces
        
        if state in valid_states:
            return state
        
        # Try to extract state from longer string
        for valid_state in valid_states:
            if valid_state in state:
                return valid_state
        
        # Special handling for common variations
        state_variations = {
            'ONTARIO': 'ON',
            'ONT': 'ON',
            'QUEBEC': 'QC',
            'BRITISH COLUMBIA': 'BC',
            'ALBERTA': 'AB',
            'MANITOBA': 'MB',
            'SASKATCHEWAN': 'SK',
            'NOVA SCOTIA': 'NS',
            'NEW BRUNSWICK': 'NB',
            'NEWFOUNDLAND': 'NL',
            'PRINCE EDWARD ISLAND': 'PE'
        }
        
        for full_name, abbrev in state_variations.items():
            if full_name in state:
                return abbrev
        
        return ""
    
    def clean_zip_code(self, zip_code: str) -> str:
        """Clean and validate ZIP code"""
        if not zip_code:
            return ""
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(zip_code))
        
        if len(digits) == 5:
            return digits
        elif len(digits) == 9:
            return f"{digits[:5]}-{digits[5:]}"
        
        return ""
    
    def clean_phone(self, phone: str) -> str:
        """Clean and format phone number"""
        if not phone:
            return ""
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(phone))
        
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        
        return phone.strip()
    
    def parse_location_from_address(self, address: str) -> Dict:
        """Parse city, state, ZIP from address string"""
        result = {"city": "", "state": "", "zip_code": ""}
        
        if not address:
            return result
        
        # Pattern 1: City, State ZIP
        pattern1 = r'([^,]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)'
        match1 = re.search(pattern1, address)
        if match1:
            result["city"] = self.clean_text(match1.group(1))
            result["state"] = match1.group(2)
            result["zip_code"] = match1.group(3)
            return result
        
        # Pattern 2: City State ZIP (no comma)
        pattern2 = r'([^0-9]+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)'
        match2 = re.search(pattern2, address)
        if match2:
            result["city"] = self.clean_text(match2.group(1).strip())
            result["state"] = match2.group(2)
            result["zip_code"] = match2.group(3)
            return result
        
        # Try to find just ZIP code
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        if zip_match:
            result["zip_code"] = zip_match.group(1)
        
        # Try to find state abbreviation
        state_match = re.search(r'\b([A-Z]{2})\b', address)
        if state_match and self.clean_state(state_match.group(1)):
            result["state"] = state_match.group(1)
        
        return result
    
    def standardize_product_name(self, receipt_name: str) -> str:
        """Convert receipt product name to standardized name"""
        if not receipt_name:
            return ""
        
        name = receipt_name.lower().strip()
        
        # Electronics
        if any(word in name for word in ['tv', 'television', 'led', 'lcd', 'smart tv']):
            return "Television"
        if any(word in name for word in ['laptop', 'notebook', 'macbook']):
            return "Laptop"
        if any(word in name for word in ['phone', 'iphone', 'android', 'smartphone']):
            return "Phone"
        if any(word in name for word in ['tablet', 'ipad']):
            return "Tablet"
        if any(word in name for word in ['headphone', 'earphone', 'bluetooth', 'airpods']):
            return "Headphones"
        if any(word in name for word in ['speaker', 'soundbar']):
            return "Speaker"
        if any(word in name for word in ['cable', 'charger', 'adapter']):
            return "Cable"
        
        # Personal Care
        if any(word in name for word in ['shampoo']):
            return "Shampoo"
        if any(word in name for word in ['conditioner']):
            return "Conditioner"
        if any(word in name for word in ['soap', 'body wash']):
            return "Soap"
        if any(word in name for word in ['toothpaste']):
            return "Toothpaste"
        if any(word in name for word in ['deodorant']):
            return "Deodorant"
        
        # Groceries
        if any(word in name for word in ['milk']):
            return "Milk"
        if any(word in name for word in ['bread']):
            return "Bread"
        if any(word in name for word in ['eggs']):
            return "Eggs"
        if any(word in name for word in ['cheese']):
            return "Cheese"
        if any(word in name for word in ['chicken', 'beef', 'pork', 'meat']):
            return "Meat"
        if any(word in name for word in ['apple', 'banana', 'orange', 'fruit']):
            return "Fruit"
        if any(word in name for word in ['vegetable', 'carrot', 'potato', 'onion']):
            return "Vegetable"
        
        # Clothing
        if any(word in name for word in ['shirt', 't-shirt', 'tshirt']):
            return "Shirt"
        if any(word in name for word in ['pants', 'jeans', 'trousers']):
            return "Pants"
        if any(word in name for word in ['dress']):
            return "Dress"
        if any(word in name for word in ['shoes', 'sneakers', 'boots']):
            return "Shoes"
        
        # Home & Garden
        if any(word in name for word in ['detergent', 'laundry']):
            return "Detergent"
        if any(word in name for word in ['towel']):
            return "Towel"
        if any(word in name for word in ['pillow']):
            return "Pillow"
        if any(word in name for word in ['plant', 'flower']):
            return "Plant"
        
        # If no match found, try to extract the main word
        words = receipt_name.split()
        if words:
            # Return the longest word as it's likely the main product
            main_word = max(words, key=len)
            return self.clean_text(main_word)
        
        return self.clean_text(receipt_name)
    
    def parse_amount(self, value) -> float:
        """Parse amount from various formats"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Extract number from string
            match = re.search(r'(\d+\.?\d*)', value.replace(',', ''))
            if match:
                return float(match.group(1))
        return 0.0
    
    def parse_quantity(self, value) -> float:
        """Parse quantity from various formats"""
        try:
            return float(value) if float(value) > 0 else 1.0
        except:
            return 1.0
    
    def parse_date(self, date_str) -> Optional[str]:
        """Parse date string to database format with enhanced patterns"""
        if not date_str or str(date_str).strip().lower() in ['', 'unknown', 'none', 'null']:
            return None
        
        date_str = str(date_str).strip()
        
        try:
            from datetime import datetime
            import re
            
            # Remove common prefixes and clean the string
            date_str = re.sub(r'^(date:?|receipt date:?)\s*', '', date_str, flags=re.IGNORECASE)
            date_str = re.sub(r'\s+', ' ', date_str).strip()
            
            # Pattern 1: MM/DD/YYYY or MM/DD/YY
            date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', date_str)
            if date_match:
                month, day, year = date_match.groups()
                year = int(year)
                if year < 100:  # Convert 2-digit year
                    year = 2000 + year if year < 50 else 1900 + year
                try:
                    parsed_date = datetime(year, int(month), int(day))
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            # Pattern 2: YYYY-MM-DD
            iso_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
            if iso_match:
                year, month, day = iso_match.groups()
                try:
                    parsed_date = datetime(int(year), int(month), int(day))
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            # Pattern 3: DD/MM/YYYY (European format)
            euro_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
            if euro_match:
                day, month, year = euro_match.groups()
                try:
                    parsed_date = datetime(int(year), int(month), int(day))
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    # Try as MM/DD/YYYY if DD/MM fails
                    try:
                        parsed_date = datetime(int(year), int(day), int(month))
                        return parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        pass
            
            # Pattern 4: Month DD, YYYY (e.g., "January 15, 2024")
            month_name_match = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', date_str)
            if month_name_match:
                month_name, day, year = month_name_match.groups()
                try:
                    parsed_date = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y")
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    try:
                        parsed_date = datetime.strptime(f"{month_name} {day} {year}", "%b %d %Y")
                        return parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        pass
            
            # Pattern 5: DD-MM-YYYY or DD.MM.YYYY
            alt_sep_match = re.search(r'(\d{1,2})[-.](\d{1,2})[-.](\d{4})', date_str)
            if alt_sep_match:
                day, month, year = alt_sep_match.groups()
                try:
                    parsed_date = datetime(int(year), int(month), int(day))
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            # Pattern 6: Extract from timestamp format (YYYYMMDD from filename-like strings)
            timestamp_match = re.search(r'(\d{8})', date_str)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                try:
                    parsed_date = datetime.strptime(timestamp, '%Y%m%d')
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
                    
        except Exception as e:
            print(f"Date parsing error for '{date_str}': {e}")
        
        return None
    
    def parse_time(self, time_str) -> Optional[str]:
        """Parse time string to database format with enhanced patterns"""
        if not time_str or str(time_str).strip().lower() in ['', 'unknown', 'none', 'null']:
            return None
        
        time_str = str(time_str).strip()
        
        try:
            from datetime import datetime
            import re
            
            # Remove common prefixes
            time_str = re.sub(r'^(time:?|receipt time:?)\s*', '', time_str, flags=re.IGNORECASE)
            
            # Pattern 1: HH:MM:SS
            time_match = re.search(r'(\d{1,2}):(\d{2}):(\d{2})', time_str)
            if time_match:
                hour, minute, second = time_match.groups()
                try:
                    parsed_time = datetime.strptime(f"{hour}:{minute}:{second}", '%H:%M:%S')
                    return parsed_time.strftime('%H:%M:%S')
                except ValueError:
                    pass
            
            # Pattern 2: HH:MM (add :00 for seconds)
            time_match_short = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if time_match_short:
                hour, minute = time_match_short.groups()
                try:
                    parsed_time = datetime.strptime(f"{hour}:{minute}:00", '%H:%M:%S')
                    return parsed_time.strftime('%H:%M:%S')
                except ValueError:
                    pass
            
            # Pattern 3: HH:MM AM/PM
            ampm_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.IGNORECASE)
            if ampm_match:
                hour, minute, period = ampm_match.groups()
                try:
                    parsed_time = datetime.strptime(f"{hour}:{minute} {period.upper()}", '%I:%M %p')
                    return parsed_time.strftime('%H:%M:%S')
                except ValueError:
                    pass
                    
        except Exception as e:
            print(f"Time parsing error for '{time_str}': {e}")
        
        return None
    
    def validate_totals(self, data: Dict) -> Dict:
        """Validate that totals match item sum"""
        if not data["items"]:
            return data
        
        # Calculate sum of items
        items_total = sum(item["price"] * item["quantity"] for item in data["items"])
        
        # If no total was found, set it to items total
        if data["transaction"]["total_amount"] == 0:
            data["transaction"]["total_amount"] = items_total
        
        # If no subtotal, calculate from total - tax
        if data["transaction"]["subtotal"] == 0:
            tax = data["transaction"]["tax_amount"]
            data["transaction"]["subtotal"] = data["transaction"]["total_amount"] - tax
        
        return data
    
    def calculate_confidence(self, data: Dict) -> str:
        """Calculate confidence level of extraction"""
        score = 0
        max_score = 7
        
        # Merchant found
        if data["merchant"]["name"] != "Unknown":
            score += 1
        
        # Location info found
        if data["merchant"]["city"] or data["merchant"]["state"]:
            score += 1
        
        # Total amount found
        if data["transaction"]["total_amount"] > 0:
            score += 1
        
        # Items found
        if len(data["items"]) > 0:
            score += 2
        
        # Date found
        if data["transaction"]["date"]:
            score += 1
        
        # Product names standardized
        if data["items"] and any(item.get("standard_name") for item in data["items"]):
            score += 1
        
        if score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"
    
    def create_fallback_response(self, receipt_text: str) -> Dict:
        """Create fallback response if AI fails"""
        return {
            "merchant": {
                "name": "Unknown",
                "address": "",
                "city": "",
                "state": "",
                "zip_code": "",
                "phone": ""
            },
            "transaction": {
                "date": None,
                "time": None,
                "subtotal": 0.0,
                "tax_amount": 0.0,
                "total_amount": 0.0,
                "payment_method": ""
            },
            "items": []
        }


def test_full_ai_analyzer():
    """Test function for improved AI analyzer"""
    # Sample receipt text for testing
    sample_text = """
    TARGET
    123 Main Street
    San Francisco, CA 94102
    (415) 555-0123
    08/19/2021 17:32:29 EXPIRES 11/17/2021
    
    ELECTRONICS
    7053275    BIG 42 Inch LED TV N     533.89
    DISCOUNT COUPON    N              -50.00
    5599903    Bluetooth Headphones   N   29.99
    HEALTH AND BEAUTY
    1542666    Dave Shampoo 16oz      N   12.98
    5044148    Dave Conditioner       N    8.99
                        SUBTOTAL       535.85
    T = CA TAX 9.7500% on 535.85        49.59
                           TOTAL       585.74
    *9999 VISA  CHARGE                585.74
    """
    
    try:
        analyzer = FullAIReceiptAnalyzer()
        result = analyzer.analyze_complete_receipt(sample_text)
        
        print("Improved AI Analysis Result:")
        print("Status:", result['status'])
        print("Confidence:", result['confidence'])
        
        if result['status'] == 'success':
            data = result['data']
            print(f"\nMerchant: {data['merchant']['name']}")
            print(f"Address: {data['merchant']['address']}")
            print(f"City: {data['merchant']['city']}")
            print(f"State: {data['merchant']['state']}")
            print(f"ZIP: {data['merchant']['zip_code']}")
            print(f"Phone: {data['merchant']['phone']}")
            print(f"Total: ${data['transaction']['total_amount']}")
            print(f"Tax: ${data['transaction']['tax_amount']}")
            print(f"Date: {data['transaction']['date']}")
            print(f"\nItems ({len(data['items'])}):")
            for item in data['items']:
                print(f"  Receipt: {item['receipt_name']}")
                print(f"  Standard: {item['standard_name']}")
                print(f"  Price: ${item['price']} [{item['category']}]")
                print()
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    test_full_ai_analyzer()