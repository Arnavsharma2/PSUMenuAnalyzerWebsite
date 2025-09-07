from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import os
import time
from urllib.parse import urljoin
import csv
import pandas as pd

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Nutritional Data Extractor Class ---
class NutritionalDataExtractor:
    def __init__(self, debug=False):
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_nutritional_data(self, url: str) -> Dict[str, float]:
        """Extract nutritional data from a PSU nutrition page"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            nutrition_data = {}
            
            # Check if nutrition data is not available
            if "nutrition information is not available" in soup.get_text().lower():
                if self.debug:
                    print(f"No nutrition data available for {url}")
                return {}
            
            # Look for nutrition facts table or similar structure
            nutrition_tables = soup.find_all('table', class_=re.compile(r'nutrition|facts', re.I))
            
            # Also look for any table that might contain nutritional data
            if not nutrition_tables:
                all_tables = soup.find_all('table')
                for table in all_tables:
                    table_text = table.get_text().lower()
                    if any(keyword in table_text for keyword in ['calories', 'protein', 'fat', 'sodium', 'fiber']):
                        nutrition_tables.append(table)
            
            for table in nutrition_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 1:
                        # Get all text from the row
                        row_text = row.get_text(strip=True).lower()
                        
                        # Extract nutritional data using patterns that match the PSU format
                        patterns = {
                            'calories': r'calories:\s*(\d+\.?\d*)',
                            'protein': r'protein\s*(\d+\.?\d*)\s*g',
                            'fat': r'total\s+fat\s*(\d+\.?\d*)\s*g',
                            'saturated_fat': r'sat\s+fat\s*(\d+\.?\d*)\s*g',
                            'carbs': r'total\s+carb\s*(\d+\.?\d*)\s*g',
                            'fiber': r'dietary\s+fiber\s*(\d+\.?\d*)\s*g',
                            'sugar': r'sugars\s*(\d+\.?\d*)\s*g',
                            'sodium': r'sodium\s*(\d+\.?\d*)\s*mg',
                            'cholesterol': r'cholesterol\s*(\d+\.?\d*)\s*mg'
                        }
                        
                        # Also try to extract from the specific PSU table structure
                        # Look for patterns like "Protein 10.1g" or "Total Fat 5.1g"
                        psu_patterns = {
                            'calories': r'calories:\s*(\d+\.?\d*)',
                            'protein': r'protein\s*(\d+\.?\d*)\s*g',
                            'fat': r'total\s+fat\s*(\d+\.?\d*)\s*g',
                            'saturated_fat': r'sat\s+fat\s*(\d+\.?\d*)\s*g',
                            'carbs': r'total\s+carb\s*(\d+\.?\d*)\s*g',
                            'fiber': r'dietary\s+fiber\s*(\d+\.?\d*)\s*g',
                            'sugar': r'sugars\s*(\d+\.?\d*)\s*g',
                            'sodium': r'sodium\s*(\d+\.?\d*)\s*mg',
                            'cholesterol': r'cholesterol\s*(\d+\.?\d*)\s*mg'
                        }
                        
                        for key, pattern in patterns.items():
                            match = re.search(pattern, row_text)
                            if match and key not in nutrition_data:  # Only set if not already found
                                nutrition_data[key] = float(match.group(1))
            
            # If no structured data found, try to extract from text with more patterns
            if not nutrition_data:
                page_text = soup.get_text().lower()
                
                # Look for common nutrition patterns in text with more flexible matching
                patterns = {
                    'calories': r'calories?:\s*(\d+\.?\d*)',
                    'protein': r'protein\s*(\d+\.?\d*)\s*g',
                    'fat': r'total\s+fat\s*(\d+\.?\d*)\s*g',
                    'saturated_fat': r'sat\s+fat\s*(\d+\.?\d*)\s*g',
                    'carbs': r'total\s+carb\s*(\d+\.?\d*)\s*g',
                    'fiber': r'fiber\s*(\d+\.?\d*)\s*g',
                    'sugar': r'sugar\s*(\d+\.?\d*)\s*g',
                    'sodium': r'sodium\s*(\d+\.?\d*)\s*mg',
                    'cholesterol': r'cholesterol\s*(\d+\.?\d*)\s*mg'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, page_text)
                    if match:
                        nutrition_data[key] = float(match.group(1))
            
            # If still no data found, try to extract from any text that looks like nutritional info
            if not nutrition_data:
                page_text = soup.get_text()
                # Look for patterns like "Calories: 250" or "Protein: 15g"
                text_patterns = {
                    'calories': r'calories?:\s*(\d+\.?\d*)',
                    'protein': r'protein:\s*(\d+\.?\d*)\s*g',
                    'fat': r'(?:total\s+)?fat:\s*(\d+\.?\d*)\s*g',
                    'carbs': r'(?:carbs|carbohydrates?):\s*(\d+\.?\d*)\s*g',
                    'fiber': r'fiber:\s*(\d+\.?\d*)\s*g',
                    'sodium': r'sodium:\s*(\d+\.?\d*)\s*mg'
                }
                
                for key, pattern in text_patterns.items():
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        nutrition_data[key] = float(match.group(1))
            
            # If no nutritional data was found, try to estimate based on food name
            if not nutrition_data:
                nutrition_data = self.estimate_nutrition_from_name(url)
            
            if self.debug and nutrition_data:
                print(f"Extracted nutrition data: {nutrition_data}")
            
            return nutrition_data
            
        except Exception as e:
            if self.debug:
                print(f"Error extracting nutrition data from {url}: {e}")
            return {}
    
    def estimate_nutrition_from_name(self, url: str) -> Dict[str, float]:
        """Estimate nutritional values based on food name when detailed data isn't available"""
        # Extract food name from URL or use a generic approach
        food_name = ""
        try:
            # Try to extract food name from URL parameters or use a generic approach
            if 'mid=' in url:
                # This is a PSU nutrition URL, we can't easily extract the name
                # Return empty dict to indicate no estimation available
                return {}
        except:
            pass
        
        # For now, return empty dict - we'll improve this later
        return {}
    
    def calculate_nutrition_score(self, nutrition_data: Dict[str, float], food_name: str = "") -> Tuple[int, str]:
        """Calculate a health score based on nutritional data"""
        if not nutrition_data:
            return 50, "No nutritional data available"
        
        # Check if this is a CYO (Create Your Own) item
        is_cyo = food_name and "cyo" in food_name.lower()
        
        # Check if we have detailed nutritional data or just calories
        has_detailed_data = any(nutrition_data.get(key, 0) > 0 for key in ['protein', 'fat', 'carbs', 'fiber', 'sodium'])
        
        score = 50  # Base score
        reasons = []
        
        # Special handling for CYO items
        if is_cyo:
            # CYO items get a base score that reflects their potential for healthy customization
            score = 70  # Higher base score for CYO items
            reasons.append("Customizable - can be made healthy")
            
            # For CYO items, we're more lenient with protein scoring since it depends on user choices
            protein = nutrition_data.get('protein', 0)
            if protein > 0:  # If there's any protein data, use it
                if protein >= 20:
                    score += 15
                    reasons.append("Good protein content")
                elif protein >= 10:
                    score += 10
                    reasons.append("Moderate protein content")
            else:
                # No protein data for CYO - don't penalize heavily
                score += 5
                reasons.append("Protein content depends on customization")
        else:
            # Regular items use standard protein scoring
            protein = nutrition_data.get('protein', 0)
            if protein > 0:  # Only apply protein scoring if we have protein data
                if protein >= 25:
                    score += 20
                    reasons.append("High protein")
                elif protein >= 15:
                    score += 10
                    reasons.append("Moderate protein")
                elif protein < 5:
                    score -= 10
                    reasons.append("Low protein")
        
        # Calorie density scoring (only if we have both calories and protein data)
        calories = nutrition_data.get('calories', 0)
        if calories > 0 and protein > 0:
            protein_per_calorie = protein / calories if calories > 0 else 0
            if protein_per_calorie >= 0.1:  # 10g protein per 100 calories
                score += 15
                reasons.append("Good protein density")
            elif protein_per_calorie < 0.05 and not is_cyo:  # Less than 5g protein per 100 calories (only penalize non-CYO)
                score -= 10
                reasons.append("Low protein density")
        
        # If we only have calories and no other nutritional data, use calorie-based scoring
        if not has_detailed_data and calories > 0:
            if calories <= 200:
                score += 10
                reasons.append("Low calorie option")
            elif calories <= 400:
                score += 5
                reasons.append("Moderate calorie option")
            elif calories > 800:
                score -= 10
                reasons.append("High calorie option")
        
        # Fat scoring (only if we have fat data)
        fat = nutrition_data.get('fat', 0)
        if fat > 0:
            if 10 <= fat <= 25:
                score += 5
                reasons.append("Moderate fat content")
            elif fat > 40:
                score -= 15
                reasons.append("High fat content")
        
        # Saturated fat penalty (only if we have saturated fat data)
        saturated_fat = nutrition_data.get('saturated_fat', 0)
        if saturated_fat > 0:
            if saturated_fat > 10:
                score -= 15
                reasons.append("High saturated fat")
            elif saturated_fat > 5:
                score -= 5
                reasons.append("Moderate saturated fat")
        
        # Fiber bonus (only if we have fiber data)
        fiber = nutrition_data.get('fiber', 0)
        if fiber > 0:
            if fiber >= 5:
                score += 10
                reasons.append("High fiber")
            elif fiber >= 3:
                score += 5
                reasons.append("Moderate fiber")
        
        # Sugar penalty (only if we have sugar data)
        sugar = nutrition_data.get('sugar', 0)
        if sugar > 0:
            if sugar > 20:
                score -= 15
                reasons.append("High sugar")
            elif sugar > 10:
                score -= 5
                reasons.append("Moderate sugar")
        
        # Sodium penalty (only if we have sodium data)
        sodium = nutrition_data.get('sodium', 0)
        if sodium > 0:
            if sodium > 1000:
                score -= 15
                reasons.append("High sodium")
            elif sodium > 600:
                score -= 5
                reasons.append("Moderate sodium")
        
        score = max(0, min(100, score))
        return score, "; ".join(reasons) if reasons else "Standard nutritional profile"

