#!/usr/bin/env python3
"""
Test script for macronutrient display functionality
"""

import os
import sys
from main import MenuAnalyzer

def test_macro_display():
    """Test the enhanced recommendations with macronutrient data"""
    print("🍽️ Testing Macronutrient Display Functionality")
    print("=" * 60)
    
    # Initialize analyzer with nutrition extraction enabled
    analyzer = MenuAnalyzer(
        campus_key='altoona-port-sky',
        extract_nutrition=True,
        debug=True
    )
    
    print("📊 Running menu analysis with macronutrient extraction...")
    
    try:
        # Run analysis (this will extract nutrition data for recommendations)
        results = analyzer.run_analysis()
        
        print(f"\n📈 Analysis Results with Macronutrients:")
        print("-" * 50)
        
        for meal, items in results.items():
            if meal == '_csv_path':
                print(f"📁 CSV file generated: {items}")
                continue
                
            print(f"\n🍽️ {meal}:")
            print("-" * 20)
            
            if items and len(items) > 0:
                for i, item in enumerate(items, 1):
                    if len(item) == 5:  # Enhanced format with nutrition data
                        food_name, score, reason, url, nutrition = item
                        print(f"{i}. {food_name}")
                        print(f"   Health Score: {score}")
                        print(f"   Analysis: {reason}")
                        
                        if nutrition and nutrition.get('calories', 0) > 0:
                            print(f"   📊 Nutrition Facts:")
                            print(f"      • Calories: {nutrition.get('calories', 0)}")
                            print(f"      • Total Fat: {nutrition.get('total_fat_g', 0)}g")
                            print(f"      • Total Carbs: {nutrition.get('total_carb_g', 0)}g")
                            print(f"      • Protein: {nutrition.get('protein_g', 0)}g")
                            if nutrition.get('sodium_mg', 0) > 0:
                                print(f"      • Sodium: {nutrition.get('sodium_mg', 0)}mg")
                            print(f"      • Serving Size: {nutrition.get('serving_size', 'N/A')}")
                        else:
                            print(f"   📊 Nutrition: No data available")
                        print()
                    else:
                        # Fallback for old format
                        food_name, score, reason, url = item
                        print(f"{i}. {food_name} (Score: {score}) - {reason}")
            else:
                print("   No items found for this meal.")
        
        print("\n✅ Macronutrient display test completed!")
        
        # Test the data structure
        print(f"\n🔍 Data Structure Analysis:")
        print("-" * 30)
        for meal, items in results.items():
            if meal != '_csv_path' and items:
                sample_item = items[0]
                print(f"{meal}: {len(sample_item)} elements per item")
                if len(sample_item) == 5:
                    print(f"  ✅ Enhanced format with nutrition data")
                else:
                    print(f"  ⚠️  Old format without nutrition data")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 Test completed!")

def test_nutrition_data_structure():
    """Test the structure of nutrition data"""
    print("\n🧪 Testing Nutrition Data Structure")
    print("=" * 50)
    
    from main import NutritionExtractor
    
    # Create a sample nutrition data structure
    extractor = NutritionExtractor(debug=True)
    sample_nutrition = extractor._get_empty_nutrition_data("test_url")
    
    print("📋 Sample Nutrition Data Structure:")
    print("-" * 40)
    for key, value in sample_nutrition.items():
        print(f"{key}: {value}")
    
    print("\n✅ Nutrition data structure test completed!")

if __name__ == "__main__":
    print("🚀 Starting Macronutrient Display Tests")
    print("=" * 60)
    
    # Test 1: Nutrition data structure
    test_nutrition_data_structure()
    
    # Test 2: Macronutrient display functionality
    test_macro_display()
    
    print("\n🎉 All tests completed!")
    print("\nTo see the full web interface with macronutrient display:")
    print("1. Run: python main.py")
    print("2. Open: http://localhost:5001")
    print("3. Click 'Analyze Today's Menu' to see macronutrients displayed!")
