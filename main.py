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
        except Exception as e:
            if self.debug:
                print(f"Error ensuring cache exists: {e}")

    def _load_cache(self):
        try:
            return pd.read_csv(self.cache_file).set_index('food_name')
        except (pd.errors.EmptyDataError, FileNotFoundError):
            return pd.DataFrame(columns=self.fieldnames[1:]).set_index(pd.Index([], name='food_name'))
        except Exception as e:
            if self.debug:
                print(f"Error loading nutrition cache: {e}")
            return pd.DataFrame()

    def get(self, food_name: str) -> Optional[Dict[str, float]]:
        """Retrieves nutritional data for a food item from the cache."""
        if not self.cache_df.empty and food_name.lower() in self.cache_df.index.str.lower():
            matching_index = self.cache_df.index[self.cache_df.index.str.lower() == food_name.lower()][0]
            return self.cache_df.loc[matching_index].to_dict()
        return None

    def put(self, food_name: str, nutrition_data: Dict[str, float]):
        """Saves nutritional data for a food item to the cache."""
        try:
            if not self.cache_df.empty and food_name.lower() in self.cache_df.index.str.lower():
                return
            with open(self.cache_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                row = {'food_name': food_name, **{field: nutrition_data.get(field) for field in self.fieldnames[1:]}}
                writer.writerow(row)
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
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            nutrition_data = {}
            nutrition_tables = soup.find_all('table', class_=re.compile(r'nutrition|facts', re.I))
            for table in nutrition_tables:
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value_match = re.search(r'(\d+\.?\d*)', cells[1].get_text(strip=True))
                        if value_match:
                            value = float(value_match.group(1))
                            if 'calories' in label: nutrition_data['calories'] = value
                            elif 'protein' in label: nutrition_data['protein'] = value
                            elif 'total fat' in label: nutrition_data['fat'] = value
                            elif 'saturated fat' in label: nutrition_data['saturated_fat'] = value
                            elif 'carbohydrate' in label: nutrition_data['carbs'] = value
                            elif 'fiber' in label: nutrition_data['fiber'] = value
                            elif 'sugar' in label: nutrition_data['sugar'] = value
                            elif 'sodium' in label: nutrition_data['sodium'] = value
                            elif 'cholesterol' in label: nutrition_data['cholesterol'] = value
            return nutrition_data
        except Exception as e:
            if self.debug: print(f"Error extracting nutrition data from {url}: {e}")
            return {}

# --- CSV Export Manager (For User Downloads) ---
class CSVExportManager:
    def __init__(self, debug=False):
        self.debug = debug
        self.export_dir = "exports"
        os.makedirs(self.export_dir, exist_ok=True)

    def save_nutritional_data(self, food_items: Dict[str, Dict[str, float]], meal: str, campus: str):
        if not food_items: return None
        try:
            filepath = os.path.join(self.export_dir, f"{campus}_{meal}_{datetime.now().strftime('%Y%m%d')}_nutrition.csv")
            fieldnames = ['food_name', 'meal', 'campus', 'date', 'calories', 'protein', 'fat', 'saturated_fat', 'carbs', 'fiber', 'sugar', 'sodium', 'cholesterol']
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for food_name, nutrition in food_items.items():
                    writer.writerow({'food_name': food_name, 'meal': meal, 'campus': campus, 'date': datetime.now().strftime('%Y-%m-%d'), **nutrition})
            return filepath
        except Exception as e:
            if self.debug: print(f"Error saving user export CSV: {e}")
            return None

# --- Enhanced Menu Analyzer Class ---
class MenuAnalyzer:
    def __init__(self, campus_key: str, gemini_api_key: str = None, exclude_beef=False, exclude_pork=False,
                 vegetarian=False, vegan=False, prioritize_protein=False, debug=False, extract_nutrition=True):
        self.base_url = "https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm"
        self.campus_key = campus_key
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
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
            if self.debug: print(f"Error fetching initial page: {e}")
            return None

    def find_campus_value(self, campus_options: Dict[str, str]) -> Optional[str]:
        search_terms_map = { 'altoona-port-sky': ['altoona'], 'beaver-brodhead': ['beaver'], 'behrend-brunos': ['behrend', 'bruno'], 'behrend-dobbins': ['behrend', 'dobbins'], 'berks-tullys': ['berks'], 'brandywine-blue-apple': ['brandywine'], 'greater-allegheny-cafe-metro': ['greater allegheny'], 'harrisburg-stacks': ['harrisburg', 'stacks'], 'harrisburg-outpost': ['harrisburg', 'outpost'], 'hazleton-highacres': ['hazleton'], 'mont-alto-mill': ['mont alto'], 'up-east-findlay': ['east'], 'up-north-warnock': ['north'], 'up-pollock': ['pollock'], 'up-south-redifer': ['south'], 'up-west-waring': ['west'] }
        search_terms = search_terms_map.get(self.campus_key.lower(), [self.campus_key.lower()])
        for name, value in campus_options.items():
            if all(term in name for term in search_terms): return value
        return None

    def get_candidate_items_from_page(self, soup: BeautifulSoup) -> Dict[str, str]:
        candidates = {}
        for a_tag in soup.find_all('a', href=re.compile(r'nutrition\.cfm', re.I)):
            text = a_tag.get_text(strip=True)
            if text and len(text) > 2:
                candidates[text] = urljoin(self.base_url, a_tag['href'])
        return candidates

    def filter_foods_with_gemini(self, candidate_items: Dict[str, str]) -> Dict[str, str]:
        if not self.gemini_api_key or not candidate_items: return candidate_items
        try:
            prompt = f"""From the list below, identify which are food/beverage items. Exclude station names or navigation links. Return a JSON object with a key "food_items" containing a list of the identified food names. List: {json.dumps(list(candidate_items.keys()))}"""
            response = self.session.post(self.gemini_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
            response.raise_for_status()
            text_response = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            json_str = re.search(r'\{.*\}', text_response, re.DOTALL).group(0)
            food_names = json.loads(json_str).get("food_items", [])
            return {name: candidate_items[name] for name in food_names if name in candidate_items}
        except Exception as e:
            if self.debug: print(f"Gemini food filtering failed: {e}. Returning all candidates.")
            return candidate_items

    def extract_nutritional_data_for_items(self, items: Dict[str, str]) -> Dict[str, Dict[str, float]]:
        if not self.extract_nutrition: return {}
        nutrition_data = {}
        for food_name, url in items.items():
            cached_data = self.nutrition_cache.get(food_name)
            if cached_data:
                nutrition_data[food_name] = cached_data
                continue
            nutrition = self.nutrition_extractor.extract_nutritional_data(url)
            if nutrition:
                nutrition_data[food_name] = nutrition
                self.nutrition_cache.put(food_name, nutrition)
            time.sleep(0.2)
        return nutrition_data

    def run_analysis(self) -> Dict:
        if self.debug: print(f"--- Starting Analysis for Campus: {self.campus_key} ---")
        form_options = self.get_initial_form_data()
        if not form_options:
            return {"error": "Could not fetch initial menu data from the PSU website. It may be down."}

        campus_value = self.find_campus_value(form_options.get('campus', {}))
        if not campus_value:
            return {"error": f"Could not find a matching campus for '{self.campus_key}'."}

        date_options = form_options.get('date', {})
        if not date_options:
            return {"error": "No menu dates are available for this campus. This often happens on weekends or holidays."}

        # --- NEW ROBUST DATE FINDING LOGIC ---
        now = datetime.now()
        today_month = now.strftime('%B').lower()
        today_day_num = str(now.day)
        date_value = None

        for date_text, value in date_options.items():
            if today_month in date_text and re.search(r'\b' + today_day_num + r'\b', date_text):
                date_value = value
                if self.debug: print(f"Successfully matched today's date: '{date_text}'")
                break
        
        if not date_value:
            if self.debug:
                print(f"Warning: Could not find today's date ({today_month} {today_day_num}). Available: {list(date_options.keys())}. Using first available date as fallback.")
            date_value = next(iter(date_options.values()), None)
            if not date_value:
                return {"error": "Could not determine a valid menu date to analyze after checking all available options."}

        daily_menu_data = {}
        for meal_name in ["Breakfast", "Lunch", "Dinner"]:
            meal_value = form_options.get('meal', {}).get(meal_name.lower())
            if not meal_value: continue
            try:
                form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
                response = self.session.post(self.base_url, data=form_data, timeout=30)
                response.raise_for_status()
                meal_soup = BeautifulSoup(response.content, 'html.parser')
                candidates = self.get_candidate_items_from_page(meal_soup)
                if not candidates: continue
                filtered_items = self.filter_foods_with_gemini(candidates)
                if not filtered_items: continue
                meal_data = {"items": filtered_items, "nutrition": {}}
                if self.extract_nutrition:
                    nutrition_data = self.extract_nutritional_data_for_items(filtered_items)
                    if nutrition_data:
                        meal_data["nutrition"] = nutrition_data
                        self.csv_manager.save_nutritional_data(nutrition_data, meal_name, self.campus_key)
                daily_menu_data[meal_name] = meal_data
            except requests.RequestException as e:
                if self.debug: print(f"Network error for {meal_name}: {e}")
                continue
        if not daily_menu_data:
            return {"error": "After checking all meals, no food items could be found for the selected date. The menu may be empty."}
        return self.analyze_menu(daily_menu_data)

    def analyze_menu(self, daily_menu_data: Dict) -> Dict:
        if not self.gemini_api_key: return {"error": "Backend is not configured with a Gemini API key."}
        restrictions = [p for p, c in [("No beef.", self.exclude_beef), ("No pork.", self.exclude_pork), ("Only vegetarian.", self.vegetarian), ("Only vegan.", self.vegan)] if c]
        priority = "prioritize HIGH PROTEIN" if self.prioritize_protein else "prioritize a healthy BALANCE"
        menu_for_prompt, original_urls = {}, {}
        for meal, data in daily_menu_data.items():
            original_urls[meal] = data.get("items", {})
            menu_for_prompt[meal] = [{"food_name": name, **({"nutrition": data["nutrition"][name]} if name in data.get("nutrition", {}) else {})} for name in data.get("items", {})]
        prompt = f"""Analyze the menu below based on the user's preferences: Goal: {priority}. Restrictions: {' '.join(restrictions) or 'None'}. Use provided nutritional data. If it's missing, estimate based on the name. Return a JSON object with keys "Breakfast", "Lunch", "Dinner", each a list of objects with "food_name", "score" (0-100), and "reasoning". Menu: {json.dumps(menu_for_prompt)}"""
        try:
            response = self.session.post(self.gemini_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
            response.raise_for_status()
            text_response = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text_response, re.DOTALL) or re.search(r'(\{.*?\})', text_response, re.DOTALL)
            if not json_match: return {"error": "AI model returned an invalid response."}
            parsed_json = json.loads(json_match.group(1))
            results = {}
            for meal, items in parsed_json.items():
                if meal not in ["Breakfast", "Lunch", "Dinner"]: continue
                meal_results = [(item["food_name"], item["score"], item["reasoning"], original_urls.get(meal, {}).get(item["food_name"], '#')) for item in items if all(k in item for k in ["food_name", "score", "reasoning"])]
                meal_results.sort(key=lambda x: x[1], reverse=True)
                results[meal] = meal_results[:5]
            return results
        except Exception as e:
            if self.debug: print(f"Error in analyze_menu: {e}")
            return {"error": "An error occurred during AI analysis."}

# --- Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        if not data: return jsonify({"error": "No data provided"}), 400
        analyzer = MenuAnalyzer(
            campus_key=data.get('campus', 'altoona-port-sky'), gemini_api_key=os.getenv('GEMINI_API_KEY'),
            exclude_beef=data.get('exclude_beef', False), exclude_pork=data.get('exclude_pork', False),
            vegetarian=data.get('vegetarian', False), vegan=data.get('vegan', False),
            prioritize_protein=data.get('prioritize_protein', False), debug=True,
            extract_nutrition=data.get('extract_nutrition', True))
        recommendations = analyzer.run_analysis()
        if 'error' in recommendations:
            return jsonify(recommendations), 400
        return jsonify(recommendations)
    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

