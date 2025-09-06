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

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# Campus configuration mapping
CAMPUS_CONFIG = {
    'altoona-port-sky': {
        'name': 'Altoona - Port Sky Cafe',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'altoona'
    },
    'beaver-brodhead': {
        'name': 'Beaver - Brodhead Bistro',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'beaver'
    },
    'behrend-brunos': {
        'name': 'Behrend - Bruno\'s',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'behrend'
    },
    'behrend-dobbins': {
        'name': 'Behrend - Dobbins',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'behrend'
    },
    'berks-tullys': {
        'name': 'Berks - Tully\'s',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'berks'
    },
    'brandywine-blue-apple': {
        'name': 'Brandywine - Blue Apple Cafe',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'brandywine'
    },
    'greater-allegheny-cafe-metro': {
        'name': 'Greater Allegheny - Cafe Metro',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'greater-allegheny'
    },
    'harrisburg-stacks': {
        'name': 'Harrisburg - Stacks',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'harrisburg'
    },
    'harrisburg-outpost': {
        'name': 'Harrisburg - The Outpost',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'harrisburg'
    },
    'hazleton-highacres': {
        'name': 'Hazleton - HighAcres Cafe',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'hazleton'
    },
    'mont-alto-mill': {
        'name': 'Mont Alto - The Mill Cafe',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'mont-alto'
    },
    'up-east-findlay': {
        'name': 'UP: East Food District @ Findlay',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'up-east'
    },
    'up-north-warnock': {
        'name': 'UP: North Food District @ Warnock',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'up-north'
    },
    'up-pollock': {
        'name': 'UP: Pollock Dining Commons',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'up-pollock'
    },
    'up-south-redifer': {
        'name': 'UP: South Food District @ Redifer',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'up-south'
    },
    'up-west-waring': {
        'name': 'UP: West Food District @ Waring',
        'base_url': 'https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm',
        'campus_value': 'up-west'
    }
}

# --- Menu Analyzer Class ---
class MenuAnalyzer:
    def __init__(self, campus_key: str, gemini_api_key: str = None, exclude_beef=False, exclude_pork=False,
                 vegetarian=False, vegan=False, prioritize_protein=False, debug=False):
        self.campus_config = CAMPUS_CONFIG.get(campus_key, CAMPUS_CONFIG['altoona-port-sky'])
        self.base_url = self.campus_config['base_url']
        self.campus_value = self.campus_config['campus_value']
        self.campus_name = self.campus_config['name']
        
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
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                f"?key={self.gemini_api_key}"
            )
        elif self.debug:
            print("No Gemini API key provided. Using local analysis only.")
        
        if self.prioritize_protein and self.debug:
            print("INFO: Analysis is set to prioritize protein content.")

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
            'made to order', 'action'
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

    def run_analysis(self) -> Dict[str, List[Tuple[str, int, str, str]]]:
        if self.debug: 
            print(f"Fetching initial form options for {self.campus_name}...")
        
        form_options = self.get_initial_form_data()
        if not form_options:
            print("Could not fetch form data. Using fallback.")
            return self.get_fallback_data()

        campus_options = form_options.get('campus', {})
        # Look for the specific campus value
        campus_value = None
        for name, val in campus_options.items():
            if self.campus_value in name.lower():
                campus_value = val
                break
        
        if not campus_value:
            print(f"Could not find {self.campus_name} campus value. Using fallback.")
            return self.get_fallback_data()

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
                if self.debug: print(f"Could not find form value for '{meal_name}'. Skipping.")
                continue

            try:
                form_data = {'selCampus': campus_value, 'selMeal': meal_value, 'selMenuDate': date_value}
                if self.debug: print(f"Fetching menu for {meal_name} with data: {form_data}")
                response = self.session.post(self.base_url, data=form_data, timeout=30)
                response.raise_for_status()
                meal_soup = BeautifulSoup(response.content, 'html.parser')
                items = self.extract_items_from_meal_page(meal_soup)
                if items:
                    daily_menu[meal_name] = items
                    if self.debug: print(f"Found {len(items)} items for {meal_name}.")
                time.sleep(0.5)
            except requests.RequestException as e:
                if self.debug: print(f"Error fetching {meal_name} menu: {e}")

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
            analyzed_items = self.analyze_food_health_local_list(items)
            analyzed_items.sort(key=lambda x: x[1], reverse=True)
            results[meal] = analyzed_items
        return results

    def analyze_food_health_local_list(self, food_items: Dict[str, str]) -> List[Tuple[str, int, str, str]]:
        health_scores = []
        protein_keywords = {'excellent': ['chicken', 'salmon', 'tuna', 'turkey'], 'good': ['beef', 'eggs', 'tofu', 'beans'], 'moderate': ['cheese', 'yogurt']}
        healthy_prep = {'excellent': ['grilled', 'baked', 'steamed'], 'good': ['sautéed'], 'poor': ['fried', 'creamy', 'battered']}

        protein_weights = {'excellent': 40, 'good': 30, 'moderate': 15} if self.prioritize_protein else {'excellent': 30, 'good': 20, 'moderate': 10}
        prep_weights = {'excellent': 10, 'good': 5, 'poor': -15} if self.prioritize_protein else {'excellent': 20, 'good': 10, 'poor': -25}

        for item, url in food_items.items():
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
            health_scores.append((item, score, ", ".join(reasoning) or "Standard option", url))
        return health_scores

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

        # Determine campus based on the selected option
        campus_key = data.get('campus')
        if not campus_key:
            return jsonify({"error": "Campus not selected."}), 400

        analyzer = MenuAnalyzer(
            campus_key=campus_key,
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
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

