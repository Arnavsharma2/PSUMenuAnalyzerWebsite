Penn State Campus Dining Analyzer
This web application provides personalized dining recommendations for Penn State campus dining locations. It scrapes the live daily menu from the official PSU dining website, analyzes food items based on nutritional data and user preferences, and provides a ranked list of suggestions with health scores.

Core Functionality
Live Menu Scraping: Fetches data directly from liveon.psu.edu for the most up-to-date menus.

Campus Selection: Supports major Penn State campus dining locations.

Dietary Preferences: Filters for vegetarian, vegan, and high-protein diets, plus exclusions for beef and pork.

Nutritional Health Scoring: Ranks food on a 0-100 scale based on scraped nutritional data (protein density, preparation method).

Nutritional Analysis: Fetches detailed nutritional data for each menu item where available.

Data Export: Download the complete nutritional data for a location as a CSV file.

How It Works
The application consists of a Python Flask backend and a vanilla JavaScript frontend.

The user selects a campus and their dietary preferences on the webpage.

The browser sends this request to the Flask backend API.

The backend scrapes the appropriate menu page from the Penn State dining website.

For each food item, it follows the link to the nutrition page and scrapes detailed data (calories, protein, fat, etc.).

It applies the user's dietary filters.

A health score is calculated for each remaining item based on its nutritional profile.

The final, sorted recommendations are sent back to the frontend to be displayed.

Getting Started (Local Development)
Clone the repository:

git clone <your-repo-url>
cd PSUMenuAnalyzerWebsite

Install dependencies:
It's recommended to use a virtual environment.

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt

Run the application:

python main.py

Open your browser and navigate to http://127.0.0.1:5001.

Deployment
This application is configured for deployment on services like Heroku, Render, or any platform that supports Python web apps via a Dockerfile.

Key Deployment Steps:

Push the code to your hosting provider (e.g., via Git).

The platform will use the Dockerfile to build a container image.

The gunicorn web server specified in the Dockerfile will start the application.

The server is configured to run on the port provided by the environment variable $PORT, which is standard for most hosting platforms.

There are no API keys or environment variables required for this refactored version to run.

API Endpoints
POST /api/analyze: The main endpoint. Takes a JSON body with user preferences and returns scored meal recommendations.

GET /api/nutrition-insights/<campus_key>: Provides high-level stats (average calories, top protein foods) for a given campus menu.

GET /api/download-nutrition/<campus_key>: Triggers a download of a CSV file containing all scraped nutritional data for the selected campus menu.

Project Refactor Summary
This project was significantly refactored to address several core issues:

Corrected Web Scraper: The scraper was rewritten to target the current Penn State dining website (liveon.psu.edu), fixing the primary bug that prevented any data from being loaded.

Integrated Nutritional Analysis: The health scoring system now uses real, scraped nutritional data instead of relying on keywords, making the recommendations far more accurate.

Frontend/Backend Synchronization: The campus selection dropdown in the frontend now matches what the backend expects, ensuring requests are processed correctly.

Simplified Dependencies: The dependency on the Gemini AI API was removed, as the new scraping method is precise enough to not require AI-based filtering. This also removes the need for an API key, simplifying deployment.

Implemented Missing Features: The "Nutritional Insights" and "Download CSV" features described in the original README have now been fully implemented.