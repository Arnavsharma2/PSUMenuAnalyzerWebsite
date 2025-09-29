#!/usr/bin/env python3
"""
Local HTTP server to test the Vercel serverless functions
"""
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class LocalServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/health':
            self.handle_health()
        elif parsed_path.path == '/':
            self.serve_index()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/analyze':
            self.handle_analyze()
        else:
            self.send_error(404, "Not Found")
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def handle_health(self):
        from api.health import handler as health_handler
        
        # Create a mock handler
        class MockHandler(health_handler):
            def __init__(self):
                self.command = 'GET'
                self.path = '/api/health'
                self.headers = {}
                self.rfile = None
                self.wfile = self
        
            def send_response(self, code):
                self.status_code = code
                super().send_response(code)
            
            def send_header(self, name, value):
                super().send_header(name, value)
            
            def end_headers(self):
                super().end_headers()
            
            def write(self, data):
                super().wfile.write(data)
        
        try:
            handler = MockHandler()
            handler.do_GET()
        except Exception as e:
            self.send_error(500, f"Health check failed: {str(e)}")
    
    def handle_analyze(self):
        from api.analyze import handler as analyze_handler
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            request_data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        
        # Create a mock handler
        class MockHandler(analyze_handler):
            def __init__(self):
                self.command = 'POST'
                self.path = '/api/analyze'
                self.headers = {'Content-Length': str(len(post_data))}
                self.rfile = type('MockRFile', (), {'read': lambda x: post_data})()
                self.wfile = self
        
            def send_response(self, code):
                self.status_code = code
                super().send_response(code)
            
            def send_header(self, name, value):
                super().send_header(name, value)
            
            def end_headers(self):
                super().end_headers()
            
            def write(self, data):
                super().wfile.write(data)
        
        try:
            handler = MockHandler()
            handler.do_POST()
        except Exception as e:
            self.send_error(500, f"Analysis failed: {str(e)}")
    
    def serve_index(self):
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
    
    def log_message(self, format, *args):
        # Custom log format
        print(f"[{self.log_date_time_string()}] {format % args}")

def run_server(port=3000):
    print(f"🚀 Starting local server on port {port}")
    print(f"📱 Frontend: http://localhost:{port}")
    print(f"🔧 API Health: http://localhost:{port}/api/health")
    print(f"🧪 API Analyze: http://localhost:{port}/api/analyze")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50)
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, LocalServerHandler)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.shutdown()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Local server for testing Vercel functions')
    parser.add_argument('--port', type=int, default=3000, help='Port to run server on')
    args = parser.parse_args()
    
    run_server(args.port)