# --- CSV Export Manager ---
class CSVExportManager:
    def __init__(self, debug=False):
        self.debug = debug
        self.export_dir = "exports"
        
        # Create exports directory if it doesn't exist
        try:
            if not os.path.exists(self.export_dir):
                os.makedirs(self.export_dir)
        except Exception as e:
            if self.debug:
                print(f"Warning: Could not create exports directory: {e}")
            self.export_dir = "."  # Fallback to current directory
    
    def save_nutritional_data(self, food_items: Dict[str, Dict[str, float]], meal: str, campus: str):
        """Save nutritional data to CSV file"""
        try:
            filepath = os.path.join(self.export_dir, f"{campus}_{meal}_{datetime.now().strftime('%Y%m%d')}_nutrition.csv")
            
            # Prepare data for CSV
            csv_data = []
            for food_name, nutrition in food_items.items():
                row = {
                    'food_name': food_name,
                    'meal': meal,
                    'campus': campus,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'calories': nutrition.get('calories', 0),
                    'protein': nutrition.get('protein', 0),
                    'fat': nutrition.get('fat', 0),
                    'saturated_fat': nutrition.get('saturated_fat', 0),
                    'carbs': nutrition.get('carbs', 0),
                    'fiber': nutrition.get('fiber', 0),
                    'sugar': nutrition.get('sugar', 0),
                    'sodium': nutrition.get('sodium', 0),
                    'cholesterol': nutrition.get('cholesterol', 0)
                }
                csv_data.append(row)
            
            # Write to CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['food_name', 'meal', 'campus', 'date', 'calories', 'protein', 'fat', 
                             'saturated_fat', 'carbs', 'fiber', 'sugar', 'sodium', 'cholesterol']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
            
            if self.debug:
                print(f"Saved nutritional data to {filepath}")
            
            return filepath
            
        except Exception as e:
            if self.debug:
                print(f"Error saving nutritional data: {e}")
            return None
    
    def get_nutritional_insights(self, campus: str) -> Dict[str, any]:
        """Analyze saved nutritional data to provide insights"""
        try:
            # Find the most recent nutrition file for this campus
            files = []
            if os.path.exists(self.export_dir):
                for file in os.listdir(self.export_dir):
                    if file.startswith(campus) and file.endswith("_nutrition.csv"):
                        files.append(file)
            
            if not files:
                return {"error": "No nutritional data found"}
            
            # Get the most recent file
            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(self.export_dir, x)))
            filepath = os.path.join(self.export_dir, latest_file)
            
            # Read and analyze the data
            df = pd.read_csv(filepath)
            
            insights = {
                "total_foods_analyzed": len(df),
                "average_calories": float(df['calories'].mean()) if len(df) > 0 else 0,
                "average_protein": float(df['protein'].mean()) if len(df) > 0 else 0,
                "highest_protein_foods": df.nlargest(3, 'protein')[['food_name', 'protein']].to_dict('records') if len(df) > 0 else [],
                "lowest_calorie_foods": df.nsmallest(3, 'calories')[['food_name', 'calories']].to_dict('records') if len(df) > 0 else [],
                "high_fiber_foods": df[df['fiber'] >= 5][['food_name', 'fiber']].to_dict('records') if len(df) > 0 else [],
                "low_sodium_foods": df[df['sodium'] <= 500][['food_name', 'sodium']].to_dict('records') if len(df) > 0 else []
            }
            
            return insights
            
        except Exception as e:
            if self.debug:
                print(f"Error analyzing nutritional insights: {e}")
            return {"error": f"Failed to analyze nutritional data: {str(e)}"}

