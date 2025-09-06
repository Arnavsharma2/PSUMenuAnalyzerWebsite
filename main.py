from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import os
import time
import sqlite3
import hashlib
import logging
from functools import lru_cache, wraps
from contextlib import contextmanager
from dataclasses import dataclass
from pydantic import BaseModel, validator

# --- Configuration ---
@dataclass
class Config:
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '3600'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))

config = Config()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Rate Limiting ---
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# --- Database Setup ---
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('menu_cache.db')
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS menu_cache (
                preferences_hash TEXT PRIMARY KEY,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS form_cache (
                id INTEGER PRIMARY KEY,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

# Initialize database on startup
init_db()

# --- Input Validation ---
class MenuPreferences(BaseModel):
    vegetarian: bool = False
    vegan: bool = False
    exclude_beef: bool = False
    exclude_pork: bool = False
    prioritize_protein: bool = False
    
    @validator('vegan')
    def vegan_excludes_vegetarian(cls, v, values):
        if v and values.get('vegetarian'):
            raise ValueError('Cannot be both vegan and vegetarian')
        return v

# --- Utility Functions ---
def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Function {func.__name__} failed after {max_retries} attempts: {e}")
                        raise e
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            return None
        return wrapper
    return decorator

def log_analysis_request(preferences, duration, success):
    logger.info(json.dumps({
        'event': 'menu_analysis',
        'preferences': preferences,
        'duration_ms': duration * 1000,
        'success': success,
        'timestamp': datetime.now().isoformat()
    }))

def get_cached_menu_analysis(preferences_hash):
    """Check if we have recent analysis for these preferences"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                'SELECT result FROM menu_cache WHERE preferences_hash = ? AND created_at > datetime("now", "-1 hour")',
                (preferences_hash,)
            )
            result = cursor.fetchone()
            return json.loads(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting cached analysis: {e}")
        return None

def cache_menu_analysis(preferences_hash, result):
    """Cache menu analysis result"""
    try:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO menu_cache (preferences_hash, result) VALUES (?, ?)',
                (preferences_hash, json.dumps(result))
            )
    except Exception as e:
        logger.error(f"Error caching analysis: {e}")

@lru_cache(maxsize=1)
def get_cached_form_data():
    """Cache form data for 1 hour to reduce API calls"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                'SELECT data FROM form_cache WHERE created_at > datetime("now", "-1 hour") ORDER BY created_at DESC LIMIT 1'
            )
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
    except Exception as e:
        logger.error(f"Error getting cached form data: {e}")
    return None

def cache_form_data(data):
    """Cache form data"""
    try:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO form_cache (data) VALUES (?)',
                (json.dumps(data),)
            )
    except Exception as e:
        logger.error(f"Error caching form data: {e}")

