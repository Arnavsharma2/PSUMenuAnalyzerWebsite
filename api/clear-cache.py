import os
import json
import shutil

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
        
        password = data.get('password', '')
        
        if password != 'admin2264':
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({"error": "Invalid password"})
            }
        
        # Clear cache directory - use /tmp for Vercel
        cache_dir = "/tmp/cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({"message": "Cache cleared successfully"})
            }
        else:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({"message": "No cache to clear"})
            }
            
    except Exception as e:
        print(f"[CACHE CLEAR ERROR] {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": "Failed to clear cache"})
        }