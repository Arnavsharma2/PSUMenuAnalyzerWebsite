from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'PSU Menu Analyzer is running'
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        campus = data.get('campus', 'altoona-port-sky')
        vegetarian = data.get('vegetarian', False)
        vegan = data.get('vegan', False)
        exclude_beef = data.get('exclude_beef', False)
        exclude_pork = data.get('exclude_pork', False)
        prioritize_protein = data.get('prioritize_protein', False)
        
        # Simple fallback data
        results = {
            "Breakfast": [
                ["Scrambled Eggs", 75, "High protein, good for breakfast", "#"],
                ["Oatmeal", 70, "High fiber, heart healthy", "#"],
                ["Greek Yogurt", 65, "High protein, probiotics", "#"],
                ["Fresh Fruit", 60, "Natural vitamins and fiber", "#"],
                ["Whole Grain Toast", 55, "Complex carbohydrates", "#"]
            ],
            "Lunch": [
                ["Grilled Chicken Salad", 80, "High protein, low calorie", "#"],
                ["Salmon Fillet", 75, "Omega-3 fatty acids, high protein", "#"],
                ["Quinoa Bowl", 70, "Complete protein, high fiber", "#"],
                ["Turkey Sandwich", 65, "Lean protein, balanced meal", "#"],
                ["Vegetable Soup", 60, "Low calorie, high nutrients", "#"]
            ],
            "Dinner": [
                ["Baked Salmon", 85, "High protein, omega-3s", "#"],
                ["Grilled Chicken Breast", 80, "Lean protein, low fat", "#"],
                ["Vegetable Stir Fry", 75, "High fiber, vitamins", "#"],
                ["Brown Rice Bowl", 70, "Complex carbs, fiber", "#"],
                ["Roasted Vegetables", 65, "Antioxidants, vitamins", "#"]
            ]
        }
        
        # Apply basic filters
        if vegetarian or vegan:
            # Remove meat items
            for meal in results:
                results[meal] = [item for item in results[meal] 
                               if not any(meat in item[0].lower() for meat in ['chicken', 'salmon', 'turkey', 'beef', 'pork'])]
        
        if exclude_beef:
            for meal in results:
                results[meal] = [item for item in results[meal] if 'beef' not in item[0].lower()]
        
        if exclude_pork:
            for meal in results:
                results[meal] = [item for item in results[meal] if 'pork' not in item[0].lower()]
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in analyze: {e}")
        return jsonify({"error": "An error occurred"}), 500

@app.route('/api/nutrition-insights/<campus>')
def get_nutrition_insights(campus):
    return jsonify({
        "message": "Nutrition insights not available in simple mode",
        "campus": campus
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
