from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# Import the MenuAnalyzer from the api module
from api.menu_analyzer import MenuAnalyzer

# --- Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health_check():
    from datetime import datetime
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

