from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
from datetime import datetime
from menu_analyzer import MenuAnalyzer

app = Flask(__name__)
CORS(app)

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
        traceback.print_exc()
        
        # Check if it's a Gemini API error and pass it through
        if "Gemini API" in str(e) or "503" in str(e) or "Service Unavailable" in str(e):
            return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": "An internal server error occurred."}), 500

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda *args: None)