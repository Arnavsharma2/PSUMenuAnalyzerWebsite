# PSU-Menu-Analyzer

Penn State Campus Dining Analyzer Web App
This web application provides personalized dining recommendations for Penn State campus dining locations. It scrapes daily menus, analyzes food items using AI (Google Gemini), and provides ranked suggestions based on user preferences (vegetarian, dietary exclusions, protein priority).

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

3. Add your Gemini API key to the `.env` file:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

4. Run the application:
   ```bash
   python main.py
   ```

## Environment Variables

- `GEMINI_API_KEY`: Required. Your Google Gemini API key for food analysis
- `PORT`: Optional. Server port (default: 5001)
