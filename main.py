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

# --- Internal Nutrition Cache Manager ---
class NutritionCache:
    """Manages an internal CSV cache for nutritional data to reduce redundant scraping."""
    def __init__(self, cache_dir='nutrition_cache', debug=False):
        self.debug = debug
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(self.cache_dir, 'nutrition_data.csv')
        self.fieldnames = ['food_name', 'calories', 'protein', 'fat', 'saturated_fat', 'carbs', 'fiber', 'sugar', 'sodium', 'cholesterol']
        self._ensure_cache_exists()
        self.cache_df = self._load_cache()

    def _ensure_cache_exists(self):
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
            if not os.path.exists(self.cache_file):
                with open(self.cache_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    writer.writeheader()
                if self.debug:
                    print(f"Created new cache file at {self.cache_file}")
        except Exception as e:
            if self.debug:
                print(f"Error ensuring cache exists: {e}")

    def _load_cache(self):
        try:
            return pd.read_csv(self.cache_file).set_index('food_name')
        except (pd.errors.EmptyDataError, FileNotFoundError):
            # Return an empty DataFrame with the correct structure if file is empty or not found
            return pd.DataFrame(columns=self.fieldnames[1:]).set_index(pd.Index([], name='food_name'))
        except Exception as e:
            if self.debug:
                print(f"Error loading nutrition cache: {e}")
            return pd.DataFrame() # Fallback to empty df on other errors

    def get(self, food_name: str) -> Optional[Dict[str, float]]:
        """Retrieves nutritional data for a food item from the cache."""
        # Normalize index and food_name for case-insensitive matching
        if not self.cache_df.empty and food_name.lower() in self.cache_df.index.str.lower():
            if self.debug:
                print(f"CACHE HIT for: {food_name}")
            # Find the actual index key to use for loc
            matching_index = self.cache_df.index[self.cache_df.index.str.lower() == food_name.lower()][0]
            return self.cache_df.loc[matching_index].to_dict()
        if self.debug:
            print(f"CACHE MISS for: {food_name}")
        return None

    def put(self, food_name: str, nutrition_data: Dict[str, float]):
        """Saves nutritional data for a food item to the cache."""
        try:
            # Avoid adding duplicates
            if not self.cache_df.empty and food_name.lower() in self.cache_df.index.str.lower():
                return

            if self.debug:
                print(f"Caching nutrition data for: {food_name}")

            # Append to the CSV file
            with open(self.cache_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                row = {'food_name': food_name}
                # Ensure all fields are present, defaulting to None or a sensible default
                for field in self.fieldnames[1:]:
                    row[field] = nutrition_data.get(field)
                writer.writerow(row)

            # Update the in-memory DataFrame
            new_data_df = pd.DataFrame([row]).set_index('food_name')
            self.cache_df = pd.concat([self.cache_df, new_data_df])

        except Exception as e:
            if self.debug:
                print(f"Error caching data for {food_name}: {e}")

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
            
            # Look for nutrition facts table or similar structure
            nutrition_tables = soup.find_all('table', class_=re.compile(r'nutrition|facts', re.I))
            
            for table in nutrition_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value_text = cells[1].get_text(strip=True)
                        
                        # Extract numeric values
                        value_match = re.search(r'(\d+\.?\d*)', value_text)
                        if value_match:
                            value = float(value_match.group(1))
                            
                            # Map common nutrition labels
                            if 'calories' in label:
                                nutrition_data['calories'] = value
                            elif 'protein' in label:
                                nutrition_data['protein'] = value
                            elif 'fat' in label and 'total' in label:
                                nutrition_data['fat'] = value
                            elif 'saturated' in label and 'fat' in label:
                                nutrition_data['saturated_fat'] = value
                            elif 'carbohydrate' in label or 'carbs' in label:
                                nutrition_data['carbs'] = value
                            elif 'fiber' in label:
                                nutrition_data['fiber'] = value
                            elif 'sugar' in label:
                                nutrition_data['sugar'] = value
                            elif 'sodium' in label:
                                nutrition_data['sodium'] = value
                            elif 'cholesterol' in label:
                                nutrition_data['cholesterol'] = value
            
            # If no structured data found, try to extract from text
            if not nutrition_data:
                page_text = soup.get_text().lower()
                
                # Look for common nutrition patterns in text
                patterns = {
                    'calories': r'(\d+)\s*calories?',
                    'protein': r'(\d+\.?\d*)\s*g\s*protein',
                    'fat': r'(\d+\.?\d*)\s*g\s*fat',
                    'carbs': r'(\d+\.?\d*)\s*g\s*(?:carbs|carbohydrates?)',
                    'fiber': r'(\d+\.?\d*)\s*g\s*fiber',
                    'sodium': r'(\d+\.?\d*)\s*mg\s*sodium'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, page_text)
                    if match:
                        nutrition_data[key] = float(match.group(1))
            
            if self.debug and nutrition_data:
                print(f"Extracted nutrition data: {nutrition_data}")
            
            return nutrition_data
            
        except Exception as e:
            if self.debug:
                print(f"Error extracting nutrition data from {url}: {e}")
            return {}

# --- CSV Export Manager (For User Downloads) ---
class CSVExportManager:
    def __init__(self, debug=False):
        self.debug = debug
        self.export_dir = "exports"
        os.makedirs(self.export_dir, exist_ok=True)

    def save_nutritional_data(self, food_items: Dict[str, Dict[str, float]], meal: str, campus: str):
        """Save nutritional data to a user-downloadable CSV file."""
        if not food_items:
            return None
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
                    'calories': nutrition.get('calories'),
                    'protein': nutrition.get('protein'),
                    'fat': nutrition.get('fat'),
                    'saturated_fat': nutrition.get('saturated_fat'),
                    'carbs': nutrition.get('carbs'),
                    'fiber': nutrition.get('fiber'),
                    'sugar': nutrition.get('sugar'),
                    'sodium': nutrition.get('sodium'),
                    'cholesterol': nutrition.get('cholesterol')
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
                print(f"Saved user export CSV to {filepath}")
            return filepath
        except Exception as e:
            if self.debug:
                print(f"Error saving user export CSV: {e}")
            return None
    
    def get_nutritional_insights(self, campus: str) -> Dict[str, any]:
        """Analyze saved nutritional data to provide insights for the user."""
        try:
            files = [f for f in os.listdir(self.export_dir) if f.startswith(campus) and f.endswith("_nutrition.csv")]
            if not files:
                return {"error": "No nutritional data found for this campus yet."}
            
            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(self.export_dir, x)))
            df = pd.read_csv(os.path.join(self.export_dir, latest_file))
            
            insights = {
                "total_foods_analyzed": len(df),
                "average_calories": round(df['calories'].mean(), 2) if len(df) > 0 else 0,
                "average_protein": round(df['protein'].mean(), 2) if len(df) > 0 else 0,
                "highest_protein_foods": df.nlargest(3, 'protein')[['food_name', 'protein']].to_dict('records') if len(df) > 0 else []
            }
            return insights
        except Exception as e:
            if self.debug:
                print(f"Error analyzing nutritional insights: {e}")
            return {"error": f"Failed to analyze nutritional data: {e}"}

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
        
        self.nutrition_extractor = NutritionalDataExtractor(debug=debug)
        self.csv_manager = CSVExportManager(debug=debug)
        self.nutrition_cache = NutritionCache(debug=debug)
        
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        elif self.debug:
            print("No Gemini API key provided. Using local keyword-based analysis.")

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
                        options[name][option.get_text(strip=True).lower()] = option.get('value', '').strip()
            return options
        except requests.RequestException as e:
            if self.debug:
                print(f"Error fetching initial page: {e}")
            return None

    def find_campus_value(self, campus_options: Dict[str, str]) -> Optional[str]:
        # This logic remains as per user request not to modify it.
        search_terms = {
            'altoona-port-sky': ['altoona', 'port sky'], 'beaver-brodhead': ['beaver', 'brodhead'],
            'behrend-brunos': ['behrend', 'bruno'], 'behrend-dobbins': ['behrend', 'dobbins'],
            'berks-tullys': ['berks', 'tully'], 'brandywine-blue-apple': ['brandywine', 'blue apple'],
            'greater-allegheny-cafe-metro': ['greater allegheny', 'cafe metro'], 'harrisburg-stacks': ['harrisburg', 'stacks'],
            'harrisburg-outpost': ['harrisburg', 'outpost'], 'hazleton-highacres': ['hazleton', 'highacres'],
            'mont-alto-mill': ['mont alto', 'mill'], 'up-east-findlay': ['east', 'findlay'],
            'up-north-warnock': ['north', 'warnock'], 'up-pollock': ['pollock'],
            'up-south-redifer': ['south', 'redifer'], 'up-west-waring': ['west', 'waring']
        }
        terms = search_terms.get(self.campus_key.lower(), [self.campus_key.lower()])
        for name, value in campus_options.items():
            if all(term in name for term in terms):
                return value
        return None

    def get_candidate_items_from_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        candidates = {}
        for a_tag in soup.find_all('a', href=True):
            text = a_tag.get_text(strip=True)
            if text and len(text) > 3 and 'nutrition' in a_tag['href'].lower():
                candidates[text] = urljoin(self.base_url, a_tag['href'])
        return candidates

    def filter_foods_with_gemini(self, candidate_items: Dict[str, str]) -> Dict[str, str]:
        if not self.gemini_api_key or not candidate_items:
            return candidate_items # Return all candidates if no API key

        try:
            item_names = list(candidate_items.keys())
            prompt = f"""From the list below, identify which are food/beverage items from a menu. Exclude navigation links or station names. Return a JSON object with a key "food_items" containing a list of the identified food names. List: {json.dumps(item_names)}"""
            
            response = self.session.post(self.gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
            response.raise_for_status()
            
            text_response = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            json_str = re.search(r'\{.*\}', text_response, re.DOTALL).group(0)
            food_names = json.loads(json_str).get("food_items", [])
            
            if self.debug:
                print(f"Gemini identified {len(food_names)} food items from {len(item_names)} candidates.")
            return {name: candidate_items[name] for name in food_names if name in candidate_items}
        except Exception as e:
            if self.debug:
                print(f"Gemini food filtering failed: {e}. Returning all candidates.")
            return candidate_items

    def extract_nutritional_data_for_items(self, items: Dict[str, str]) -> Dict[str, Dict[str, float]]:
        if not self.extract_nutrition:
            return {}
        
        nutrition_data = {}
        for food_name, url in items.items():
            cached_data = self.nutrition_cache.get(food_name)
            if cached_data:
                nutrition_data[food_name] = cached_data
                continue
            
            if self.debug:
                print(f"Scraping nutrition for: {food_name}")
            nutrition = self.nutrition_extractor.extract_nutritional_data(url)
            if nutrition:
                nutrition_data[food_name] = nutrition
                self.nutrition_cache.put(food_name, nutrition)
            time.sleep(0.2) # Rate limit
        return nutrition_data

    def run_analysis(self) -> Dict[str, List[Tuple[str, int, str, str]]]:
        form_options = self.get_initial_form_data()
        if not form_options:
            return {"error": "Could not fetch initial menu data from PSU website."}

        campus_value = self.find_campus_value(form_options.get('campus', {}))
        if not campus_value:
            return {"error": f"Could not find a matching campus for '{self.campus_key}'."}

        today_str_key = datetime.now().strftime('%A, %B %d').lower()
        date_value = form_options.get('date', {}).get(today_str_key)
        if not date_value: # Fallback to first available date
            date_value = next(iter(form_options.get('date', {}).values()), None)
            if not date_value: return {"error": "No menu dates available."}

        daily_menu_data = {}
        for meal_name in ["Breakfast", "Lunch", "Dinner"]:
            meal_value = form_options.get('meal', {}).get(meal_name.lower())
            if not meal_value: continue

            form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
            response = self.session.post(self.base_url, data=form_data, timeout=30)
            meal_soup = BeautifulSoup(response.content, 'html.parser')
            
            candidates = self.get_candidate_items_from_page(meal_soup)
            filtered_items = self.filter_foods_with_gemini(candidates)
            
            if filtered_items:
                meal_data = {"items": filtered_items, "nutrition": {}}
                if self.extract_nutrition:
                    nutrition_data = self.extract_nutritional_data_for_items(filtered_items)
                    meal_data["nutrition"] = nutrition_data
                    self.csv_manager.save_nutritional_data(nutrition_data, meal_name, self.campus_key)
                daily_menu_data[meal_name] = meal_data

        if not daily_menu_data:
            return {}

        return self.analyze_menu(daily_menu_data)

    def analyze_menu(self, daily_menu_data: Dict) -> Dict[str, List[Tuple[str, int, str, str]]]:
        if not self.gemini_api_key:
            # Fallback to simple local analysis if no API key
            return {}

        restrictions = [p for p, c in [("No beef.", self.exclude_beef), ("No pork.", self.exclude_pork),
                        ("Only vegetarian.", self.vegetarian), ("Only vegan.", self.vegan)] if c]
        priority = "prioritize HIGH PROTEIN" if self.prioritize_protein else "prioritize overall BALANCE"
        
        menu_for_prompt = {}
        original_urls = {}
        for meal, data in daily_menu_data.items():
            original_urls[meal] = data["items"]
            menu_for_prompt[meal] = [{"food_name": name, "nutrition": data["nutrition"].get(name)} for name in data["items"]]

        prompt = f"""Analyze the menu below. Use the provided nutritional data to make decisions. Your goal is to {priority}. My restrictions are: {' '.join(restrictions) or 'None'}. Return a JSON object with keys "Breakfast", "Lunch", "Dinner", each a list of objects with "food_name", "score" (0-100), and "reasoning". Menu: {json.dumps(menu_for_prompt)}"""
        
        response = self.session.post(self.gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
        response.raise_for_status()
        
        text_response = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        json_str = re.search(r'\{.*\}', text_response, re.DOTALL).group(0)
        parsed_json = json.loads(json_str)

        results = {}
        for meal, items in parsed_json.items():
            meal_results = []
            for item in items:
                url = original_urls.get(meal, {}).get(item["food_name"], '#')
                meal_results.append((item["food_name"], item["score"], item["reasoning"], url))
            meal_results.sort(key=lambda x: x[1], reverse=True)
            results[meal] = meal_results[:5] # Return top 5
        return results

# --- Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        api_key = os.getenv('GEMINI_API_KEY')
        analyzer = MenuAnalyzer(
            campus_key=data.get('campus', 'altoona-port-sky'),
            gemini_api_key=api_key,
            exclude_beef=data.get('exclude_beef', False),
            exclude_pork=data.get('exclude_pork', False),
            vegetarian=data.get('vegetarian', False),
            vegan=data.get('vegan', False),
            prioritize_protein=data.get('prioritize_protein', False),
            debug=True,
            extract_nutrition=data.get('extract_nutrition', True)
        )
        recommendations = analyzer.run_analysis()
        
        # Check if the result is an error dictionary
        if isinstance(recommendations, dict) and 'error' in recommendations:
             return jsonify(recommendations), 400

        return jsonify(recommendations)
        
    except Exception as e:
        print(f"[SERVER ERROR] An exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred. The analysis could not be completed. Details: {str(e)}"}), 500

@app.route('/api/nutrition-insights/<campus>')
def get_nutrition_insights(campus):
    csv_manager = CSVExportManager(debug=True)
    return jsonify(csv_manager.get_nutritional_insights(campus))

@app.route('/api/download-nutrition/<campus>')
def download_nutrition_csv(campus):
    export_dir = "exports"
    files = [f for f in os.listdir(export_dir) if f.startswith(campus) and f.endswith("_nutrition.csv")]
    if not files:
        return jsonify({"error": "No nutrition data found"}), 404
    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(export_dir, x)))
    return send_from_directory(export_dir, latest_file, as_attachment=True)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
