#!/usr/bin/env python3
"""
Test script for nutrition data extraction functionality
"""

import os
import sys
from main import MenuAnalyzer, NutritionExtractor

def test_nutrition_extraction():
    """Test the nutrition extraction functionality"""
    print("🧪 Testing Nutrition Data Extraction")
    print("=" * 50)
    
    # Test with a sample URL (you can replace this with an actual Penn State nutrition URL)
    sample_url = "https://www.absecom.psu.edu/menus/user-pages/daily-menu.cfm"
    
    # Initialize the nutrition extractor
    extractor = NutritionExtractor(debug=True)
    
    print(f"📊 Testing nutrition extraction from: {sample_url}")
    
    # Extract nutrition data
    nutrition_data = extractor.extract_nutrition_data(sample_url)
    
    print("\n📋 Extracted Nutrition Data:")
    print("-" * 30)
    for key, value in nutrition_data.items():
        print(f"{key}: {value}")
    
    print("\n✅ Nutrition extraction test completed!")

def test_menu_analyzer_with_nutrition():
    """Test the MenuAnalyzer with nutrition extraction enabled"""
    print("\n🍽️ Testing MenuAnalyzer with Nutrition Extraction")
    print("=" * 50)
    
    # Initialize analyzer with nutrition extraction enabled
    analyzer = MenuAnalyzer(
        campus_key='altoona-port-sky',
        extract_nutrition=True,
        debug=True
    )
    
    print("📊 Running menu analysis with nutrition extraction...")
    
    try:
        # Run analysis (this will also extract nutrition data)
        results = analyzer.run_analysis()
        
        print(f"\n📈 Analysis Results:")
        print("-" * 20)
        for meal, items in results.items():
            if meal != '_csv_path':
                print(f"{meal}: {len(items)} items")
        
        if '_csv_path' in results:
            print(f"\n📁 CSV file generated: {results['_csv_path']}")
        else:
            print("\n⚠️ No CSV file was generated")
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    
    print("\n✅ MenuAnalyzer test completed!")

if __name__ == "__main__":
    print("🚀 Starting PSU Menu Analyzer Nutrition Extraction Tests")
    print("=" * 60)
    
    # Test 1: Basic nutrition extraction
    test_nutrition_extraction()
    
    # Test 2: Menu analyzer with nutrition extraction
    test_menu_analyzer_with_nutrition()
    
    print("\n🎉 All tests completed!")
    print("\nTo run the full application:")
    print("1. Set your GEMINI_API_KEY environment variable")
    print("2. Run: python main.py")
    print("3. Open http://localhost:5001 in your browser")
    print("4. Use the 'Extract Nutrition Data' button to generate CSV files")
