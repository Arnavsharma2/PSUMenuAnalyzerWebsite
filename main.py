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
import google.generativeai as genai

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# Configure Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY', 'your-gemini-api-key-here'))

# --- AI Food Filter Class ---
class AIFoodFilter:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    def filter_food_items(self, items, meal_type, location):
        """Use Gemini AI to filter out non-food items"""
        try:
            # Create a prompt for Gemini to identify food items
            prompt = f"""
            You are analyzing a menu from a college dining hall. Please identify which items are actual food/drink items vs UI elements, navigation items, or non-food content.
            
            Location: {location}
            Meal Type: {meal_type}
            
            Items to analyze:
            {json.dumps(items, indent=2)}
            
            Please return ONLY a JSON array of the actual food/drink items. Exclude:
            - Navigation elements (Home, Menu, Contact, etc.)
            - UI elements (Set Dietary Filters, Hours, etc.)
            - Non-food content
            - Empty or placeholder items
            
            Return format: ["item1", "item2", "item3"]
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse the response
            try:
                # Extract JSON from response
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3]
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3]
                
                filtered_items = json.loads(response_text)
                return filtered_items if isinstance(filtered_items, list) else items
            except json.JSONDecodeError:
                print(f"Failed to parse Gemini response: {response.text}")
                return items
                
        except Exception as e:
            print(f"Error using Gemini AI: {e}")
            return items

# Initialize AI filter
ai_filter = AIFoodFilter()

# --- Menu Analyzer Class ---
class MenuAnalyzer:
    def __init__(self, debug=False):
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://dining.psu.edu"
        self.campus_data = {
            "University Park": {
                "url": "https://dining.psu.edu/menus",
                "locations": {
                    "Findlay Commons": "findlay-commons",
                    "Redifer Commons": "redifer-commons",
                    "Waring Commons": "waring-commons",
                    "Pollock Commons": "pollock-commons",
                    "South Food District": "south-food-district",
                    "West Food District": "west-food-district",
                    "East Food District": "east-food-district",
                    "North Food District": "north-food-district"
                }
            },
            "Harrisburg": {
                "url": "https://dining.psu.edu/menus/harrisburg",
                "locations": {
                    "Capital Union Building": "capital-union-building"
                }
            },
            "Altoona": {
                "url": "https://dining.psu.edu/menus/altoona",
                "locations": {
                    "Slep Student Center": "slep-student-center"
                }
            },
            "Behrend": {
                "url": "https://dining.psu.edu/menus/behrend",
                "locations": {
                    "Reed Union Building": "reed-union-building"
                }
            },
            "Berks": {
                "url": "https://dining.psu.edu/menus/berks",
                "locations": {
                    "Thun Library": "thun-library"
                }
            },
            "Brandywine": {
                "url": "https://dining.psu.edu/menus/brandywine",
                "locations": {
                    "Commons Building": "commons-building"
                }
            },
            "DuBois": {
                "url": "https://dining.psu.edu/menus/dubois",
                "locations": {
                    "Hiller Student Union": "hiller-student-union"
                }
            },
            "Fayette": {
                "url": "https://dining.psu.edu/menus/fayette",
                "locations": {
                    "Eberly Building": "eberly-building"
                }
            },
            "Greater Allegheny": {
                "url": "https://dining.psu.edu/menus/greater-allegheny",
                "locations": {
                    "Student Community Center": "student-community-center"
                }
            },
            "Hazleton": {
                "url": "https://dining.psu.edu/menus/hazleton",
                "locations": {
                    "Student Union Building": "student-union-building"
                }
            },
            "Lehigh Valley": {
                "url": "https://dining.psu.edu/menus/lehigh-valley",
                "locations": {
                    "Student Union": "student-union"
                }
            },
            "Mont Alto": {
                "url": "https://dining.psu.edu/menus/mont-alto",
                "locations": {
                    "General Studies Building": "general-studies-building"
                }
            },
            "New Kensington": {
                "url": "https://dining.psu.edu/menus/new-kensington",
                "locations": {
                    "Student Union": "student-union"
                }
            },
            "Schuylkill": {
                "url": "https://dining.psu.edu/menus/schuylkill",
                "locations": {
                    "Student Community Center": "student-community-center"
                }
            },
            "Scranton": {
                "url": "https://dining.psu.edu/menus/scranton",
                "locations": {
                    "Student Union": "student-union"
                }
            },
            "Shenango": {
                "url": "https://dining.psu.edu/menus/shenango",
                "locations": {
                    "Student Union": "student-union"
                }
            },
            "Wilkes-Barre": {
                "url": "https://dining.psu.edu/menus/wilkes-barre",
                "locations": {
                    "Student Union": "student-union"
                }
            },
            "York": {
                "url": "https://dining.psu.edu/menus/york",
                "locations": {
                    "Student Union": "student-union"
                }
            }
        }
    
    def get_menu_data(self, campus, location, date=None):
        """Get menu data for a specific campus and location"""
        try:
            if campus not in self.campus_data:
                return {"error": f"Campus '{campus}' not found"}
            
            if location not in self.campus_data[campus]["locations"]:
                return {"error": f"Location '{location}' not found for campus '{campus}'"}
            
            location_slug = self.campus_data[campus]["locations"][location]
            base_url = self.campus_data[campus]["url"]
            
            # Construct the URL
            if date:
                url = f"{base_url}/{location_slug}?date={date}"
            else:
                url = f"{base_url}/{location_slug}"
            
            if self.debug:
                print(f"Fetching menu from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract menu data
            menu_data = self.extract_menu_data(soup, campus, location)
            
            return menu_data
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to fetch menu data: {str(e)}"}
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}
    
    def extract_menu_data(self, soup, campus, location):
        """Extract menu data from the HTML"""
        menu_data = {
            "campus": campus,
            "location": location,
            "meals": {},
            "extraction_time": datetime.now().isoformat()
        }
        
        # Find all meal sections
        meal_sections = soup.find_all(['div', 'section'], class_=re.compile(r'meal|menu|food', re.I))
        
        for section in meal_sections:
            # Try to identify meal type
            meal_type = self.identify_meal_type(section)
            if not meal_type:
                continue
            
            # Extract food items from this section
            food_items = self.extract_food_items(section)
            
            # Use AI to filter out non-food items
            if food_items:
                filtered_items = ai_filter.filter_food_items(food_items, meal_type, location)
                menu_data["meals"][meal_type] = filtered_items
            else:
                menu_data["meals"][meal_type] = []
        
        return menu_data
    
    def identify_meal_type(self, section):
        """Identify the meal type from a section"""
        text = section.get_text().lower()
        
        if 'breakfast' in text:
            return 'breakfast'
        elif 'lunch' in text:
            return 'lunch'
        elif 'dinner' in text:
            return 'dinner'
        elif 'brunch' in text:
            return 'brunch'
        elif 'late night' in text or 'late-night' in text:
            return 'late night'
        else:
            return None
    
    def extract_food_items(self, section):
        """Extract food items from a section"""
        items = []
        
        # Look for various food item patterns
        food_elements = section.find_all(['a', 'span', 'div', 'li'], 
                                       class_=re.compile(r'food|item|menu|dish', re.I))
        
        for element in food_elements:
            text = element.get_text().strip()
            if text and len(text) > 2:
                items.append(text)
        
        # Also look for links that might be food items
        links = section.find_all('a', href=True)
        for link in links:
            text = link.get_text().strip()
            if text and len(text) > 2:
                items.append(text)
        
        return items
    
    def analyze_food_health(self, food_items):
        """Analyze the healthiness of food items"""
        if not food_items:
            return []
        
        analysis = []
        for item in food_items:
            # Simple health analysis based on keywords
            health_score = self.calculate_health_score(item)
            analysis.append({
                "item": item,
                "health_score": health_score,
                "health_rating": self.get_health_rating(health_score)
            })
        
        return analysis
    
    def calculate_health_score(self, food_item):
        """Calculate a health score for a food item"""
        score = 50  # Base score
        item_lower = food_item.lower()
        
        # Positive keywords
        healthy_keywords = {
            'grilled': 10, 'baked': 8, 'steamed': 10, 'roasted': 8,
            'fresh': 8, 'organic': 10, 'whole grain': 10, 'whole wheat': 8,
            'vegetable': 8, 'salad': 10, 'fruit': 8, 'lean': 8,
            'chicken breast': 10, 'salmon': 10, 'quinoa': 10,
            'brown rice': 8, 'sweet potato': 8, 'broccoli': 10,
            'spinach': 10, 'kale': 10, 'avocado': 8, 'nuts': 6,
            'yogurt': 6, 'eggs': 6, 'fish': 8, 'turkey': 6
        }
        
        # Negative keywords
        unhealthy_keywords = {
            'fried': -15, 'deep fried': -20, 'battered': -15,
            'breaded': -10, 'crispy': -8, 'cheesy': -5,
            'creamy': -5, 'buttery': -8, 'sugary': -10,
            'sweet': -5, 'chocolate': -8, 'cake': -10,
            'cookie': -10, 'pie': -8, 'ice cream': -10,
            'soda': -15, 'juice': -5, 'smoothie': -3
        }
        
        # Apply keyword scoring
        for keyword, points in healthy_keywords.items():
            if keyword in item_lower:
                score += points
        
        for keyword, points in unhealthy_keywords.items():
            if keyword in item_lower:
                score += points
        
        return max(0, min(100, score))
    
    def get_health_rating(self, score):
        """Get health rating based on score"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Poor"

