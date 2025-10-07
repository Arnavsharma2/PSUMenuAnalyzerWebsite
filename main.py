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
import hashlib
import pickle
from urllib.parse import urljoin
from dotenv import load_dotenv
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from .env file
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Menu Analyzer Class ---
class MenuAnalyzer:
    def __init__(self, campus_key: str, gemini_api_key: str = None, exclude_beef=False, exclude_pork=False,
                 vegetarian=False, vegan=False, prioritize_protein=False, debug=False):
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
        
        # Use the passed parameter or fall back to environment variable
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            self.gemini_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
                f"?key={self.gemini_api_key}"
            )
        elif self.debug:
            print("No Gemini API key provided. Using local analysis only.")
        
        if self.prioritize_protein and self.debug:
            print("INFO: Analysis is set to prioritize protein content.")
        
        # Cache directory setup
        self.cache_dir = "cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_cache_key(self, date_str: str) -> str:
        """Generate a cache key based on campus, date, and preferences"""
        preferences = {
            'campus': self.campus_key,
            'exclude_beef': self.exclude_beef,
            'exclude_pork': self.exclude_pork,
            'vegetarian': self.vegetarian,
            'vegan': self.vegan,
            'prioritize_protein': self.prioritize_protein,
            'date': date_str
        }
        key_string = json.dumps(preferences, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_cached_result(self, date_str: str) -> Optional[Dict[str, List[Tuple[str, int, str, str]]]]:
        """Check if we have cached results for this campus/date/preferences combination"""
        cache_key = self.get_cache_key(date_str)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                
                # Check if cache is from today
                if cached_data.get('date') == date_str:
                    if self.debug:
                        print(f"Using cached results for {self.campus_key} on {date_str}")
                    return cached_data.get('results')
            except Exception as e:
                if self.debug:
                    print(f"Error reading cache file: {e}")
        
        return None

    def save_cached_result(self, date_str: str, results: Dict[str, List[Tuple[str, int, str, str]]]):
        """Save results to cache"""
        cache_key = self.get_cache_key(date_str)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        try:
            cache_data = {
                'date': date_str,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            if self.debug:
                print(f"Cached results for {self.campus_key} on {date_str}")
        except Exception as e:
            if self.debug:
                print(f"Error saving cache: {e}")

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
            if self.debug: print(f"Error fetching initial page: {e}")
            return None

    def looks_like_food_item(self, text: str) -> bool:
        if not text or len(text.strip()) < 3 or len(text.strip()) > 70: return False
        text_lower = text.lower()
        non_food_keywords = [
            'select', 'menu', 'date', 'campus', 'print', 'view', 'nutrition', 'allergen',
            'feedback', 'contact', 'hours', 'location', 'penn state', 'altoona', 
            'port sky', 'cafe', 'kitchen', 'station', 'grill', 'deli', 'market',
            'made to order', 'action', 'no items', 'not available', 'closed'
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

    def fetch_single_meal(self, meal_name: str, meal_value: str, campus_value: str, date_value: str) -> Tuple[str, Dict[str, str]]:
        """Fetch a single meal's menu data. Returns (meal_name, items_dict) or (meal_name, {}) on error."""
        try:
            form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
            if self.debug: print(f"Fetching menu for {meal_name} with data: {form_data}")
            
            response = self.session.post(self.base_url, data=form_data, timeout=30)
            response.raise_for_status()
            meal_soup = BeautifulSoup(response.content, 'html.parser')
            items = self.extract_items_from_meal_page(meal_soup)
            
            if items:
                if self.debug: print(f"Found {len(items)} items for {meal_name}.")
                return meal_name, items
            else:
                if self.debug: print(f"No items found for {meal_name}.")
                return meal_name, {}
                
        except requests.RequestException as e:
            if self.debug: print(f"Error fetching {meal_name} menu: {e}")
            return meal_name, {}

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
        # Get current date for caching (with version to force refresh)
        today_str_key = datetime.now().strftime('%A, %B %d').lower() + "_v2"
        
        # Check cache first
        cached_result = self.get_cached_result(today_str_key)
        if cached_result:
            return cached_result
        
        if self.debug: 
            print(f"Fetching initial form options for campus: {self.campus_key}")
        
        form_options = self.get_initial_form_data()
        if not form_options:
            raise Exception("Could not fetch form data from Penn State website. Please try again later.")

        campus_options = form_options.get('campus', {})
        campus_value, campus_name_found = self.find_campus_value(campus_options)
        
        if not campus_value:
            raise Exception(f"Could not find campus value for {self.campus_key}. Available options: {list(campus_options.keys())}")
        
        if self.debug:
            print(f"Found campus: {campus_name_found} with value: {campus_value}")

        date_options = form_options.get('date', {})
        date_value = date_options.get(today_str_key)
        if not date_value:
            if date_options:
                first_available_date = list(date_options.keys())[0]
                date_value = list(date_options.values())[0]
                print(f"Warning: Today's menu ('{today_str_key}') not found. Using first available date: {first_available_date}")
            else:
                raise Exception("No dates found. Please try again later.")

        daily_menu = {}
        meal_options = form_options.get('meal', {})
        
        # Prepare meal data for concurrent execution
        meal_tasks = []
        for meal_name in ["Breakfast", "Lunch", "Dinner"]:
            meal_key = meal_name.lower()
            meal_value = meal_options.get(meal_key)
            
            if not meal_value:
                if self.debug: print(f"Could not find form value for '{meal_name}'. Skipping.")
                daily_menu[meal_name] = {}
                continue
            
            meal_tasks.append((meal_name, meal_value))
        
        # Execute meal fetching concurrently
        if meal_tasks:
            if self.debug: print(f"Fetching {len(meal_tasks)} meals concurrently...")
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all tasks
                future_to_meal = {
                    executor.submit(self.fetch_single_meal, meal_name, meal_value, campus_value, date_value): meal_name
                    for meal_name, meal_value in meal_tasks
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_meal):
                    meal_name = future_to_meal[future]
                    try:
                        result_meal_name, items = future.result()
                        daily_menu[result_meal_name] = items
                    except Exception as e:
                        if self.debug: print(f"Unexpected error fetching {meal_name}: {e}")
                        daily_menu[meal_name] = {}

        if not daily_menu:
            raise Exception("Failed to scrape any menu items from the website. Please try again later.")
        
        if not self.gemini_api_key:
            raise Exception("Gemini API key is required but not provided. Please check your configuration.")
        
        analyzed_results = self.analyze_menu_with_gemini(daily_menu)
        
        final_results = {}
        for meal, items in analyzed_results.items():
            # First, apply the hard filters based on user preferences
            filtered_items = self.apply_hard_filters(items)
            # Since we're now asking for top 5 directly, we don't need to slice further
            final_results[meal] = filtered_items
        
        # Save to cache
        self.save_cached_result(today_str_key, final_results)
        
        return final_results

    def analyze_menu_with_gemini(self, daily_menu: Dict[str, Dict[str, str]]) -> Dict[str, List[Tuple[str, int, str, str]]]:
        exclusions = []
        if self.exclude_beef: exclusions.append("No beef.")
        if self.exclude_pork: exclusions.append("No pork.")
        if self.vegetarian: exclusions.append("Only vegetarian items (includes eggs).")
        if self.vegan: exclusions.append("Only vegan items (no animal products including eggs and dairy).")
        restrictions_text = " ".join(exclusions) if exclusions else "None."

        priority_instruction = ("prioritize PROTEIN content" if self.prioritize_protein else "prioritize a BALANCE of high protein and healthy preparation")
        
        menu_for_prompt = {meal: list(items.keys()) for meal, items in daily_menu.items()}

        # Ask for top 5 options per meal, with special handling for CYO items
        prompt = f"""
        Analyze the menu below. Your goal is to {priority_instruction}. My restrictions are: {restrictions_text}
        For EACH meal, identify the top 5 options.
        
        CRITICAL RULES:
        - ONLY select items that appear EXACTLY as listed in the menu below
        - DO NOT create any variations, modifications, or "High Protein" versions
        - DO NOT add "(High Protein)" or any other suffixes to item names
        - For CYO items, explain in the reasoning how to customize them for high protein
        - Select exactly 5 items per meal category (Breakfast, Lunch, Dinner)
        
        Example of CORRECT format:
        "food_name": "CYO Omelet"
        "reasoning": "Customize with high-protein ingredients like extra eggs, cheese, and meat"
        
        Example of INCORRECT format:
        "food_name": "CYO Omelet (High Protein)"  // DO NOT DO THIS
        
        Return your response as a single, valid JSON object with keys "Breakfast", "Lunch", "Dinner". Each value should be a list of objects, each with "food_name", "score" (0-100), and "reasoning".
        Menu: {json.dumps(menu_for_prompt, indent=2)}
        """
        
        # Retry mechanism with exponential backoff
        max_retries = 5  # Increased retries for better reliability
        base_delay = 2   # Increased base delay
        retry_attempted = False
        
        for attempt in range(max_retries):
            try:
                if self.debug: print(f"Gemini API attempt {attempt + 1}/{max_retries}")
                
                response = self.session.post(
                    self.gemini_url, 
                    headers={"Content-Type": "application/json"}, 
                    json={"contents": [{"parts": [{"text": prompt}]}]}, 
                    timeout=60
                )
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
                        
                        # Skip items with "(High Protein)" suffix as they don't exist in the menu
                        if "(High Protein)" in food_name:
                            continue
                            
                        url = daily_menu.get(meal, {}).get(food_name, '#')
                        meal_results.append((food_name, item_info.get("score"), item_info.get("reasoning"), url))
                    meal_results.sort(key=lambda x: x[1], reverse=True)
                    results[meal] = meal_results
                return results
                
            except Exception as e:
                if self.debug: print(f"Gemini analysis attempt {attempt + 1} failed: {e}")
                
                # If it's the last attempt, raise the exception
                if attempt == max_retries - 1:
                    raise Exception(f"Gemini API analysis failed after {max_retries} attempts: {str(e)}")
                
                # Check for retryable errors
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ["503", "service unavailable", "overloaded", "rate limit", "quota exceeded"]):
                    retry_attempted = True
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    if self.debug: print(f"Retryable error detected: {e}. Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                else:
                    # For other errors, don't retry
                    raise Exception(f"Gemini API analysis failed: {str(e)}")
        
        # This should never be reached, but just in case
        raise Exception("Unexpected error in retry loop")

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

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    try:
        data = request.json
        password = data.get('password', '')
        
        if password != 'admin2264':
            return jsonify({"error": "Invalid password"}), 401
        
        # Clear cache directory
        import shutil
        if os.path.exists("cache"):
            shutil.rmtree("cache")
            os.makedirs("cache")
            return jsonify({"message": "Cache cleared successfully"})
        else:
            return jsonify({"message": "No cache to clear"})
            
    except Exception as e:
        print(f"[CACHE CLEAR ERROR] {e}")
        return jsonify({"error": "Failed to clear cache"}), 500

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
            debug=True
        )
        
        recommendations = analyzer.run_analysis()
        print(f"Returning recommendations: {recommendations}")
        
        return jsonify(recommendations)
    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        import traceback
        traceback.print_exc()
        
        # Check if it's a Gemini API error and pass it through
        if "Gemini API" in str(e) or "503" in str(e) or "Service Unavailable" in str(e):
            return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": "An internal server error occurred."}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

