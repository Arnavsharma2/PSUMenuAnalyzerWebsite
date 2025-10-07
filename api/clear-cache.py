from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import shutil

app = Flask(__name__)
CORS(app)

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    try:
        data = request.json
        password = data.get('password', '')
        
        if password != 'admin2264':
            return jsonify({"error": "Invalid password"}), 401
        
        # Clear cache directory - use /tmp for Vercel
        cache_dir = "/tmp/cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
            return jsonify({"message": "Cache cleared successfully"})
        else:
            return jsonify({"message": "No cache to clear"})
            
    except Exception as e:
        print(f"[CACHE CLEAR ERROR] {e}")
        return jsonify({"error": "Failed to clear cache"}), 500

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda *args: None)