# Initialize analyzer
analyzer = MenuAnalyzer(debug=True)

# --- Flask Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js')

@app.route('/api/campuses', methods=['GET'])
def get_campuses():
    """Get list of available campuses"""
    return jsonify(list(analyzer.campus_data.keys()))

@app.route('/api/locations/<campus>', methods=['GET'])
def get_locations(campus):
    """Get locations for a specific campus"""
    if campus not in analyzer.campus_data:
        return jsonify({"error": "Campus not found"}), 404
    
    locations = list(analyzer.campus_data[campus]["locations"].keys())
    return jsonify(locations)

@app.route('/api/analyze', methods=['POST'])
def analyze_menu():
    """Analyze menu for a specific campus and location"""
    try:
        data = request.get_json()
        campus = data.get('campus')
        location = data.get('location')
        date = data.get('date')
        
        if not campus or not location:
            return jsonify({"error": "Campus and location are required"}), 400
        
        # Get menu data
        menu_data = analyzer.get_menu_data(campus, location, date)
        
        if "error" in menu_data:
            return jsonify(menu_data), 500
        
        # Analyze each meal
        for meal_type, items in menu_data["meals"].items():
            if items:  # Only analyze if there are items
                analysis = analyzer.analyze_food_health(items)
                menu_data["meals"][meal_type] = analysis
            else:
                menu_data["meals"][meal_type] = []
        
        return jsonify(menu_data)
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