# --- Enhanced Menu Analyzer Class ---
class MenuAnalyzer:
    def __init__(self, campus_key: str, gemini_api_key: str = None, exclude_beef=False, exclude_pork=False,
                 vegetarian=False, vegan=False, prioritize_protein=False, debug=False, extract_nutrition=True):
        self.base_url = "https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm"
        self.campus_key = campus_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.debug = debug
        self.exclude_beef = exclude_beef
        self.exclude_pork = exclude_pork
        self.vegetarian = vegetarian
        self.vegan = vegan
        self.prioritize_protein = prioritize_protein
        self.extract_nutrition = extract_nutrition
        
        # Initialize nutritional data extractor and CSV manager
        self.nutrition_extractor = NutritionalDataExtractor(debug=debug)
        self.csv_manager = CSVExportManager(debug=debug)
        
        # Use the passed parameter or fall back to environment variable
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            self.gemini_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                f"?key={self.gemini_api_key}"
            )
        elif self.debug:
            print("No Gemini API key provided. Using local analysis only.")
        
        if self.prioritize_protein and self.debug:
            print("INFO: Analysis is set to prioritize protein content.")
        
        if self.extract_nutrition and self.debug:
            print("INFO: Nutritional data extraction is enabled.")

    def get_initial_form_data(self) -> Optional[Dict[str, Dict[str, str]]]:
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            options = {'campus': {}, 'meal': {}, 'date': {}}
            for name in options.keys():
                select_tag = soup.find('select', {'name': f'sel{name.capitalize()}' if name != 'date' else 'selMenuDate'})
                if select_tag:
                    for option in select_tag.find_all('option'):
                        value = option.get('value', '').strip()
                        text = option.get_text(strip=True)
                        if value and text:
                            options[name][text.lower()] = value
            
            if self.debug:
                print("Available campus options:")
                for name, val in options['campus'].items():
                    print(f"  {name}: {val}")
            
            return options
        except requests.RequestException as e:
            if self.debug:
                print(f"Error fetching initial page: {e}")
            return None

    def looks_like_food_item(self, text: str) -> bool:
        if not text or len(text.strip()) < 3 or len(text.strip()) > 70:
            return False
        text_lower = text.lower()
        non_food_keywords = [
            'select', 'menu', 'date', 'campus', 'print', 'view', 'nutrition', 'allergen',
            'feedback', 'contact', 'hours', 'location', 'penn state', 'altoona', 
            'port sky', 'cafe', 'kitchen', 'station', 'grill', 'deli', 'market',
            'made to order', 'action', 'no items', 'not available', 'closed'
        ]
        if any(keyword in text_lower for keyword in non_food_keywords):
            return False
        if not any(c.isalpha() for c in text):
            return False
        return True

    def extract_items_from_meal_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        items = {}
        # Look specifically for nutrition links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '')
            text = a_tag.get_text(strip=True)
            
            # Check if this is a nutrition link
            if 'nutrition-label' in href and self.looks_like_food_item(text):
                relative_url = href
                full_url = urljoin(self.base_url, relative_url)
                items[text] = full_url
        return items

    def find_campus_value(self, campus_options: Dict[str, str]) -> Tuple[Optional[str], str]:
        """Find the correct campus value based on the campus key"""
        campus_key_lower = self.campus_key.lower()
        
        # Mapping of our campus keys to search terms
        search_terms = {
            'altoona-port-sky': ['altoona', 'port sky'],
            'beaver-brodhead': ['beaver', 'brodhead'],
            'behrend-brunos': ['behrend', 'bruno'],
            'behrend-dobbins': ['behrend', 'dobbins'],
            'berks-tullys': ['berks', 'tully'],
            'brandywine-blue-apple': ['brandywine', 'blue apple'],
            'greater-allegheny-cafe-metro': ['greater allegheny', 'cafe metro'],
            'harrisburg-stacks': ['harrisburg', 'stacks'],
            'harrisburg-outpost': ['harrisburg', 'outpost'],
            'hazleton-highacres': ['hazleton', 'highacres'],
            'mont-alto-mill': ['mont alto', 'mill'],
            'up-east-findlay': ['east', 'findlay'],
            'up-north-warnock': ['north', 'warnock'],
            'up-pollock': ['pollock'],
            'up-south-redifer': ['south', 'redifer'],
            'up-west-waring': ['west', 'waring']
        }
        
        terms = search_terms.get(campus_key_lower, [campus_key_lower])
        
        # Try to find exact matches first
        for name, value in campus_options.items():
            if all(term in name for term in terms):
                return value, name
        
        # Try partial matches
        for name, value in campus_options.items():
            if any(term in name for term in terms):
                return value, name
        
        return None, ""

    def extract_nutritional_data_for_items(self, items: Dict[str, str]) -> Dict[str, Dict[str, float]]:
        """Extract nutritional data for all food items"""
        nutrition_data = {}
        
        if not self.extract_nutrition:
            return nutrition_data
        
        for food_name, url in items.items():
            if self.debug:
                print(f"Extracting nutrition data for: {food_name}")
            
            try:
                nutrition = self.nutrition_extractor.extract_nutritional_data(url)
                if nutrition:
                    nutrition_data[food_name] = nutrition
            except Exception as e:
                if self.debug:
                    print(f"Error extracting nutrition for {food_name}: {e}")
            
            # Add delay to avoid overwhelming the server
            time.sleep(0.5)
        
        return nutrition_data

    def run_analysis(self) -> Dict[str, List[Tuple[str, int, str, str]]]:
        try:
            if self.debug:
                print(f"Fetching initial form options for campus: {self.campus_key}")
            
            form_options = self.get_initial_form_data()
            if not form_options:
                print("Could not fetch form data. Using fallback.")
                return self.get_fallback_data()

            campus_options = form_options.get('campus', {})
            campus_value, campus_name_found = self.find_campus_value(campus_options)
            
            if not campus_value:
                print(f"Could not find campus value for {self.campus_key}. Available options: {list(campus_options.keys())}")
                return self.get_fallback_data()
            
            if self.debug:
                print(f"Found campus: {campus_name_found} with value: {campus_value}")

            date_options = form_options.get('date', {})
            today_str_key = datetime.now().strftime('%A, %B %d').lower()
            date_value = date_options.get(today_str_key)
            if not date_value:
                if date_options:
                    first_available_date = list(date_options.keys())[0]
                    date_value = list(date_options.values())[0]
                    print(f"Warning: Today's menu ('{today_str_key}') not found. Using first available date: {first_available_date}")
                else:
                    print("No dates found. Using fallback.")
                    return self.get_fallback_data()

            daily_menu = {}
            meal_options = form_options.get('meal', {})
            
            for meal_name in ["Breakfast", "Lunch", "Dinner"]:
                meal_key = meal_name.lower()
                meal_value = meal_options.get(meal_key)
                
                if not meal_value:
                    if self.debug:
                        print(f"Could not find form value for '{meal_name}'. Skipping.")
                    continue

                try:
                    form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
                    if self.debug:
                        print(f"Fetching menu for {meal_name} with data: {form_data}")
                    response = self.session.post(self.base_url, data=form_data, timeout=30)
                    response.raise_for_status()
                    meal_soup = BeautifulSoup(response.content, 'html.parser')
                    items = self.extract_items_from_meal_page(meal_soup)
                    if items:
                        daily_menu[meal_name] = items
                        if self.debug:
                            print(f"Found {len(items)} items for {meal_name}.")
                        
                        # Extract nutritional data if enabled
                        if self.extract_nutrition:
                            try:
                                nutrition_data = self.extract_nutritional_data_for_items(items)
                                if nutrition_data:
                                    # Save nutritional data to CSV
                                    self.csv_manager.save_nutritional_data(nutrition_data, meal_name, self.campus_key)
                            except Exception as e:
                                if self.debug:
                                    print(f"Error extracting nutrition data for {meal_name}: {e}")
                    else:
                        # Explicitly mark meals with no items
                        daily_menu[meal_name] = {}
                        if self.debug:
                            print(f"No items found for {meal_name}.")
                    time.sleep(0.5)
                except requests.RequestException as e:
                    if self.debug:
                        print(f"Error fetching {meal_name} menu: {e}")
                    # Mark as no items if there's an error
                    daily_menu[meal_name] = {}

            if not daily_menu:
                print("Failed to scrape any menu items from the website. Using fallback.")
                return self.get_fallback_data()
            
            analyzed_results = self.analyze_menu_with_gemini(daily_menu) if self.gemini_api_key else self.analyze_menu_local(daily_menu)
            
            final_results = {}
            for meal, items in analyzed_results.items():
                # First, apply the hard filters based on user preferences
                filtered_items = self.apply_hard_filters(items)
                # Then, slice the list to get only the top 5 items
                final_results[meal] = filtered_items[:5]
            
            return final_results
            
        except Exception as e:
            if self.debug:
                print(f"Error in run_analysis: {e}")
                import traceback
                traceback.print_exc()
            return self.get_fallback_data()

    def analyze_menu_with_gemini(self, daily_menu: Dict[str, Dict[str, str]]) -> Dict[str, List[Tuple[str, int, str, str]]]:
        try:
            exclusions = []
            if self.exclude_beef:
                exclusions.append("No beef.")
            if self.exclude_pork:
                exclusions.append("No pork.")
            if self.vegetarian:
                exclusions.append("Only vegetarian items (includes eggs).")
            if self.vegan:
                exclusions.append("Only vegan items (no animal products including eggs and dairy).")
            restrictions_text = " ".join(exclusions) if exclusions else "None."

            priority_instruction = ("prioritize PROTEIN content" if self.prioritize_protein else "prioritize a BALANCE of high protein and healthy preparation")
            
            # Get nutritional data for each meal to include in analysis
            menu_with_nutrition = {}
            for meal, items in daily_menu.items():
                menu_with_nutrition[meal] = {}
                for food_name, url in items.items():
                    # Try to get nutritional data for this item
                    nutrition_data = {}
                    try:
                        nutrition_file = os.path.join(self.csv_manager.export_dir, f"{self.campus_key}_{meal}_{datetime.now().strftime('%Y%m%d')}_nutrition.csv")
                        if os.path.exists(nutrition_file):
                            df = pd.read_csv(nutrition_file)
                            item_data = df[df['food_name'] == food_name]
                            if not item_data.empty:
                                nutrition_data = item_data.iloc[0].to_dict()
                    except Exception as e:
                        if self.debug:
                            print(f"Error loading nutrition data for {food_name}: {e}")
                    
                    menu_with_nutrition[meal][food_name] = {
                        'url': url,
                        'nutrition': nutrition_data
                    }

            # Ask for more items (e.g., 15) to allow for filtering down to 5.
            prompt = f"""
            Analyze the menu below. Your goal is to {priority_instruction}. My restrictions are: {restrictions_text}
            
            IMPORTANT: Use the detailed nutritional data provided for each food item to make accurate health assessments. 
            Prioritize items with higher protein content, lower sodium, higher fiber, and better macro/micronutrient profiles.
            
            SPECIAL NOTE: Items with "CYO" (Create Your Own) in the name have variable nutritional content based on user customization choices. 
            These items should be scored based on their potential for healthy customization rather than their base nutritional values.
            CYO items like salads, bowls, and wraps can be made very healthy depending on ingredient choices.
            
            For EACH meal, identify the top 15 options based on nutritional value and health benefits.
            Return your response as a single, valid JSON object with keys "Breakfast", "Lunch", "Dinner". 
            Each value should be a list of objects, each with "food_name", "score" (0-100), and "reasoning".
            
            Menu with nutritional data: {json.dumps(menu_with_nutrition, indent=2)}
            """
            
            response = self.session.post(self.gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
            response.raise_for_status()
            data = response.json()
            text_response = data["candidates"][0]["content"]["parts"][0]["text"]
            json_str = re.search(r'\{.*\}', text_response, re.DOTALL).group(0)
            parsed_json = json.loads(json_str)

            results = {}
            for meal, analyzed_items in parsed_json.items():
                meal_results = []
                for item_info in analyzed_items:
                    food_name = item_info.get("food_name")
                    url = daily_menu.get(meal, {}).get(food_name, '#')
                    meal_results.append((food_name, item_info.get("score"), item_info.get("reasoning"), url))
                meal_results.sort(key=lambda x: x[1], reverse=True)
                results[meal] = meal_results
            return results
        except Exception as e:
            if self.debug:
                print(f"Gemini analysis failed: {e}. Falling back to local analysis.")
            return self.analyze_menu_local(daily_menu)

    def apply_hard_filters(self, food_items: List[Tuple[str, int, str, str]]) -> List[Tuple[str, int, str, str]]:
        if not (self.exclude_beef or self.exclude_pork or self.vegetarian or self.vegan):
            return food_items
        filtered_list = []
        for food, score, reason, url in food_items:
            item_lower = food.lower()
            excluded = False
            if self.exclude_beef and "beef" in item_lower:
                excluded = True
            if self.exclude_pork and any(p in item_lower for p in ["pork", "bacon", "sausage", "ham"]):
                excluded = True
            if self.vegetarian and any(m in item_lower for m in ["beef", "pork", "chicken", "turkey", "fish", "salmon", "tuna", "bacon", "sausage", "ham"]):
                excluded = True
            if self.vegan and any(m in item_lower for m in ["beef", "pork", "chicken", "turkey", "fish", "salmon", "tuna", "bacon", "sausage", "ham", "egg", "eggs", "dairy", "milk", "cheese", "butter", "yogurt"]):
                excluded = True
            if not excluded:
                filtered_list.append((food, score, reason, url))
        return filtered_list

    def get_fallback_data(self) -> Dict[str, List[Tuple[str, int, str, str]]]:
        fallback_menu = {
            "Breakfast": {"Scrambled Eggs": "#", "Turkey Sausage": "#", "Oatmeal": "#"},
            "Lunch": {"Grilled Chicken Salad": "#", "Turkey Club Sandwich": "#", "Quinoa Bowl": "#"},
            "Dinner": {"Baked Salmon": "#", "Beef Stir-Fry": "#", "Grilled Chicken Breast": "#"}
        }
        analyzed = self.analyze_menu_local(fallback_menu)
        filtered_fallback = {}
        for meal, items in analyzed.items():
            filtered_items = self.apply_hard_filters(items)
            filtered_fallback[meal] = filtered_items[:5]
        return filtered_fallback

    def analyze_menu_local(self, daily_menu: Dict[str, Dict[str, str]]) -> Dict[str, List[Tuple[str, int, str, str]]]:
        results = {}
        for meal, items in daily_menu.items():
            if not items:  # Handle empty meals
                results[meal] = []
            else:
                analyzed_items = self.analyze_food_health_local_list(items, meal)
                analyzed_items.sort(key=lambda x: x[1], reverse=True)
                results[meal] = analyzed_items
        return results

    def analyze_food_health_local_list(self, food_items: Dict[str, str], meal: str = "") -> List[Tuple[str, int, str, str]]:
        health_scores = []
        protein_keywords = {'excellent': ['chicken', 'salmon', 'tuna', 'turkey'], 'good': ['beef', 'eggs', 'tofu', 'beans'], 'moderate': ['cheese', 'yogurt']}
        healthy_prep = {'excellent': ['grilled', 'baked', 'steamed'], 'good': ['sautéed'], 'poor': ['fried', 'creamy', 'battered']}

        protein_weights = {'excellent': 40, 'good': 30, 'moderate': 15} if self.prioritize_protein else {'excellent': 30, 'good': 20, 'moderate': 10}
        prep_weights = {'excellent': 10, 'good': 5, 'poor': -15} if self.prioritize_protein else {'excellent': 20, 'good': 10, 'poor': -25}

        for item, url in food_items.items():
            item_lower = item.lower()
            score, reasoning = 50, []
            has_nutrition_data = False
            
            # Try to get nutritional data if available - this is now the primary scoring method
            if self.extract_nutrition and meal:
                try:
                    nutrition_file = os.path.join(self.csv_manager.export_dir, f"{self.campus_key}_{meal}_{datetime.now().strftime('%Y%m%d')}_nutrition.csv")
                    if os.path.exists(nutrition_file):
                        df = pd.read_csv(nutrition_file)
                        item_data = df[df['food_name'] == item]
                        if not item_data.empty:
                            nutrition_dict = item_data.iloc[0].to_dict()
                            nutrition_score, nutrition_reason = self.nutrition_extractor.calculate_nutrition_score(nutrition_dict, item)
                            
                            # Use nutrition score as primary score, with keyword analysis as modifier
                            score = nutrition_score
                            reasoning.append(f"Nutritional analysis: {nutrition_reason}")
                            has_nutrition_data = True
                            
                            if self.debug:
                                print(f"Using nutritional data for {item}: score={nutrition_score}, reason={nutrition_reason}")
                except Exception as e:
                    if self.debug:
                        print(f"Error loading nutrition data for {item}: {e}")
            
            # If no nutritional data available, fall back to keyword-based analysis
            if not has_nutrition_data:
                for level, keywords in protein_keywords.items():
                    if any(kw in item_lower for kw in keywords):
                        score += protein_weights[level]
                        reasoning.append(f"High protein ({level})")
                        break
                for level, keywords in healthy_prep.items():
                    if any(kw in item_lower for kw in keywords):
                        score += prep_weights[level]
                        reasoning.append(f"Prep style ({level})")
                        break
            else:
                # If we have nutritional data, add keyword-based modifiers (smaller impact)
                for level, keywords in protein_keywords.items():
                    if any(kw in item_lower for kw in keywords):
                        score += protein_weights[level] * 0.3  # Reduced impact when nutrition data is available
                        reasoning.append(f"Protein keyword bonus ({level})")
                        break
                for level, keywords in healthy_prep.items():
                    if any(kw in item_lower for kw in keywords):
                        score += prep_weights[level] * 0.3  # Reduced impact when nutrition data is available
                        reasoning.append(f"Prep style bonus ({level})")
                        break
            
            score = max(0, min(100, score))
            health_scores.append((item, score, ", ".join(reasoning) or "Standard option", url))
        return health_scores

# --- Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        print("=== ANALYZE REQUEST START ===")
        data = request.json
        print(f"Received request with data: {data}")
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Simple validation
        campus = data.get('campus', 'altoona-port-sky')
        vegetarian = data.get('vegetarian', False)
        vegan = data.get('vegan', False)
        exclude_beef = data.get('exclude_beef', False)
        exclude_pork = data.get('exclude_pork', False)
        prioritize_protein = data.get('prioritize_protein', False)
        extract_nutrition = True  # Always enabled
        
        print(f"Parsed parameters - campus: {campus}, vegetarian: {vegetarian}, vegan: {vegan}")
        
        # Validate that vegan and vegetarian aren't both selected
        if vegan and vegetarian:
            return jsonify({"error": "Cannot be both vegan and vegetarian"}), 400
        
        # Get API key from environment
        api_key = os.getenv('GEMINI_API_KEY')
        print(f"Gemini API key available: {bool(api_key)}")

        print("Creating MenuAnalyzer instance...")
        analyzer = MenuAnalyzer(
            campus_key=campus,
            gemini_api_key=api_key,
            exclude_beef=exclude_beef,
            exclude_pork=exclude_pork,
            vegetarian=vegetarian,
            vegan=vegan,
            prioritize_protein=prioritize_protein,
            debug=True,
            extract_nutrition=extract_nutrition
        )
        
        print("Running analysis...")
        recommendations = analyzer.run_analysis()
        print(f"Analysis complete. Returning recommendations: {recommendations}")
        
        return jsonify(recommendations)
        
    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500

@app.route('/api/nutrition-insights/<campus>')
def get_nutrition_insights(campus):
    """Get nutritional insights for a specific campus"""
    try:
        csv_manager = CSVExportManager(debug=True)
        insights = csv_manager.get_nutritional_insights(campus)
        return jsonify(insights)
    except Exception as e:
        print(f"Error getting nutrition insights: {e}")
        return jsonify({"error": "Failed to get nutrition insights"}), 500

@app.route('/api/download-nutrition/<campus>')
def download_nutrition_csv(campus):
    """Download the most recent nutrition CSV for a campus"""
    try:
        csv_manager = CSVExportManager(debug=True)
        export_dir = csv_manager.export_dir
        
        # Find the most recent nutrition file for this campus
        files = []
        if os.path.exists(export_dir):
            for file in os.listdir(export_dir):
                if file.startswith(campus) and file.endswith("_nutrition.csv"):
                    files.append(file)
        
        if not files:
            return jsonify({"error": "No nutrition data found"}), 404
        
        # Get the most recent file
        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(export_dir, x)))
        filepath = os.path.join(export_dir, latest_file)
        
        return send_from_directory(export_dir, latest_file, as_attachment=True)
    except Exception as e:
        print(f"Error downloading nutrition CSV: {e}")
        return jsonify({"error": "Failed to download nutrition data"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

