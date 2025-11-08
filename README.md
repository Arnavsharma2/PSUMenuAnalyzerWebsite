# PSU Menu Analyzer

Web application that scrapes Penn State campus dining menus, analyzes food items using Google Gemini AI, and provides personalized meal recommendations based on dietary preferences.

## What It Does

- Scrapes daily menus from Penn State dining websites
- Analyzes food items with AI for health scores (0-100)
- Filters by dietary preferences (vegetarian, vegan, protein priority, exclusions)
- Ranks recommendations by meal (Breakfast, Lunch, Dinner)
- Provides nutrition information links
- Caches results for 24 hours to reduce API calls

Controls:
- Select campus dining location from dropdown
- Toggle dietary preferences (vegetarian, vegan, exclude beef/pork, prioritize protein)
- Click "Analyze Today's Menu" button
- Preferences are saved to localStorage

## How It Works

1. **Menu Scraping**: Flask backend scrapes menu data from Penn State dining websites using BeautifulSoup
2. **Data Processing**: Parses HTML to extract food items, meal times, and nutrition links
3. **AI Analysis**: Sends food items to Google Gemini 2.0 Flash API for health scoring
4. **Preference Filtering**: Applies user dietary restrictions and preferences server-side
5. **Ranking**: Sorts items by health score and protein content (if prioritized)
6. **Caching**: Stores results in pickle files with MD5 hash keys for 24-hour cache
7. **Display**: Frontend displays ranked recommendations with scores and analysis

## Dependencies

- `Flask` - Backend web framework
- `Flask-CORS` - Cross-origin resource sharing
- `beautifulsoup4` - HTML parsing and web scraping
- `requests` - HTTP requests for menu scraping
- `aiohttp` - Async HTTP requests
- `python-dotenv` - Environment variable management
- `gunicorn` - WSGI server for production
- `Google Gemini 2.5 Flash API` - AI-powered nutritional analysis
- `Tailwind CSS` - Frontend styling framework

## Technical Details

- Backend: Flask REST API with CORS enabled
- Frontend: HTML/JavaScript with Tailwind CSS
- Health Score Range: 0-100 (based on protein, cooking method, nutritional balance)
- Supported Locations: 16+ Penn State campus dining locations
- Cache: 24-hour pickle file cache with MD5 hash keys
- Scraping: BeautifulSoup parsing of Penn State dining HTML
- AI Model: Google Gemini 2.5 Flash
- Note: Results may be inaccurate on weekends due to missing menu data
