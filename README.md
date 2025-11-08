# PSU Menu Analyzer

Web application that scrapes Penn State campus dining menus, analyzes food items using Google Gemini AI, and provides personalized meal recommendations based on dietary preferences.

## What It Does

- Scrapes daily menus from Penn State dining locations
- Analyzes food items with AI for health scores (0-100)
- Filters by dietary preferences (vegetarian, vegan, protein priority, exclusions)
- Ranks recommendations by meal (Breakfast, Lunch, Dinner)
- Provides nutrition information links

Controls:
- Select campus dining location from dropdown
- Toggle dietary preferences (vegetarian, vegan, exclude beef/pork, prioritize protein)
- Click "Analyze Today's Menu" button
- Preferences are saved to localStorage

## How It Works

1. **Menu Scraping**: Fetches menu data from Penn State dining websites
2. **AI Analysis**: Sends food items to Google Gemini for health scoring
3. **Preference Filtering**: Applies user dietary restrictions and preferences
4. **Ranking**: Sorts items by health score and protein content
5. **Display**: Shows ranked recommendations with scores and analysis

## Dependencies

- `Google Gemini API` - AI-powered nutritional analysis
- `Tailwind CSS` - Styling framework
- `JavaScript` - Frontend logic and API calls

## Technical Details

- Health Score Range: 0-100 (based on protein, cooking method, nutritional balance)
- Supported Locations: 16+ Penn State campus dining locations
- Cache: 24-hour caching for menu data
- Note: Results may be inaccurate on weekends due to missing menu data
