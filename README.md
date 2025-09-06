# Penn State Campus Dining Analyzer
# PSU-Menu-Analyzer

Penn State Altoona Menu Analyzer Web App
This web application provides personalized dining recommendations for the Penn State Altoona campus cafeteria, Port Sky Cafe. It scrapes the daily menu, analyzes food items based on user preferences (vegetarian, dietary exclusions, protein priority), and provides a ranked list of suggestions.


### Core Functionality
- **Campus Selection**: Support for all Penn State campus dining locations
- **Dietary Preferences**: Vegetarian, vegan, and protein-prioritized options
- **Health Scoring**: 0-100 health scores based on nutritional content and preparation methods
- **Real-time Analysis**: Live menu scraping and analysis

### Enhanced Nutritional Analysis (NEW!)
- **Detailed Nutritional Data Extraction**: Automatically extracts calories, protein, fat, fiber, sodium, and other nutrients from PSU nutrition pages
- **CSV Export**: Download comprehensive nutritional data for all analyzed foods
- **Nutritional Insights**: View aggregated nutritional statistics and top-performing foods
- **Enhanced Scoring**: More accurate health scores based on actual nutritional data rather than just keywords

### Technical Features
- **AI-Powered Analysis**: Uses Google Gemini AI for intelligent food recommendations
- **Fallback System**: Local analysis when AI is unavailable
- **Responsive Design**: Works on desktop and mobile devices
- **Data Persistence**: Saves user preferences locally

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Arnavsharma2/PSUMenuAnalyzerWebsite.git
cd PSUMenuAnalyzerWebsite
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

4. Run the application:
```bash
python main.py
```

5. Open your browser and navigate to `http://localhost:5001`

## New Nutritional Analysis Features

### Nutritional Data Extraction
- Automatically follows nutrition links from menu items
- Extracts detailed nutritional information including:
  - Calories
  - Protein content
  - Fat (total and saturated)
  - Carbohydrates
  - Fiber
  - Sugar
  - Sodium
  - Cholesterol

### CSV Export
- Download nutritional data for any campus
- Includes all nutritional metrics for each food item
- Organized by meal and date
- Perfect for further analysis or tracking

### Enhanced Health Scoring
The new system provides more accurate health scores by considering:
- **Protein Density**: Protein content per calorie
- **Fat Quality**: Total fat vs saturated fat ratios
- **Fiber Content**: Higher fiber foods score better
- **Sodium Levels**: Lower sodium foods are preferred
- **Sugar Content**: Lower sugar foods score higher

### Nutritional Insights Dashboard
- View aggregated nutritional statistics
- Identify highest protein foods
- Find lowest calorie options
- Discover high fiber choices
- Track low sodium alternatives

## API Endpoints

### Core Endpoints
- `POST /api/analyze` - Analyze menu with user preferences
- `GET /health` - Health check endpoint

### New Nutritional Endpoints
- `GET /api/nutrition-insights/<campus>` - Get nutritional insights for a campus
- `GET /api/download-nutrition/<campus>` - Download nutrition CSV for a campus

## Configuration

### Environment Variables
- `GEMINI_API_KEY`: Your Google Gemini API key (optional, enables AI analysis)
- `PORT`: Server port (default: 5001)

### Nutritional Analysis Settings
- Enable/disable nutritional data extraction via the web interface
- Nutritional data is saved to `exports/` directory
- CSV files are named: `{campus}_{meal}_{date}_nutrition.csv`

## Usage

1. **Select Campus**: Choose your Penn State dining location
2. **Set Preferences**: Configure dietary restrictions and priorities
3. **Enable Nutritional Analysis**: Toggle nutritional data extraction (recommended)
4. **Analyze Menu**: Click "Analyze Today's Menu" to get recommendations
5. **View Insights**: Check nutritional insights and download CSV data
6. **Review Results**: See detailed health scores and nutritional information

## Data Storage

### Nutritional Data
- Stored in CSV format in `exports/` directory
- Organized by campus, meal, and date
- Includes comprehensive nutritional metrics
- Can be imported into spreadsheet applications

### User Preferences
- Saved in browser localStorage
- Automatically restored on page reload
- Includes all dietary preferences and campus selection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This is an independent project and is not affiliated with Penn State University. The nutritional data is extracted from publicly available Penn State dining information and should be used for informational purposes only.

## Contact

- Email: arnav.sharma2264@gmail.com
- LinkedIn: [Arnav Sharma](https://linkedin.com/in/arnav-sharma-b2014824b/)
- GitHub: [Arnavsharma2](https://github.com/Arnavsharma2)
