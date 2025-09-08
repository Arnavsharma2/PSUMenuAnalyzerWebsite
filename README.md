# PSU-Menu-Analyzer

Penn State Campus Dining Menu Analyzer with Nutrition Data Extraction

This web application provides personalized dining recommendations for any Penn State campus dining location. It scrapes daily menus, analyzes food items based on user preferences, and extracts detailed macronutrient data for comprehensive nutritional analysis.

## 🚀 Features

### Core Functionality
- **Multi-Campus Support**: Works with 15+ Penn State campus dining locations
- **AI-Powered Analysis**: Uses Google's Gemini API for intelligent food recommendations
- **Dietary Filtering**: Vegetarian, vegan, beef/pork exclusions, protein prioritization
- **Health Scoring**: 0-100 health scores based on nutritional content and cooking methods

### 🆕 Nutrition Data Extraction
- **Comprehensive Macronutrient Data**: Extracts detailed nutritional information from each food item's nutrition page
- **CSV Export**: Generates campus-specific CSV files with complete nutritional data
- **Batch Processing**: Processes all menu items for a selected campus
- **Structured Data**: Includes calories, macronutrients, vitamins, minerals, and ingredients

## 📊 Nutrition Data Fields

Each CSV file contains the following nutritional information for every menu item:

| Field | Description | Unit |
|-------|-------------|------|
| `food_name` | Name of the food item | - |
| `meal` | Meal type (Breakfast/Lunch/Dinner) | - |
| `campus` | Campus location | - |
| `serving_size` | Serving size description | - |
| `calories` | Total calories | kcal |
| `calories_from_fat` | Calories from fat | kcal |
| `total_fat_g` | Total fat content | grams |
| `total_fat_dv` | Total fat daily value percentage | % |
| `saturated_fat_g` | Saturated fat content | grams |
| `saturated_fat_dv` | Saturated fat daily value percentage | % |
| `trans_fat_g` | Trans fat content | grams |
| `cholesterol_mg` | Cholesterol content | mg |
| `sodium_mg` | Sodium content | mg |
| `sodium_dv` | Sodium daily value percentage | % |
| `total_carb_g` | Total carbohydrates | grams |
| `total_carb_dv` | Total carbs daily value percentage | % |
| `dietary_fiber_g` | Dietary fiber content | grams |
| `dietary_fiber_dv` | Dietary fiber daily value percentage | % |
| `sugars_g` | Total sugars | grams |
| `added_sugars_g` | Added sugars | grams |
| `protein_g` | Protein content | grams |
| `protein_dv` | Protein daily value percentage | % |
| `vitamin_d_mcg` | Vitamin D content | mcg |
| `calcium_mg` | Calcium content | mg |
| `iron_mg` | Iron content | mg |
| `potassium_mg` | Potassium content | mg |
| `ingredients` | Complete ingredients list | - |
| `extraction_timestamp` | When data was extracted | ISO timestamp |
| `url` | Source nutrition page URL | - |

## 🛠️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Arnavsharma2/PSUMenuAnalyzerWebsite.git
   cd PSUMenuAnalyzerWebsite
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key_here"
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Access the web interface**
   - Open http://localhost:5001 in your browser

## 📱 Usage

### Basic Menu Analysis
1. Select your campus dining location
2. Choose dietary preferences (vegetarian, vegan, exclusions, etc.)
3. Click "Analyze Today's Menu" for personalized recommendations

### Nutrition Data Extraction
1. Select your campus dining location
2. Click "Extract Nutrition Data" to generate a comprehensive CSV file
3. Download the CSV file with complete macronutrient data
4. Use "View Available CSVs" to see all generated files

### API Endpoints

- `POST /api/analyze` - Get personalized menu recommendations
- `POST /api/extract-nutrition` - Extract nutrition data and generate CSV
- `GET /api/download-csv/<filename>` - Download a specific CSV file
- `GET /api/list-csv-files` - List all available CSV files

## 🧪 Testing

Run the test script to verify functionality:

```bash
python test_nutrition_extraction.py
```

## 🏗️ Architecture

- **Backend**: Python Flask with BeautifulSoup for web scraping
- **Frontend**: HTML/CSS/JavaScript with Tailwind CSS
- **AI Integration**: Google Gemini API for food analysis
- **Data Storage**: CSV files for nutrition data export
- **Deployment**: Docker containerization support

## 📁 File Structure

```
PSUMenuAnalyzerWebsite/
├── main.py                          # Main Flask application
├── index.html                       # Frontend interface
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container configuration
├── test_nutrition_extraction.py     # Test script
├── nutrition_data/                  # Generated CSV files (created at runtime)
└── README.md                        # This file
```

## 🔧 Configuration

### Campus Locations Supported
- University Park (East, North, South, West food districts)
- Altoona - Port Sky Cafe
- Beaver - Brodhead Bistro
- Behrend - Bruno's & Dobbins
- Berks - Tully's
- Brandywine - Blue Apple Cafe
- Greater Allegheny - Cafe Metro
- Harrisburg - Stacks & The Outpost
- Hazleton - HighAcres Cafe
- Mont Alto - The Mill Cafe

### Environment Variables
- `GEMINI_API_KEY`: Required for AI-powered analysis
- `PORT`: Server port (default: 5001)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Contact

- **Email**: arnav.sharma2264@gmail.com
- **LinkedIn**: [Arnav Sharma](https://linkedin.com/in/arnav-sharma-b2014824b/)
- **GitHub**: [Arnavsharma2](https://github.com/Arnavsharma2)

## ⚠️ Disclaimer

This is an independent project and is not affiliated with Penn State University. The nutritional data is extracted from publicly available Penn State dining information and should be used for informational purposes only.
