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

# --- Nutrition Data Extractor Class ---
class NutritionExtractor:
    def __init__(self, debug=False):
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_nutrition_data(self, url: str) -> Dict[str, any]:
        """Extract comprehensive nutrition data from a Penn State nutrition page"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            nutrition_data = {
                'food_name': '',
                'serving_size': '',
                'calories': 0,
                'calories_from_fat': 0,
                'total_fat_g': 0.0,
                'total_fat_dv': 0.0,
                'saturated_fat_g': 0.0,
                'saturated_fat_dv': 0.0,
                'trans_fat_g': 0.0,
                'cholesterol_mg': 0.0,
                'sodium_mg': 0.0,
                'sodium_dv': 0.0,
                'total_carb_g': 0.0,
                'total_carb_dv': 0.0,
                'dietary_fiber_g': 0.0,
                'dietary_fiber_dv': 0.0,
                'sugars_g': 0.0,
                'added_sugars_g': 0.0,
                'protein_g': 0.0,
                'protein_dv': 0.0,
                'vitamin_d_mcg': 0.0,
                'calcium_mg': 0.0,
                'iron_mg': 0.0,
                'potassium_mg': 0.0,
                'ingredients': '',
                'extraction_timestamp': datetime.now().isoformat(),
                'url': url
            }
            
            # Extract food name
            food_name_elem = soup.find('h1') or soup.find('h2') or soup.find('title')
            if food_name_elem:
                nutrition_data['food_name'] = food_name_elem.get_text(strip=True)
            
            # Look for nutrition facts table or structured data
            nutrition_table = soup.find('table', class_=re.compile(r'nutrition|facts', re.I))
            if not nutrition_table:
                # Try to find any table that might contain nutrition data
                tables = soup.find_all('table')
                for table in tables:
                    if any(keyword in table.get_text().lower() for keyword in ['calories', 'fat', 'protein', 'carbohydrate']):
                        nutrition_table = table
                        break
            
            if nutrition_table:
                self._parse_nutrition_table(nutrition_table, nutrition_data)
            else:
                # Try to extract from text patterns if no table found
                self._parse_nutrition_text(soup, nutrition_data)
            
            # Extract ingredients
            ingredients_text = self._extract_ingredients(soup)
            nutrition_data['ingredients'] = ingredients_text
            
            if self.debug:
                print(f"Extracted nutrition data for: {nutrition_data['food_name']}")
            
            return nutrition_data
            
        except Exception as e:
            if self.debug:
                print(f"Error extracting nutrition data from {url}: {e}")
            return self._get_empty_nutrition_data(url)
    
    def _parse_nutrition_table(self, table, nutrition_data):
        """Parse nutrition data from a structured table - optimized for Penn State format"""
        # First, try to extract serving size and calories from the header
        header_cell = table.find('th', class_='top')
        if header_cell:
            header_text = header_cell.get_text()
            
            # Extract serving size
            serving_match = re.search(r'Serving Size:\s*([^<]+)', header_text)
            if serving_match:
                nutrition_data['serving_size'] = serving_match.group(1).strip()
            
            # Extract calories
            calories_match = re.search(r'Calories:\s*(\d+)', header_text)
            if calories_match:
                nutrition_data['calories'] = int(calories_match.group(1))
            
            # Extract calories from fat
            fat_calories_match = re.search(r'Calories from Fat:\s*(\d+)', header_text)
            if fat_calories_match:
                nutrition_data['calories_from_fat'] = int(fat_calories_match.group(1))
        
        # Parse the nutrition facts table rows
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                # Get text from all cells
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                
                # Look for nutrition data in the table cells
                for i, cell_text in enumerate(cell_texts):
                    cell_lower = cell_text.lower()
                    
                    # Extract values and percentages using regex
                    value_match = re.search(r'([\d.]+)g', cell_text)
                    mg_value_match = re.search(r'([\d.]+)mg', cell_text)
                    mcg_value_match = re.search(r'([\d.]+)mcg', cell_text)
                    percent_match = re.search(r'(\d+)%', cell_text)
                    
                    if value_match:
                        value = float(value_match.group(1))
                        percent = float(percent_match.group(1)) if percent_match else 0.0
                    elif mg_value_match:
                        value = float(mg_value_match.group(1))
                        percent = float(percent_match.group(1)) if percent_match else 0.0
                    elif mcg_value_match:
                        value = float(mcg_value_match.group(1))
                        percent = float(percent_match.group(1)) if percent_match else 0.0
                    else:
                        continue
                    
                    # Map nutrition labels to data structure
                    if 'total fat' in cell_lower and 'g' in cell_text:
                        nutrition_data['total_fat_g'] = value
                        nutrition_data['total_fat_dv'] = percent
                    elif 'sat fat' in cell_lower and 'g' in cell_text:
                        nutrition_data['saturated_fat_g'] = value
                        nutrition_data['saturated_fat_dv'] = percent
                    elif 'trans fat' in cell_lower and 'g' in cell_text:
                        nutrition_data['trans_fat_g'] = value
                    elif 'cholesterol' in cell_lower and 'mg' in cell_text:
                        nutrition_data['cholesterol_mg'] = value
                    elif 'sodium' in cell_lower and 'mg' in cell_text:
                        nutrition_data['sodium_mg'] = value
                        nutrition_data['sodium_dv'] = percent
                    elif 'total carb' in cell_lower and 'g' in cell_text:
                        nutrition_data['total_carb_g'] = value
                        nutrition_data['total_carb_dv'] = percent
                    elif 'dietary fiber' in cell_lower and 'g' in cell_text:
                        nutrition_data['dietary_fiber_g'] = value
                        nutrition_data['dietary_fiber_dv'] = percent
                    elif 'sugars' in cell_lower and 'g' in cell_text and 'added' not in cell_lower:
                        nutrition_data['sugars_g'] = value
                    elif 'added sugar' in cell_lower and 'g' in cell_text:
                        nutrition_data['added_sugars_g'] = value
                    elif 'protein' in cell_lower and 'g' in cell_text:
                        nutrition_data['protein_g'] = value
                        nutrition_data['protein_dv'] = percent
                    elif 'vitamin d' in cell_lower and 'mcg' in cell_text:
                        nutrition_data['vitamin_d_mcg'] = value
                    elif 'calcium' in cell_lower and 'mg' in cell_text:
                        nutrition_data['calcium_mg'] = value
                    elif 'iron' in cell_lower and 'mg' in cell_text:
                        nutrition_data['iron_mg'] = value
                    elif 'potassium' in cell_lower and 'mg' in cell_text:
                        nutrition_data['potassium_mg'] = value
    
    def _parse_nutrition_text(self, soup, nutrition_data):
        """Parse nutrition data from text patterns when no table is available"""
        text_content = soup.get_text().lower()
        
        # Common patterns for nutrition data
        patterns = {
            'calories': r'calories[:\s]*(\d+)',
            'total_fat': r'total fat[:\s]*([\d.]+)g',
            'saturated_fat': r'saturated fat[:\s]*([\d.]+)g',
            'sodium': r'sodium[:\s]*([\d.]+)mg',
            'total_carb': r'total carbohydrate[:\s]*([\d.]+)g|total carb[:\s]*([\d.]+)g',
            'protein': r'protein[:\s]*([\d.]+)g'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_content)
            if match:
                value = float(match.group(1) or match.group(2) or 0)
                if key == 'calories':
                    nutrition_data['calories'] = int(value)
                elif key == 'total_fat':
                    nutrition_data['total_fat_g'] = value
                elif key == 'saturated_fat':
                    nutrition_data['saturated_fat_g'] = value
                elif key == 'sodium':
                    nutrition_data['sodium_mg'] = value
                elif key == 'total_carb':
                    nutrition_data['total_carb_g'] = value
                elif key == 'protein':
                    nutrition_data['protein_g'] = value
    
    def _extract_ingredients(self, soup) -> str:
        """Extract ingredients list from the page - optimized for Penn State format"""
        # Look for ingredients in the specific Penn State format
        ingredients_div = soup.find('div', class_='row col-12 mt-10 rpt-ml-20')
        if ingredients_div:
            ingredients_text = ingredients_div.get_text()
            
            # Extract ingredients using the Penn State pattern
            ingredients_match = re.search(r'Ingredients:\s*(.+?)(?:\n\n|\n[A-Z]|Allergens:)', ingredients_text, re.IGNORECASE | re.DOTALL)
            if ingredients_match:
                ingredients = ingredients_match.group(1).strip()
                # Clean up the ingredients text
                ingredients = re.sub(r'\s+', ' ', ingredients)
                return ingredients[:1000]  # Increased limit for more complete ingredients
        
        # Fallback to general patterns
        ingredients_patterns = [
            r'ingredients?[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'contains?[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)',
            r'ingredient list[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)'
        ]
        
        text_content = soup.get_text()
        
        for pattern in ingredients_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE | re.DOTALL)
            if match:
                ingredients = match.group(1).strip()
                # Clean up the ingredients text
                ingredients = re.sub(r'\s+', ' ', ingredients)
                return ingredients[:1000]  # Increased limit
        
        return ''
    
    def _get_empty_nutrition_data(self, url: str) -> Dict[str, any]:
        """Return empty nutrition data structure when extraction fails"""
        return {
            'food_name': 'Unknown',
            'serving_size': '',
            'calories': 0,
            'calories_from_fat': 0,
            'total_fat_g': 0.0,
            'total_fat_dv': 0.0,
            'saturated_fat_g': 0.0,
            'saturated_fat_dv': 0.0,
            'trans_fat_g': 0.0,
            'cholesterol_mg': 0.0,
            'sodium_mg': 0.0,
            'sodium_dv': 0.0,
            'total_carb_g': 0.0,
            'total_carb_dv': 0.0,
            'dietary_fiber_g': 0.0,
            'dietary_fiber_dv': 0.0,
            'sugars_g': 0.0,
            'added_sugars_g': 0.0,
            'protein_g': 0.0,
            'protein_dv': 0.0,
            'vitamin_d_mcg': 0.0,
            'calcium_mg': 0.0,
            'iron_mg': 0.0,
            'potassium_mg': 0.0,
            'ingredients': '',
            'extraction_timestamp': datetime.now().isoformat(),
            'url': url
        }

# --- Menu Analyzer Class ---
class MenuAnalyzer:
    def __init__(self, campus_key: str, gemini_api_key: str = None, exclude_beef=False, exclude_pork=False,
                 vegetarian=False, vegan=False, prioritize_protein=False, debug=False, extract_nutrition=False):
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
        
        # Initialize nutrition extractor (always needed for fallback)
        self.nutrition_extractor = NutritionExtractor(debug=debug)
        
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

    def get_initial_form_data(self) -> Optional[Dict[str, Dict[str, str]]]:
        try:
            response = self.session.get(self.base_url)
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
            if self.debug: print(f"Error fetching initial page: {e}")
            return None

    def looks_like_food_item(self, text: str) -> bool:
        if not text or len(text.strip()) < 3 or len(text.strip()) > 70: return False
        text_lower = text.lower()
        non_food_keywords = [
            'select', 'menu', 'date', 'campus', 'print', 'view', 'nutrition', 'allergen',
            'feedback', 'contact', 'hours', 'location', 'penn state', 'altoona', 
            'port sky', 'cafe', 'kitchen', 'station', 'grill', 'deli', 'market',
            'made to order', 'action', 'no items', 'not available', 'closed',
            'dietary filters', 'sign in', 'account', 'lunch for', 'breakfast for',
            'dinner for', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday', 'september', 'october', 'november', 'december',
            'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
            '2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017',
            '2016', '2015', '2014', '2013', '2012', '2011', '2010', '2009', '2008',
            '2007', '2006', '2005', '2004', '2003', '2002', '2001', '2000',
            'does not contain', 'contains', 'allergen', 'dietary', 'filters',
            'custom food', 'order', 'win', 'daily menu', 'nutrition ▸'
        ]
        if any(keyword in text_lower for keyword in non_food_keywords): return False
        if not any(c.isalpha() for c in text): return False
        return True

    def extract_items_from_meal_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        items = {}
        for a_tag in soup.find_all('a', href=True):
            text = a_tag.get_text(strip=True)
            if self.looks_like_food_item(text):
                relative_url = a_tag['href']
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

    def run_analysis(self) -> Dict[str, List[Tuple[str, int, str, str]]]:
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
        if not date_options:
            print("No dates found. Using fallback.")
            return self.get_fallback_data()
        
        # Use the first available date (default date the site loads into)
        first_date_key = list(date_options.keys())[0]
        date_value = date_options[first_date_key]
        
        if self.debug:
            print(f"Using date: {first_date_key} -> {date_value}")

        daily_menu = {}
        meal_options = form_options.get('meal', {})
        
        for meal_name in ["Breakfast", "Lunch", "Dinner"]:
            meal_key = meal_name.lower()
            meal_value = meal_options.get(meal_key)
            
            if not meal_value:
                if self.debug: print(f"Could not find form value for '{meal_name}'. Skipping.")
                continue

            try:
                form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
                if self.debug: print(f"Fetching menu for {meal_name} with data: {form_data}")
                response = self.session.post(self.base_url, data=form_data)
                response.raise_for_status()
                meal_soup = BeautifulSoup(response.content, 'html.parser')
                items = self.extract_items_from_meal_page(meal_soup)
                if items:
                    daily_menu[meal_name] = items
                    if self.debug: print(f"Found {len(items)} items for {meal_name}.")
                else:
                    # Explicitly mark meals with no items
                    daily_menu[meal_name] = {}
                    if self.debug: print(f"No items found for {meal_name}.")
                time.sleep(0.5)
            except requests.RequestException as e:
                if self.debug: print(f"Error fetching {meal_name} menu: {e}")
                # Mark as no items if there's an error
                daily_menu[meal_name] = {}

        if not daily_menu:
            print("Failed to scrape any menu items from the website. Using fallback.")
            return self.get_fallback_data()
        
        # Generate nutrition CSV first to get complete data
        if self.extract_nutrition:
            if self.debug: print("📊 Generating nutrition CSV for detailed analysis...")
            csv_path = self.generate_nutrition_csv(daily_menu)
            if csv_path:
                # Load the CSV data for AI analysis
                import pandas as pd
                df = pd.read_csv(csv_path)
                csv_data = df.to_dict('records')
                
                if self.debug: print(f"📈 CSV generated with {len(csv_data)} nutrition records")
                
                # Use AI to analyze the complete nutrition data
                if self.gemini_api_key:
                    if self.debug: print("🔑 Gemini API key available - attempting AI analysis...")
                    analyzed_results = self.analyze_menu_with_gemini_csv(csv_data)
                else:
                    if self.debug: print("⚠️ No Gemini API key - using local analysis...")
                    analyzed_results = self.analyze_menu_local_from_csv(csv_data)
            else:
                # If CSV generation fails, still try to extract nutrition data for analysis
                print("CSV generation failed, extracting nutrition data directly for analysis...")
                all_nutrition_data = []
                
                # Extract nutrition data for all items
                for meal_name, items in daily_menu.items():
                    if not items:
                        continue
                    if self.debug:
                        print(f"Processing {meal_name} with {len(items)} items")
                    for food_name, url in items.items():
                        if url and url != '#':
                            try:
                                nutrition_data = self.nutrition_extractor.extract_nutrition_data(url)
                                nutrition_data['meal'] = meal_name
                                nutrition_data['campus'] = self.campus_key
                                all_nutrition_data.append(nutrition_data)
                                if self.debug:
                                    print(f"  Added {food_name} to {meal_name}")
                                time.sleep(0.1)  # Small delay
                            except Exception as e:
                                if self.debug:
                                    print(f"Error extracting nutrition for {food_name}: {e}")
                                continue
                
                if all_nutrition_data:
                    # Use AI to analyze the extracted nutrition data
                    analyzed_results = self.analyze_menu_with_gemini_csv(all_nutrition_data) if self.gemini_api_key else self.analyze_menu_local_from_csv(all_nutrition_data)
                else:
                    # Final fallback to original method
                    analyzed_results = self.analyze_menu_with_gemini(daily_menu) if self.gemini_api_key else self.analyze_menu_local(daily_menu)
        else:
            # Use original method if nutrition extraction is disabled
            analyzed_results = self.analyze_menu_with_gemini(daily_menu) if self.gemini_api_key else self.analyze_menu_local(daily_menu)
        
        final_results = {}
        for meal, items in analyzed_results.items():
            # First, apply the hard filters based on user preferences
            filtered_items = self.apply_hard_filters(items)
            
            # Check for CYO items in top 5 and add extra recommendations
            top_5 = filtered_items[:5]
            cyo_count = sum(1 for item in top_5 if 'cyo' in item[0].lower() or 'create your own' in item[0].lower())
            
            if cyo_count > 0:
                # Add extra items for each CYO item found
                extra_items = filtered_items[5:5+cyo_count]  # Get next items after top 5
                final_results[meal] = top_5 + extra_items
            else:
                final_results[meal] = top_5
        
        # Add CSV path to results if it was generated
        if self.extract_nutrition and 'csv_path' in locals():
            final_results['_csv_path'] = csv_path
        
        # Extract nutrition data for displayed recommendations
        if self.extract_nutrition:
            enhanced_results = self.enhance_recommendations_with_nutrition(final_results, daily_menu)
            return enhanced_results
        
        return final_results
    
    def generate_nutrition_csv(self, daily_menu: Dict[str, Dict[str, str]]) -> str:
        """Generate CSV file with nutrition data for all menu items"""
        if not self.extract_nutrition:
            return None
        
        all_nutrition_data = []
        
        for meal_name, items in daily_menu.items():
            if not items:
                continue
                
            if self.debug:
                print(f"Extracting nutrition data for {meal_name}...")
            
            # Process all items for comprehensive nutrition data
            for food_name, url in items.items():
                if url and url != '#':
                    try:
                        nutrition_data = self.nutrition_extractor.extract_nutrition_data(url)
                        nutrition_data['meal'] = meal_name
                        nutrition_data['campus'] = self.campus_key
                        all_nutrition_data.append(nutrition_data)
                        
                        if self.debug:
                            print(f"  Successfully extracted nutrition for {food_name}")
                        
                        # Add small delay to be respectful to the server
                        time.sleep(0.1)
                        
                    except Exception as e:
                        if self.debug:
                            print(f"Error extracting nutrition for {food_name}: {e}")
                        continue
        
        if not all_nutrition_data:
            if self.debug:
                print("No nutrition data extracted, returning None")
            return None
        
        # Generate CSV filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nutrition_data_{self.campus_key}_{timestamp}.csv"
        filepath = os.path.join('nutrition_data', filename)
        
        # Create directory if it doesn't exist
        os.makedirs('nutrition_data', exist_ok=True)
        
        # Write CSV file
        fieldnames = [
            'food_name', 'meal', 'campus', 'serving_size', 'calories', 'calories_from_fat',
            'total_fat_g', 'total_fat_dv', 'saturated_fat_g', 'saturated_fat_dv', 'trans_fat_g',
            'cholesterol_mg', 'sodium_mg', 'sodium_dv', 'total_carb_g', 'total_carb_dv',
            'dietary_fiber_g', 'dietary_fiber_dv', 'sugars_g', 'added_sugars_g',
            'protein_g', 'protein_dv', 'vitamin_d_mcg', 'calcium_mg', 'iron_mg', 'potassium_mg',
            'ingredients', 'extraction_timestamp', 'url'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_nutrition_data)
        
        if self.debug:
            print(f"Generated nutrition CSV: {filepath} with {len(all_nutrition_data)} items")
        
        return filepath
    
    def enhance_recommendations_with_nutrition(self, recommendations: Dict[str, List[Tuple[str, int, str, str]]], daily_menu: Dict[str, Dict[str, str]]) -> Dict[str, List[Tuple[str, int, str, str, Dict]]]:
        """Enhance recommendations with nutrition data for display"""
        enhanced_results = {}
        
        for meal, items in recommendations.items():
            if meal == '_csv_path':
                enhanced_results[meal] = items
                continue
                
            enhanced_items = []
            for food_name, score, reason, url in items:
                nutrition_data = None
                
                # Try to get nutrition data from the daily menu
                if url and url != '#':
                    try:
                        nutrition_data = self.nutrition_extractor.extract_nutrition_data(url)
                        # Add a small delay to be respectful to the server
                        time.sleep(0.2)
                    except Exception as e:
                        if self.debug:
                            print(f"Error extracting nutrition for {food_name}: {e}")
                        nutrition_data = self.nutrition_extractor._get_empty_nutrition_data(url)
                else:
                    # Create empty nutrition data if no URL
                    nutrition_data = self.nutrition_extractor._get_empty_nutrition_data('#')
                
                # Add nutrition data as the 5th element in the tuple
                enhanced_items.append((food_name, score, reason, url, nutrition_data))
            
            enhanced_results[meal] = enhanced_items
        
        return enhanced_results

    def analyze_menu_with_gemini_csv(self, csv_data: List[Dict[str, any]]) -> Dict[str, List[Tuple[str, int, str, str]]]:
        """Analyze menu using complete CSV nutrition data with AI"""
        exclusions = []
        if self.exclude_beef: exclusions.append("No beef.")
        if self.exclude_pork: exclusions.append("No pork.")
        if self.vegetarian: exclusions.append("Only vegetarian items (includes eggs).")
        if self.vegan: exclusions.append("Only vegan items (no animal products including eggs and dairy).")
        restrictions_text = " ".join(exclusions) if exclusions else "None."

        priority_instruction = ("prioritize PROTEIN content" if self.prioritize_protein else "prioritize a BALANCE of high protein and healthy preparation")
        
        # Group CSV data by meal
        meal_data = {}
        for item in csv_data:
            meal = item.get('meal', 'Unknown')
            if meal not in meal_data:
                meal_data[meal] = []
            meal_data[meal].append(item)
        
        # Create a comprehensive prompt with all nutrition data
        prompt = f"""
        You are a nutrition expert analyzing college dining menu items with complete macronutrient data. Select the top 5 healthiest options for EACH meal.

        GOAL: {priority_instruction}
        DIETARY RESTRICTIONS: {restrictions_text}

        SCORING CRITERIA (0-100 points) - Use actual nutrition data:
        - High protein (20g+): +25-30 points
        - Moderate protein (10-19g): +15-25 points
        - Low protein (<10g): +5-15 points
        - High fiber (5g+): +15-20 points
        - Moderate fiber (2-4g): +8-15 points
        - Low sodium (<300mg): +15-20 points
        - Moderate sodium (300-600mg): +5-15 points
        - High sodium (600mg+): -10-20 points
        - Healthy fats (mono/polyunsaturated): +10-15 points
        - Saturated fats: -5-15 points
        - Trans fats: -20-30 points
        - Added sugars (0-5g): +5-10 points
        - Added sugars (5-15g): 0 points
        - Added sugars (15-25g): -10-15 points
        - Added sugars (25g+): -20-30 points
        - Calorie density (calories per serving): Lower is better
        - Whole food ingredients: +5-15 points
        - Highly processed ingredients: -5-15 points
        - Overall nutritional balance: +10-25 points

        PRIORITY FACTORS:
        1. Protein content and quality
        2. Fiber content
        3. Sodium levels (lower is better)
        4. Added sugar content (lower is better)
        5. Healthy fat profile
        6. Ingredient quality (whole foods preferred)
        7. Calorie density
        8. Overall nutritional completeness

        INGREDIENT QUALITY ASSESSMENT:
        - Give additional points for items made primarily from whole-food ingredients (e.g., fresh vegetables, lean meats, whole grains, natural dairy)
        - Penalize items with long lists of additives, preservatives, or highly-processed ingredients
        - Consider the ingredient list when scoring - prioritize natural, minimally processed foods

        Return ONLY a valid JSON object with this exact structure:
        {{
            "Breakfast": [{{"food_name": "Item Name", "score": 85, "reasoning": "High protein (25g), low sodium (200mg), good fiber (4g), low added sugar (3g)"}}],
            "Lunch": [{{"food_name": "Item Name", "score": 90, "reasoning": "Excellent protein (30g), low sodium (150mg), high fiber (6g), whole food ingredients"}}],
            "Dinner": [{{"food_name": "Item Name", "score": 75, "reasoning": "Good protein (18g), moderate sodium (400mg), moderate added sugar (12g)"}}]
        }}

        Complete Nutrition Data:
        {json.dumps(meal_data, indent=2)}
        """
        
        try:
            if self.debug: print("🤖 Using AI (Gemini) analysis for detailed nutrition scoring...")
            response = self.session.post(self.gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
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
                    # Find the corresponding URL from the original data
                    url = '#'
                    for item in csv_data:
                        if item.get('food_name') == food_name and item.get('meal') == meal:
                            url = item.get('url', '#')
                            break
                    meal_results.append((food_name, item_info.get("score"), item_info.get("reasoning"), url))
                meal_results.sort(key=lambda x: x[1], reverse=True)
                results[meal] = meal_results
            
            # Recalculate health scores for top items using local analysis for consistency
            if self.debug: print("🔄 Recalculating health scores for top items using local analysis...")
            recalculated_results = self._recalculate_top_items_scores(results, csv_data)
            if self.debug: print("✅ AI analysis completed successfully!")
            return recalculated_results
        except Exception as e:
            if self.debug: print(f"❌ AI analysis failed: {e}. Falling back to local analysis.")
            return self.analyze_menu_local_from_csv(csv_data)

    def _recalculate_top_items_scores(self, ai_results: Dict[str, List[Tuple[str, int, str, str]]], csv_data: List[Dict[str, any]]) -> Dict[str, List[Tuple[str, int, str, str]]]:
        """Recalculate health scores for top AI-selected items using local analysis for consistency"""
        recalculated_results = {}
        
        for meal, items in ai_results.items():
            if meal == '_csv_path':
                recalculated_results[meal] = items
                continue
                
            recalculated_items = []
            for food_name, ai_score, ai_reasoning, url in items:
                # Find the nutrition data for this item
                nutrition_data = None
                for item in csv_data:
                    if item.get('food_name') == food_name and item.get('meal') == meal:
                        nutrition_data = item
                        break
                
                if nutrition_data:
                    # Recalculate using local analysis
                    local_score, local_reasoning = self.calculate_health_score_from_nutrition(nutrition_data)
                    recalculated_items.append((food_name, local_score, local_reasoning, url))
                    if self.debug:
                        print(f"  {food_name}: AI={ai_score} → Local={local_score}")
                else:
                    # Keep original if no nutrition data found
                    recalculated_items.append((food_name, ai_score, ai_reasoning, url))
                    if self.debug:
                        print(f"  {food_name}: No nutrition data, keeping AI score={ai_score}")
            
            # Sort by recalculated scores
            recalculated_items.sort(key=lambda x: x[1], reverse=True)
            recalculated_results[meal] = recalculated_items
        
        return recalculated_results

    def analyze_menu_local_from_csv(self, csv_data: List[Dict[str, any]]) -> Dict[str, List[Tuple[str, int, str, str]]]:
        """Fallback local analysis using CSV nutrition data"""
        if self.debug: print("🧮 Using local analysis for detailed nutrition scoring...")
        # Group by meal
        meal_data = {}
        for item in csv_data:
            meal = item.get('meal', 'Unknown')
            if meal not in meal_data:
                meal_data[meal] = []
            meal_data[meal].append(item)
        
        if self.debug:
            print(f"Grouped nutrition data by meal: {list(meal_data.keys())}")
            for meal, items in meal_data.items():
                print(f"  {meal}: {len(items)} items")
        
        # Find items that are unique to each meal (not served at other meals)
        meal_unique_items = {}
        for meal, items in meal_data.items():
            unique_items = []
            for item in items:
                food_name = item.get('food_name', 'Unknown')
                # Check if this item appears in other meals
                appears_in_other_meals = False
                for other_meal, other_items in meal_data.items():
                    if other_meal != meal:
                        for other_item in other_items:
                            if other_item.get('food_name', 'Unknown') == food_name:
                                appears_in_other_meals = True
                                break
                        if appears_in_other_meals:
                            break
                
                if not appears_in_other_meals:
                    unique_items.append(item)
            
            meal_unique_items[meal] = unique_items
            if self.debug:
                print(f"  {meal} unique items: {len(unique_items)}")
        
        results = {}
        for meal, items in meal_data.items():
            analyzed_items = []
            
            # First, prioritize unique items for this meal
            unique_items = meal_unique_items.get(meal, [])
            for item in unique_items:
                score, reasoning = self.calculate_health_score_from_nutrition(item)
                analyzed_items.append((item.get('food_name', 'Unknown'), score, reasoning, item.get('url', '#')))
            
            # Then add other items if we don't have enough unique items
            if len(analyzed_items) < 5:
                for item in items:
                    if item not in unique_items:
                        score, reasoning = self.calculate_health_score_from_nutrition(item)
                        analyzed_items.append((item.get('food_name', 'Unknown'), score, reasoning, item.get('url', '#')))
            
            analyzed_items.sort(key=lambda x: x[1], reverse=True)
            # Take only top 5 items per meal
            results[meal] = analyzed_items[:5]
        
        if self.debug: print("✅ Local analysis completed successfully!")
        return results

    def run_quick_analysis(self) -> Dict[str, List[Tuple[str, int, str, str]]]:
        """Quick analysis using only food names with AI"""
        if self.debug: 
            print(f"Running quick analysis for campus: {self.campus_key}")
        
        form_options = self.get_initial_form_data()
        if not form_options:
            return {"error": "Could not fetch menu data"}
        
        # Use the first available date (default date the site loads into)
        date_options = form_options.get('date', {})
        if not date_options:
            return {"error": "No date options available"}
        
        # Get the first available date
        first_date_key = list(date_options.keys())[0]
        date_value = date_options[first_date_key]
        
        if self.debug:
            print(f"Using date: {first_date_key} -> {date_value}")
        
        # Get campus value
        campus_options = form_options.get('campus', {})
        campus_value, campus_name_found = self.find_campus_value(campus_options)
        
        if not campus_value:
            return {"error": f"Could not find campus: {self.campus_key}"}
        
        # Get menu data by fetching each meal
        daily_menu = {}
        meal_options = form_options.get('meal', {})
        
        for meal_name in ["Breakfast", "Lunch", "Dinner"]:
            meal_key = meal_name.lower()
            meal_value = meal_options.get(meal_key)
            
            if not meal_value:
                if self.debug: print(f"Could not find form value for '{meal_name}'. Skipping.")
                continue

            try:
                form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
                if self.debug: print(f"Fetching menu for {meal_name} with data: {form_data}")
                response = self.session.post(self.base_url, data=form_data)
                response.raise_for_status()
                meal_soup = BeautifulSoup(response.content, 'html.parser')
                items = self.extract_items_from_meal_page(meal_soup)
                if items:
                    daily_menu[meal_name] = items
                    if self.debug: print(f"Found {len(items)} items for {meal_name}.")
                else:
                    if self.debug: print(f"No items found for {meal_name}.")
            except Exception as e:
                if self.debug: print(f"Error fetching {meal_name}: {e}")
                continue
        
        if not daily_menu:
            return {"error": "Could not fetch menu data"}
        
        # Prepare food names for AI analysis
        meal_data = {}
        for meal_name, items in daily_menu.items():
            meal_data[meal_name] = []
            for item in items:
                if isinstance(item, dict):
                    meal_data[meal_name].append(item.get('food_name', 'Unknown'))
                else:
                    # If item is a string, use it directly
                    meal_data[meal_name].append(str(item))
        
        # AI analysis of food names only
        exclusions = []
        if self.exclude_beef: exclusions.append("No beef.")
        if self.exclude_pork: exclusions.append("No pork.")
        if self.vegetarian: exclusions.append("Only vegetarian items (includes eggs).")
        if self.vegan: exclusions.append("Only vegan items (no animal products including eggs and dairy).")
        restrictions_text = " ".join(exclusions) if exclusions else "None."

        priority_instruction = ("prioritize PROTEIN content" if self.prioritize_protein else "prioritize a BALANCE of healthy options")
        
        prompt = f"""
        You are a nutrition expert analyzing a college dining menu. Select the top 5 healthiest options for EACH meal based on food names only.

        GOAL: {priority_instruction}
        DIETARY RESTRICTIONS: {restrictions_text}

        SCORING CRITERIA (0-100 points):
        - High protein foods (eggs, chicken, fish, beans, nuts): +20-30 points
        - Whole grains (brown rice, whole wheat, quinoa): +15-25 points
        - Fresh vegetables and fruits: +15-25 points
        - Healthy cooking methods (grilled, baked, steamed, roasted): +10-20 points
        - Lean proteins (chicken breast, fish, turkey): +15-25 points
        - Processed/fried foods: -20-40 points
        - High sugar items (desserts, sugary drinks): -15-30 points
        - Refined carbs (white bread, white rice): -10-20 points

        EXAMPLES OF HIGH SCORES (80-100):
        - Grilled Chicken Breast, Scrambled Eggs, Fresh Fruit Salad
        - Baked Salmon, Quinoa Bowl, Steamed Broccoli
        - Greek Yogurt with Berries, Whole Grain Toast

        EXAMPLES OF LOW SCORES (0-40):
        - French Fries, Fried Chicken, Donuts
        - White Bread, Sugary Cereal, Processed Meats

        Return ONLY a valid JSON object with this exact structure:
        {{
            "Breakfast": [{{"food_name": "Item Name", "score": 85, "reasoning": "High protein, whole grains"}}],
            "Lunch": [{{"food_name": "Item Name", "score": 90, "reasoning": "Lean protein, vegetables"}}],
            "Dinner": [{{"food_name": "Item Name", "score": 75, "reasoning": "Balanced nutrition"}}]
        }}

        Menu Items by Meal:
        {json.dumps(meal_data, indent=2)}
        """
        
        if not hasattr(self, 'gemini_url') or not self.gemini_url:
            if self.debug: print("No Gemini API key available. Using local analysis.")
            return self.analyze_menu_local(daily_menu)
        
        try:
            response = self.session.post(self.gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
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
                    url = '#'
                    # Find the item in daily_menu to get the URL
                    for meal_name, items in daily_menu.items():
                        for item in items:
                            if isinstance(item, dict) and item.get('food_name') == food_name:
                                url = item.get('url', '#')
                                break
                    meal_results.append((food_name, item_info.get("score"), item_info.get("reasoning"), url))
                meal_results.sort(key=lambda x: x[1], reverse=True)
                results[meal] = meal_results[:5]  # Limit to top 5 items
            
            return results
        except Exception as e:
            if self.debug: print(f"Quick analysis failed: {e}. Falling back to local analysis.")
            return self.analyze_menu_local(daily_menu)

    def analyze_menu_with_gemini(self, daily_menu: Dict[str, Dict[str, str]]) -> Dict[str, List[Tuple[str, int, str, str]]]:
        exclusions = []
        if self.exclude_beef: exclusions.append("No beef.")
        if self.exclude_pork: exclusions.append("No pork.")
        if self.vegetarian: exclusions.append("Only vegetarian items (includes eggs).")
        if self.vegan: exclusions.append("Only vegan items (no animal products including eggs and dairy).")
        restrictions_text = " ".join(exclusions) if exclusions else "None."

        priority_instruction = ("prioritize PROTEIN content" if self.prioritize_protein else "prioritize a BALANCE of high protein and healthy preparation")
        
        menu_for_prompt = {meal: list(items.keys()) for meal, items in daily_menu.items()}

        # Ask for more items (e.g., 15) to allow for filtering down to 5.
        prompt = f"""
        Analyze the menu below. Your goal is to {priority_instruction}. My restrictions are: {restrictions_text}
        For EACH meal, identify the top 15 options.
        Return your response as a single, valid JSON object with keys "Breakfast", "Lunch", "Dinner". Each value should be a list of objects, each with "food_name", "score" (0-100), and "reasoning".
        Menu: {json.dumps(menu_for_prompt, indent=2)}
        """
        try:
            response = self.session.post(self.gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
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
            if self.debug: print(f"Gemini analysis failed: {e}. Falling back to local analysis.")
            return self.analyze_menu_local(daily_menu)

    def apply_hard_filters(self, food_items: List[Tuple[str, int, str, str]]) -> List[Tuple[str, int, str, str]]:
        if not (self.exclude_beef or self.exclude_pork or self.vegetarian or self.vegan): 
            return food_items
        filtered_list = []
        for food, score, reason, url in food_items:
            item_lower = food.lower()
            excluded = False
            if self.exclude_beef and "beef" in item_lower: excluded = True
            if self.exclude_pork and any(p in item_lower for p in ["pork", "bacon", "sausage", "ham"]): excluded = True
            if self.vegetarian and any(m in item_lower for m in ["beef", "pork", "chicken", "turkey", "fish", "salmon", "tuna", "bacon", "sausage", "ham"]): excluded = True
            if self.vegan and any(m in item_lower for m in ["beef", "pork", "chicken", "turkey", "fish", "salmon", "tuna", "bacon", "sausage", "ham", "egg", "eggs", "dairy", "milk", "cheese", "butter", "yogurt"]): excluded = True
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
                analyzed_items = self.analyze_food_health_local_list(items)
                analyzed_items.sort(key=lambda x: x[1], reverse=True)
                results[meal] = analyzed_items
        return results

    def analyze_food_health_local_list(self, food_items: Dict[str, str]) -> List[Tuple[str, int, str, str]]:
        health_scores = []
        
        for item, url in food_items.items():
            # First, try to extract nutrition data for accurate scoring
            nutrition_data = None
            if url and url != '#':
                try:
                    nutrition_data = self.nutrition_extractor.extract_nutrition_data(url)
                    # Add a small delay to be respectful to the server
                    time.sleep(0.1)
                except Exception as e:
                    if self.debug:
                        print(f"Error extracting nutrition for {item}: {e}")
                    nutrition_data = self.nutrition_extractor._get_empty_nutrition_data(url)
            else:
                nutrition_data = self.nutrition_extractor._get_empty_nutrition_data('#')
            
            # Calculate health score based on macronutrient data
            if nutrition_data and nutrition_data.get('calories', 0) > 0:
                score, reasoning = self.calculate_health_score_from_nutrition(nutrition_data)
            else:
                # Fallback to keyword-based scoring if no nutrition data
                score, reasoning = self._fallback_keyword_scoring(item)
            
            health_scores.append((item, score, reasoning, url))
        
        return health_scores
    
    def calculate_health_score_from_nutrition(self, nutrition_data: Dict[str, any]) -> Tuple[int, str]:
        """Calculate health score based on actual macronutrient data"""
        calories = nutrition_data.get('calories', 0)
        protein = nutrition_data.get('protein_g', 0)
        total_fat = nutrition_data.get('total_fat_g', 0)
        saturated_fat = nutrition_data.get('saturated_fat_g', 0)
        carbs = nutrition_data.get('total_carb_g', 0)
        fiber = nutrition_data.get('dietary_fiber_g', 0)
        sodium = nutrition_data.get('sodium_mg', 0)
        
        if calories == 0:
            return 50, "No nutrition data available"
        
        score = 50  # Base score
        reasoning_parts = []
        
        # Protein scoring (0-30 points)
        protein_per_calorie = (protein * 4) / calories if calories > 0 else 0
        if protein_per_calorie >= 0.25:  # 25%+ calories from protein
            score += 30
            reasoning_parts.append("Excellent protein density")
        elif protein_per_calorie >= 0.20:  # 20%+ calories from protein
            score += 20
            reasoning_parts.append("Good protein density")
        elif protein_per_calorie >= 0.15:  # 15%+ calories from protein
            score += 10
            reasoning_parts.append("Moderate protein density")
        else:
            score -= 10
            reasoning_parts.append("Low protein density")
        
        # Fat quality scoring (0-20 points)
        if total_fat > 0:
            saturated_ratio = saturated_fat / total_fat
            if saturated_ratio <= 0.3:  # 30% or less saturated fat
                score += 20
                reasoning_parts.append("Healthy fat profile")
            elif saturated_ratio <= 0.5:  # 50% or less saturated fat
                score += 10
                reasoning_parts.append("Moderate fat profile")
            else:
                score -= 10
                reasoning_parts.append("High saturated fat")
        
        # Fiber scoring (0-15 points) - using absolute grams
        if fiber >= 5:
            score += 15
            reasoning_parts.append("High fiber content")
        elif fiber >= 3:
            score += 10
            reasoning_parts.append("Good fiber content")
        elif fiber >= 1:
            score += 5
            reasoning_parts.append("Moderate fiber content")
        else:
            score -= 5
            reasoning_parts.append("Low fiber content")
        
        # Sodium scoring (0-15 points)
        sodium_per_calorie = sodium / calories if calories > 0 else 0
        if sodium_per_calorie <= 1.0:  # 1mg per calorie or less
            score += 15
            reasoning_parts.append("Low sodium")
        elif sodium_per_calorie <= 2.0:  # 2mg per calorie or less
            score += 10
            reasoning_parts.append("Moderate sodium")
        elif sodium_per_calorie <= 3.0:  # 3mg per calorie or less
            score += 5
            reasoning_parts.append("Acceptable sodium")
        else:
            score -= 10
            reasoning_parts.append("High sodium")
        
        # Sugar scoring (0-15 points penalty for high sugar)
        added_sugars = nutrition_data.get('added_sugars_g', 0)
        if added_sugars > 0:
            sugar_percentage = (added_sugars * 4) / calories if calories > 0 else 0
            if sugar_percentage >= 0.25:  # 25%+ calories from added sugar
                score -= 15
                reasoning_parts.append("Very high added sugar")
            elif sugar_percentage >= 0.15:  # 15%+ calories from added sugar
                score -= 10
                reasoning_parts.append("High added sugar")
            elif sugar_percentage >= 0.10:  # 10%+ calories from added sugar
                score -= 5
                reasoning_parts.append("Moderate added sugar")
            else:
                score += 5
                reasoning_parts.append("Low added sugar")
        
        # Calorie density bonus/penalty (0-10 points)
        if calories <= 200:
            score += 10
            reasoning_parts.append("Low calorie density")
        elif calories <= 400:
            score += 5
            reasoning_parts.append("Moderate calorie density")
        elif calories >= 800:
            score -= 10
            reasoning_parts.append("High calorie density")
        
        # Protein prioritization bonus
        if self.prioritize_protein and protein_per_calorie >= 0.20:
            score += 10
            reasoning_parts.append("High protein priority")
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        return score, ", ".join(reasoning_parts) if reasoning_parts else "Standard nutrition profile"
    
    def _fallback_keyword_scoring(self, item: str) -> Tuple[int, str]:
        """Fallback keyword-based scoring when nutrition data is unavailable"""
        protein_keywords = {'excellent': ['chicken', 'salmon', 'tuna', 'turkey'], 'good': ['beef', 'eggs', 'tofu', 'beans'], 'moderate': ['cheese', 'yogurt']}
        healthy_prep = {'excellent': ['grilled', 'baked', 'steamed'], 'good': ['sautéed'], 'poor': ['fried', 'creamy', 'battered']}

        protein_weights = {'excellent': 40, 'good': 30, 'moderate': 15} if self.prioritize_protein else {'excellent': 30, 'good': 20, 'moderate': 10}
        prep_weights = {'excellent': 10, 'good': 5, 'poor': -15} if self.prioritize_protein else {'excellent': 20, 'good': 10, 'poor': -25}

        item_lower = item.lower()
        score, reasoning = 50, []
        
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
        
        score = max(0, min(100, score))
        return score, ", ".join(reasoning) or "Standard option (keyword-based)"

# --- Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        print(f"Received request with data: {data}")
        
        # Simple validation
        campus = data.get('campus', 'altoona-port-sky')
        vegetarian = data.get('vegetarian', False)
        vegan = data.get('vegan', False)
        exclude_beef = data.get('exclude_beef', False)
        exclude_pork = data.get('exclude_pork', False)
        prioritize_protein = data.get('prioritize_protein', False)
        analysis_type = data.get('analysis_type', 'detailed')
        extract_nutrition = analysis_type == 'detailed'  # Only extract nutrition for detailed analysis
        
        # Validate that vegan and vegetarian aren't both selected
        if vegan and vegetarian:
            return jsonify({"error": "Cannot be both vegan and vegetarian"}), 400
        
        # Get API key from environment
        api_key = os.getenv('GEMINI_API_KEY')

        analyzer = MenuAnalyzer(
            campus_key=campus,
            gemini_api_key=api_key,
            exclude_beef=exclude_beef,
            exclude_pork=exclude_pork,
            vegetarian=vegetarian,
            vegan=vegan,
            prioritize_protein=prioritize_protein,
            extract_nutrition=extract_nutrition,
            debug=True
        )
        
        # Choose analysis method based on type
        if analysis_type == 'quick':
            recommendations = analyzer.run_quick_analysis()
        else:
            recommendations = analyzer.run_analysis()
        print(f"Returning recommendations: {recommendations}")
        
        return jsonify(recommendations)
    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/api/extract-nutrition', methods=['POST'])
def extract_nutrition():
    """Extract nutrition data for all menu items and generate CSV"""
    try:
        data = request.json
        campus = data.get('campus', 'altoona-port-sky')
        
        print(f"Extracting nutrition data for campus: {campus}")
        
        # Get API key from environment
        api_key = os.getenv('GEMINI_API_KEY')
        
        analyzer = MenuAnalyzer(
            campus_key=campus,
            gemini_api_key=api_key,
            extract_nutrition=True,
            debug=True
        )
        
        # Get the raw menu data first
        form_options = analyzer.get_initial_form_data()
        if not form_options:
            return jsonify({"error": "Could not fetch menu data"}), 500
        
        campus_options = form_options.get('campus', {})
        campus_value, campus_name_found = analyzer.find_campus_value(campus_options)
        
        if not campus_value:
            return jsonify({"error": f"Could not find campus: {campus}"}), 400
        
        # Use the first available date (default date the site loads into)
        date_options = form_options.get('date', {})
        if not date_options:
            return jsonify({"error": "No menu dates available"}), 400
        
        first_date_key = list(date_options.keys())[0]
        date_value = date_options[first_date_key]
        
        # Get all menu items for all meals
        daily_menu = {}
        meal_options = form_options.get('meal', {})
        
        for meal_name in ["Breakfast", "Lunch", "Dinner"]:
            meal_key = meal_name.lower()
            meal_value = meal_options.get(meal_key)
            
            if meal_value:
                try:
                    form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
                    response = analyzer.session.post(analyzer.base_url, data=form_data)
                    response.raise_for_status()
                    meal_soup = BeautifulSoup(response.content, 'html.parser')
                    items = analyzer.extract_items_from_meal_page(meal_soup)
                    daily_menu[meal_name] = items
                    time.sleep(0.2)
                except Exception as e:
                    print(f"Error fetching {meal_name} menu: {e}")
                    daily_menu[meal_name] = {}
        
        # Generate nutrition CSV
        try:
            csv_path = analyzer.generate_nutrition_csv(daily_menu)
            
            if csv_path:
                return jsonify({
                    "message": "Nutrition data extracted successfully",
                    "csv_path": csv_path,
                    "campus": campus,
                    "total_items": sum(len(items) for items in daily_menu.values())
                })
            else:
                return jsonify({"error": "No nutrition data could be extracted"}), 500
        except Exception as e:
            print(f"Error generating CSV: {e}")
            return jsonify({"error": f"Error generating CSV: {str(e)}"}), 500
            
    except Exception as e:
        print(f"[NUTRITION EXTRACTION ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred during nutrition extraction."}), 500

@app.route('/api/download-csv/<filename>')
def download_csv(filename):
    """Download a generated CSV file"""
    try:
        # Security check - only allow CSV files from nutrition_data directory
        if not filename.endswith('.csv') or '..' in filename or '/' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        file_path = os.path.join('nutrition_data', filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        return send_from_directory('nutrition_data', filename, as_attachment=True)
        
    except Exception as e:
        print(f"[DOWNLOAD ERROR] {e}")
        return jsonify({"error": "Error downloading file"}), 500

@app.route('/api/list-csv-files')
def list_csv_files():
    """List all available CSV files"""
    try:
        csv_files = []
        nutrition_dir = 'nutrition_data'
        
        if os.path.exists(nutrition_dir):
            for filename in os.listdir(nutrition_dir):
                if filename.endswith('.csv'):
                    file_path = os.path.join(nutrition_dir, filename)
                    stat = os.stat(file_path)
                    csv_files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        # Sort by creation time (newest first)
        csv_files.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({"csv_files": csv_files})
        
    except Exception as e:
        print(f"[LIST CSV ERROR] {e}")
        return jsonify({"error": "Error listing CSV files"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

