#!/usr/bin/env python3
"""
Test script specifically for testing Belgian Waffle nutrition extraction
"""

import os
import sys
from main import NutritionExtractor

def test_belgian_waffle_extraction():
    """Test nutrition extraction with a specific Belgian Waffle URL"""
    print("🧇 Testing Belgian Waffle Nutrition Extraction")
    print("=" * 50)
    
    # Initialize the nutrition extractor
    extractor = NutritionExtractor(debug=True)
    
    # Test with a sample Belgian Waffle URL (you can replace this with an actual URL)
    # For now, we'll test with the main menu page to see if we can find a Belgian Waffle link
    sample_url = "https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm"
    
    print(f"📊 Testing nutrition extraction from: {sample_url}")
    
    # Extract nutrition data
    nutrition_data = extractor.extract_nutrition_data(sample_url)
    
    print("\n📋 Extracted Nutrition Data:")
    print("-" * 30)
    for key, value in nutrition_data.items():
        print(f"{key}: {value}")
    
    print("\n✅ Belgian Waffle extraction test completed!")

def test_with_sample_html():
    """Test with the sample HTML you provided"""
    print("\n🧪 Testing with Sample HTML Structure")
    print("=" * 50)
    
    # Sample HTML structure from your example
    sample_html = """
    <body cz-shortcut-listen="true">
      <div id="wrapper">
        <div class="container">
          <div id="main">
            <div class="row col-12">
              <h1 class="rpt-ml-20">Belgian Waffle</h1>
            </div>
            <table class="responsive-table">
              <tbody>
                <tr class="no-bkg">
                  <th scope="row" rowspan="7" class="top">
                    <h3 class="nutrition-header">Nutrition Facts</h3>
                    <b>Serving Size:</b> 1 EACH<br>
                    <b>Calories:</b> 376<br>
                    <b>Calories from Fat:</b> 38<br><br>
                    * Percent Daily Values (DV) are based on a 2,000 calorie diet.
                  </th>
                  <td class="b-0 hide-el">
                    <b>Amount/Serving</b>
                  </td>
                  <td class="b-0 hide-el">
                    <b>% DV*</b>
                  </td>
                  <td class="b-0 hide-el">
                    <b>Amount/Serving</b>
                  </td>
                  <td class="b-0 hide-el">
                    <b>% DV*</b>
                  </td>
                </tr>
                <tr class="no-bkg">
                  <td class="b-0 bt-thick">
                    <b>Total Fat</b> 4.2g
                  </td>
                  <td data-title="Fat % DV*" class="b-0 bt-thick rpt-pb-20">
                    10%
                  </td>
                  <td class="b-0 bt-thick">
                    <b>Total Carb</b> 73.8g
                  </td>
                  <td data-title="Carb % DV*" class="b-0 bt-thick">
                    57%
                  </td>
                </tr>
                <tr class="no-bkg">
                  <td class="b-0">
                    <b>Sat Fat</b> 1.4g
                  </td>
                  <td data-title="Sat Fat % DV*" class="b-0 rpt-pb-20">
                    6%
                  </td>
                  <td class="b-0">
                    <b>Dietary Fiber</b> 1.4g
                  </td>
                  <td data-title="Dietary Fiber % DV*" class="b-0">
                    4%
                  </td>
                </tr>
                <tr class="no-bkg">
                  <td class="b-0">
                    <b>Trans Fat</b> 0g
                  </td>
                  <td data-title="Trans Fat % DV*" class="b-0 rpt-pb-20">
                    &nbsp;
                  </td>
                  <td class="b-0">
                    <b>Sugars</b> 7g<br>
                    <b>Added Sugar</b> 0g
                  </td>
                  <td data-title="Sugars % DV*" class="b-0">
                    &nbsp;
                  </td>
                </tr>
                <tr class="no-bkg">
                  <td class="b-0">
                    <b>Cholesterol</b> 13.9mg
                  </td>
                  <td data-title="Cholestorol % DV*" class="b-0 rpt-pb-20">
                    &nbsp;
                  </td>
                  <td class="b-0">
                    <b>Protein</b> 7g
                  </td>
                  <td data-title="Protein % DV*" class="b-0">
                    12%
                  </td>
                </tr>
                <tr class="no-bkg">
                  <td class="b-0">
                    <b>Sodium</b> 1243.3mg
                  </td>
                  <td data-title="Sodium % DV*" class="b-0">
                    54%
                  </td>
                  <td colspan="2" class="b-0">
                    &nbsp;
                  </td>
                </tr>
                <tr class="no-bkg">
                  <td colspan="2" class="b-0 top bt-thick">
                    <b>Vitamin D</b> 0mcg<br>
                    <b>Calcium</b> 142.7mg<br>
                  </td>
                  <td colspan="2" class="b-0 top bt-thick">
                    <b>Iron</b> 1.5mg<br>
                    <b>Potassium:</b> 1.1mg
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="row col-12 mt-10 rpt-ml-20">
              <b>Ingredients:</b> Water, Waffle Mix (Enriched Wheat Flour (Wheat Flour, Niacin, Reduced Iron, Thiamine Monocitrate, Riboflavin, Folic Acid), Sugar, Soybean Oil, Sodium Bicarbonate, Monocalcium Phosphate, Natural and Artifical Flavors(Dextrose, Maltodextrin, Starch, Silicon Dioxide), Salt, Yellow Corn Flour, Buttermilk Solids, Malted Barley Extract.)
            </div>
          </div>
        </div>
      </div>
    </body>
    """
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    # Test the parsing functions directly
    extractor = NutritionExtractor(debug=True)
    
    # Create empty nutrition data
    nutrition_data = {
        'food_name': '',
        'serving_size': '',
        'calories': 0,
        'calories_from_fat': 0,
        'total_fat_g': 0.0,
        'total_fat_dv': 0.0,
        'saturated_fat_g': 0.0,
        'saturated_fat_dv': 0.0,
        'trans_fat_g': 0.0,
        'cholesterol_mg': 0.0,
        'sodium_mg': 0.0,
        'sodium_dv': 0.0,
        'total_carb_g': 0.0,
        'total_carb_dv': 0.0,
        'dietary_fiber_g': 0.0,
        'dietary_fiber_dv': 0.0,
        'sugars_g': 0.0,
        'added_sugars_g': 0.0,
        'protein_g': 0.0,
        'protein_dv': 0.0,
        'vitamin_d_mcg': 0.0,
        'calcium_mg': 0.0,
        'iron_mg': 0.0,
        'potassium_mg': 0.0,
        'ingredients': '',
        'extraction_timestamp': '2025-09-08T10:40:13.364851',
        'url': 'test_url'
    }
    
    # Test table parsing
    table = soup.find('table', class_='responsive-table')
    if table:
        print("📊 Testing table parsing...")
        extractor._parse_nutrition_table(table, nutrition_data)
    
    # Test ingredients extraction
    print("🧾 Testing ingredients extraction...")
    ingredients = extractor._extract_ingredients(soup)
    nutrition_data['ingredients'] = ingredients
    
    print("\n📋 Parsed Nutrition Data:")
    print("-" * 30)
    for key, value in nutrition_data.items():
        print(f"{key}: {value}")
    
    print("\n✅ Sample HTML parsing test completed!")

if __name__ == "__main__":
    print("🚀 Starting Belgian Waffle Nutrition Extraction Tests")
    print("=" * 60)
    
    # Test 1: General nutrition extraction
    test_belgian_waffle_extraction()
    
    # Test 2: Sample HTML parsing
    test_with_sample_html()
    
    print("\n🎉 All tests completed!")
