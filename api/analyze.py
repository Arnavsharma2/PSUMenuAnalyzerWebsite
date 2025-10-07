import os
import json
import traceback
from datetime import datetime
from menu_analyzer import MenuAnalyzer

def handler(request):
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # Parse request body
        if hasattr(request, 'json'):
            data = request.json
        else:
            data = json.loads(request.body) if hasattr(request, 'body') else {}
        
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
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({"error": "Cannot be both vegan and vegetarian"})
            }
        
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
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(recommendations)
        }
    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        traceback.print_exc()
        
        # Check if it's a Gemini API error and pass it through
        if "Gemini API" in str(e) or "503" in str(e) or "Service Unavailable" in str(e):
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({"error": str(e)})
            }
        else:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({"error": "An internal server error occurred."})
            }