import os
import re
import json
from datetime import datetime
from urllib.parse import urljoin
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

# --- App Initialization ---
app = Flask(__name__, static_folder=None)
CORS(app)

# --- Constants & Configuration ---
# Data structure mapping frontend values to the correct URL slugs on the PSU dining website
CAMPUS_DATA = {
    "up-east-findlay": "east-food-district",
    "up-north-warnock": "north-food-district-warnock",
    "up-pollock": "pollock-dining-commons",
    "up-south-redifer": "south-food-district-redifer",
    "up-west-waring": "west-food-district-waring",
    "altoona-port-sky": "port-sky-cafe-altoona",
    "beaver-brodhead": "brodhead-bistro-beaver",
    "behrend-dobbins": "dobbins-dining-behrend",
    "berks-tullys": "tullys-berks",
    "brandywine-blue-apple": "blue-apple-cafe-brandywine",
    "harrisburg-stacks": "the-stacks-harrisburg",
    "hazleton-highacres": "highacres-cafe-hazleton",
    # Add other campuses here if needed
}

# --- Menu Analyzer Service ---
class MenuAnalyzer:
    """
    Handles scraping and analyzing menu data from the Penn State dining website.
    """
    def __init__(self, debug=False):
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.0 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://liveon.psu.edu/penn-state-food-services/dining/menus/"

    def _log(self, message):
        if self.debug:
            print(f"[DEBUG] {message}")

    def get_nutrition_data(self, url):
        """Scrapes detailed nutritional data from a specific food item's page."""
        try:
            full_url = urljoin(self.base_url, url)
            self._log(f"Fetching nutrition from: {full_url}")
            response = self.session.get(full_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            nutrition_data = {}
            # Find the nutrition facts table and extract rows
            table = soup.find('div', class_='nutrition-facts')
            if not table:
                return None

            rows = table.find_all('div', class_='nutrition-facts-row')
            for row in rows:
                label_div = row.find('div', class_='nutrition-facts-label')
                value_div = row.find('div', class_='nutrition-facts-value')
                if label_div and value_div:
                    label = label_div.get_text(strip=True).lower()
                    value = value_div.get_text(strip=True)
                    nutrition_data[label.replace(' ', '_')] = value
            
            # Standardize keys
            standardized_data = {
                "calories": nutrition_data.get("calories", "0"),
                "protein": nutrition_data.get("protein", "0g"),
                "total_fat": nutrition_data.get("total_fat", "0g"),
                "carbohydrates": nutrition_data.get("total_carbohydrate", "0g"),
                "dietary_fiber": nutrition_data.get("dietary_fiber", "0g"),
                "sugars": nutrition_data.get("total_sugars", "0g"),
                "sodium": nutrition_data.get("sodium", "0mg"),
            }
            return standardized_data
        except requests.exceptions.RequestException as e:
            self._log(f"Error fetching nutrition for {url}: {e}")
            return None

    def get_full_menu(self, campus_slug):
        """Scrapes the entire menu for a given campus slug."""
        if not campus_slug:
            return {"error": "Invalid campus slug provided."}

        menu_url = f"{self.base_url}{campus_slug}"
        self._log(f"Fetching menu from: {menu_url}")

        try:
            response = self.session.get(menu_url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            daily_menu = {"Breakfast": [], "Lunch": [], "Dinner": []}
            
            for meal in daily_menu.keys():
                meal_container = soup.find('div', id=f'meal-group-{meal.lower()}')
                if not meal_container:
                    continue
                
                # Find all food item containers to get name, link, and dietary icons
                food_item_containers = meal_container.find_all('div', class_='menu-item-container')
                for container in food_item_containers:
                    item_link = container.find('a', class_='lightbox-nutrition')
                    if not item_link:
                        continue

                    food_name = item_link.get_text(strip=True)
                    nutrition_url = item_link.get('href', '')
                    
                    # **IMPROVEMENT**: Scrape dietary icons for accurate filtering
                    dietary_info = []
                    icons_div = container.find('div', class_='menu-item-icons')
                    if icons_div:
                        icons = icons_div.find_all('img')
                        for icon in icons:
                            alt_text = icon.get('alt', '').strip()
                            if alt_text:
                                dietary_info.append(alt_text)
                    
                    menu_item = {
                        "food_name": food_name,
                        "url": nutrition_url,
                        "nutrition": None,
                        "dietary": dietary_info  # e.g., ['Vegan', 'Vegetarian']
                    }

                    if nutrition_url:
                        nutrition = self.get_nutrition_data(nutrition_url)
                        if nutrition:
                             menu_item["nutrition"] = nutrition

                    daily_menu[meal].append(menu_item)

            return daily_menu
        except requests.exceptions.RequestException as e:
            self._log(f"Failed to fetch menu page: {e}")
            return {"error": f"Could not fetch menu from Penn State's website: {e}"}
        except Exception as e:
            self._log(f"An unexpected error occurred during scraping: {e}")
            return {"error": f"An unexpected error occurred: {e}"}

    def analyze_and_score(self, menu_data, preferences):
        """Applies filters and scores menu items based on preferences and nutritional data."""
        analyzed_menu = {"Breakfast": [], "Lunch": [], "Dinner": []}
        
        for meal, items in menu_data.items():
            filtered_items = items
            
            # **IMPROVEMENT**: Use accurate dietary data for filtering instead of keywords
            if preferences.get('vegan'):
                filtered_items = [item for item in filtered_items if 'Vegan' in item.get('dietary', [])]
            elif preferences.get('vegetarian'):
                filtered_items = [item for item in filtered_items if 'Vegetarian' in item.get('dietary', [])]

            # Keyword search is still appropriate for non-icon filters
            if preferences.get('exclude_beef'):
                filtered_items = [item for item in filtered_items if 'beef' not in item['food_name'].lower()]
            if preferences.get('exclude_pork'):
                filtered_items = [item for item in filtered_items if 'pork' not in item['food_name'].lower()]

            # Score remaining items
            for item in filtered_items:
                score, reason = self.calculate_score(item, preferences)
                analyzed_menu[meal].append([
                    item['food_name'],
                    score,
                    reason,
                    item.get('url', '')
                ])
            
            analyzed_menu[meal].sort(key=lambda x: x[1], reverse=True)

        return analyzed_menu

    def calculate_score(self, item, preferences):
        """Calculates a 0-100 score for a food item."""
        score = 50
        reasons = []

        nutrition = item.get('nutrition')
        if nutrition:
            try:
                protein = float(re.sub(r'[^0-9.]', '', nutrition.get('protein', '0')))
                calories = float(re.sub(r'[^0-9.]', '', nutrition.get('calories', '0')))
                
                if calories > 0 and protein > 0:
                    protein_density = protein / (calories / 100)
                    if protein_density > 10:
                        score += 20
                        reasons.append("Excellent protein density.")
                    elif protein_density > 5:
                        score += 10
                        reasons.append("Good protein content.")
                
                if preferences.get('prioritize_protein') and protein > 15:
                    score += 15
            
            except (ValueError, TypeError):
                pass

        name_lower = item['food_name'].lower()
        if any(kw in name_lower for kw in ['grilled', 'baked', 'steamed']):
            score += 10
            reasons.append("Healthy preparation method.")
        if any(kw in name_lower for kw in ['fried', 'creamy', 'battered']):
            score -= 15
            reasons.append("Less healthy preparation method.")
        if any(kw in name_lower for kw in ['salad', 'vegetable', 'quinoa']):
            score += 10
            reasons.append("Contains healthy ingredients.")
        
        return min(max(int(score), 0), 100), " ".join(reasons) if reasons else "A standard balanced option."

# --- Initialize Service ---
analyzer = MenuAnalyzer(debug=True)

# --- Flask Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js')

@app.route('/api/analyze', methods=['POST'])
def handle_analyze():
    """Main endpoint to analyze a menu based on user preferences."""
    try:
        prefs = request.get_json()
        campus_key = prefs.get('campus')
        campus_slug = CAMPUS_DATA.get(campus_key)

        if not campus_slug:
            return jsonify({"error": f"Invalid campus selection: {campus_key}"}), 400

        menu_data = analyzer.get_full_menu(campus_slug)
        if "error" in menu_data:
            return jsonify(menu_data), 500
        
        analyzed_results = analyzer.analyze_and_score(menu_data, prefs)
        
        return jsonify(analyzed_results)

    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/api/nutrition-insights/<campus_key>', methods=['GET'])
def get_nutrition_insights(campus_key):
    campus_slug = CAMPUS_DATA.get(campus_key)
    if not campus_slug:
        return jsonify({"error": "Invalid campus selection"}), 400

    menu = analyzer.get_full_menu(campus_slug)
    if "error" in menu:
        return jsonify(menu), 500

    all_foods = [item for meal in menu.values() for item in meal if item.get("nutrition")]
    if not all_foods:
        return jsonify({"error": "No nutritional data available for insights."})
    
    df = pd.json_normalize(all_foods)
    for col in ['nutrition.calories', 'nutrition.protein', 'nutrition.total_fat', 'nutrition.sodium']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)

    insights = {
        "total_foods_analyzed": len(df),
        "average_calories": df['nutrition.calories'].mean(),
        "average_protein": df['nutrition.protein'].mean(),
        "highest_protein_foods": df.nlargest(3, 'nutrition.protein')[['food_name', 'nutrition.protein']].to_dict('records')
    }
    return jsonify(insights)


@app.route('/api/download-nutrition/<campus_key>', methods=['GET'])
def download_nutrition_csv(campus_key):
    campus_slug = CAMPUS_DATA.get(campus_key)
    if not campus_slug:
        return jsonify({"error": "Invalid campus selection"}), 400

    menu = analyzer.get_full_menu(campus_slug)
    if "error" in menu:
        return jsonify(menu), 500

    all_foods = []
    for meal, items in menu.items():
        for item in items:
            if item.get("nutrition"):
                food_record = {"meal": meal, "food_name": item["food_name"]}
                food_record.update(item["nutrition"])
                all_foods.append(food_record)

    if not all_foods:
        return Response("No nutritional data available for download.", status=404)

    df = pd.DataFrame(all_foods)
    csv_data = df.to_csv(index=False)
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={campus_key}_nutrition.csv"}
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