# --- Menu Analyzer Class ---
class MenuAnalyzer:
    def __init__(self, gemini_api_key: str = None, exclude_beef=False, exclude_pork=False,
                 vegetarian=False, vegan=False, prioritize_protein=False, debug=False):
        self.base_url = "https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm"
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
        self.gemini_api_key = gemini_api_key or config.GEMINI_API_KEY
        if self.gemini_api_key:
            self.gemini_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                f"?key={self.gemini_api_key}"
            )
        elif self.debug:
            logger.info("No Gemini API key provided. Using local analysis only.")
        
        if self.prioritize_protein and self.debug:
            logger.info("INFO: Analysis is set to prioritize protein content.")

    @retry_on_failure(max_retries=config.MAX_RETRIES)
    def get_initial_form_data(self) -> Optional[Dict[str, Dict[str, str]]]:
        # Check cache first
        cached_data = get_cached_form_data()
        if cached_data:
            logger.info("Using cached form data")
            return cached_data

        try:
            response = self.session.get(self.base_url, timeout=config.REQUEST_TIMEOUT)
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
            
            # Cache the result
            cache_form_data(options)
            return options
        except requests.RequestException as e:
            logger.error(f"Error fetching initial page: {e}")
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
        start_time = time.time()
        
        if self.debug: 
            logger.info("Fetching initial form options...")
        
        form_options = self.get_initial_form_data()
        if not form_options:
            logger.warning("Could not fetch form data. Using fallback.")
            return self.get_fallback_data()

        campus_options = form_options.get('campus', {})
        altoona_value = next((val for name, val in campus_options.items() if 'altoona' in name), None)
        if not altoona_value:
            logger.warning("Could not find Altoona campus value. Using fallback.")
            return self.get_fallback_data()

        date_options = form_options.get('date', {})
        today_str_key = datetime.now().strftime('%A, %B %d').lower()
        date_value = date_options.get(today_str_key)
        if not date_value:
            if date_options:
                first_available_date = list(date_options.keys())[0]
                date_value = list(date_options.values())[0]
                logger.warning(f"Today's menu ('{today_str_key}') not found. Using first available date: {first_available_date}")
            else:
                logger.warning("No dates found. Using fallback.")
                return self.get_fallback_data()

        daily_menu = {}
        meal_options = form_options.get('meal', {})
        
        # Sequential fetching (simplified for reliability)
        for meal_name in ["Breakfast", "Lunch", "Dinner"]:
            meal_key = meal_name.lower()
            meal_value = meal_options.get(meal_key)
            
            if not meal_value:
                if self.debug: 
                    logger.warning(f"Could not find form value for '{meal_name}'. Skipping.")
                continue

            try:
                form_data = {'selCampus': altoona_value, 'selMeal': meal_value, 'selMenuDate': date_value}
                if self.debug: 
                    logger.info(f"Fetching menu for {meal_name} with data: {form_data}")
                response = self.session.post(self.base_url, data=form_data, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()
                meal_soup = BeautifulSoup(response.content, 'html.parser')
                items = self.extract_items_from_meal_page(meal_soup)
                if items:
                    daily_menu[meal_name] = items
                    if self.debug: 
                        logger.info(f"Found {len(items)} items for {meal_name}.")
                time.sleep(0.5)
            except requests.RequestException as e:
                if self.debug: 
                    logger.error(f"Error fetching {meal_name} menu: {e}")

        if not daily_menu:
            logger.warning("Failed to scrape any menu items from the website. Using fallback.")
            return self.get_fallback_data()
        
        analyzed_results = self.analyze_menu_with_gemini(daily_menu) if self.gemini_api_key else self.analyze_menu_local(daily_menu)
        
        final_results = {}
        for meal, items in analyzed_results.items():
            # First, apply the hard filters based on user preferences
            filtered_items = self.apply_hard_filters(items)
            # Then, slice the list to get only the top 5 items
            final_results[meal] = filtered_items[:5]
        
        duration = time.time() - start_time
        log_analysis_request({
            'vegetarian': self.vegetarian,
            'vegan': self.vegan,
            'exclude_beef': self.exclude_beef,
            'exclude_pork': self.exclude_pork,
            'prioritize_protein': self.prioritize_protein
        }, duration, True)
        
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
            if self.debug: 
                logger.error(f"Gemini analysis failed: {e}. Falling back to local analysis.")
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
@limiter.limit("10 per minute")
def analyze():
    start_time = time.time()
    try:
        data = request.json
        logger.info(f"Received request with data: {data}")
        
        # Validate input
        try:
            preferences = MenuPreferences(**data)
        except Exception as e:
            logger.error(f"Invalid input data: {e}")
            return jsonify({"error": "Invalid input data"}), 400
        
        # Create preferences hash for caching
        preferences_dict = preferences.dict()
        preferences_hash = hashlib.md5(json.dumps(preferences_dict, sort_keys=True).encode()).hexdigest()
        
        # Check cache first
        cached_result = get_cached_menu_analysis(preferences_hash)
        if cached_result:
            logger.info("Returning cached result")
            return jsonify(cached_result)
        
        # NOTE: The GEMINI_API_KEY is retrieved from environment variables for security
        api_key = config.GEMINI_API_KEY

        analyzer = MenuAnalyzer(
            gemini_api_key=api_key,
            exclude_beef=preferences.exclude_beef,
            exclude_pork=preferences.exclude_pork,
            vegetarian=preferences.vegetarian,
            vegan=preferences.vegan,
            prioritize_protein=preferences.prioritize_protein,
            debug=config.DEBUG
        )
        
        recommendations = analyzer.run_analysis()
        
        # Cache the result
        cache_menu_analysis(preferences_hash, recommendations)
        
        duration = time.time() - start_time
        log_analysis_request(preferences_dict, duration, True)
        
        return jsonify(recommendations)
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[SERVER ERROR] {e}")
        log_analysis_request({}, duration, False)
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=config.DEBUG)

