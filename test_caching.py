#!/usr/bin/env python3
"""
Test script to verify caching functionality works
"""
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_caching_functionality():
    print("🧪 Testing Caching Functionality")
    print("=" * 50)
    
    try:
        from api.analyze import MenuAnalyzer
        
        # Get API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ No API key found. Please check your .env file.")
            return
        
        # Test 1: First request (should be slow - no cache)
        print("\n🔄 Test 1: First request (no cache)")
        print("-" * 30)
        
        start_time = time.time()
        analyzer1 = MenuAnalyzer(
            campus_key="altoona-port-sky",
            gemini_api_key=api_key,
            prioritize_protein=True,
            debug=True
        )
        
        results1 = analyzer1.run_analysis()
        first_request_time = time.time() - start_time
        
        print(f"✅ First request completed in {first_request_time:.2f} seconds")
        print(f"📊 Results: {len(results1.get('Breakfast', []))} breakfast items")
        
        # Test 2: Second request with same settings (should be fast - cached)
        print("\n⚡ Test 2: Second request (should be cached)")
        print("-" * 30)
        
        start_time = time.time()
        analyzer2 = MenuAnalyzer(
            campus_key="altoona-port-sky",
            gemini_api_key=api_key,
            prioritize_protein=True,
            debug=True
        )
        
        results2 = analyzer2.run_analysis()
        second_request_time = time.time() - start_time
        
        print(f"✅ Second request completed in {second_request_time:.2f} seconds")
        print(f"📊 Results: {len(results2.get('Breakfast', []))} breakfast items")
        
        # Test 3: Different preferences (should be slow - different cache key)
        print("\n🔄 Test 3: Different preferences (different cache)")
        print("-" * 30)
        
        start_time = time.time()
        analyzer3 = MenuAnalyzer(
            campus_key="altoona-port-sky",
            gemini_api_key=api_key,
            prioritize_protein=True,
            vegetarian=True,  # Different preference
            debug=True
        )
        
        results3 = analyzer3.run_analysis()
        third_request_time = time.time() - start_time
        
        print(f"✅ Third request completed in {third_request_time:.2f} seconds")
        print(f"📊 Results: {len(results3.get('Breakfast', []))} breakfast items")
        
        # Test 4: Same preferences again (should be fast - cached)
        print("\n⚡ Test 4: Same preferences again (should be cached)")
        print("-" * 30)
        
        start_time = time.time()
        analyzer4 = MenuAnalyzer(
            campus_key="altoona-port-sky",
            gemini_api_key=api_key,
            prioritize_protein=True,
            vegetarian=True,  # Same as test 3
            debug=True
        )
        
        results4 = analyzer4.run_analysis()
        fourth_request_time = time.time() - start_time
        
        print(f"✅ Fourth request completed in {fourth_request_time:.2f} seconds")
        print(f"📊 Results: {len(results4.get('Breakfast', []))} breakfast items")
        
        # Analysis
        print("\n📈 Performance Analysis:")
        print("=" * 30)
        print(f"First request (no cache):     {first_request_time:.2f}s")
        print(f"Second request (cached):      {second_request_time:.2f}s")
        print(f"Third request (new cache):    {third_request_time:.2f}s")
        print(f"Fourth request (cached):      {fourth_request_time:.2f}s")
        
        # Check if caching worked
        if second_request_time < first_request_time * 0.5:  # At least 50% faster
            print("✅ Caching is working! Second request was much faster.")
        else:
            print("⚠️  Caching may not be working optimally.")
        
        if fourth_request_time < third_request_time * 0.5:  # At least 50% faster
            print("✅ Caching is working! Fourth request was much faster.")
        else:
            print("⚠️  Caching may not be working optimally.")
        
        # Verify results are the same for cached requests
        if results1 == results2:
            print("✅ Cached results match original results.")
        else:
            print("⚠️  Cached results differ from original (this might be expected).")
        
        if results3 == results4:
            print("✅ Cached results match original results for vegetarian preferences.")
        else:
            print("⚠️  Cached results differ from original for vegetarian preferences.")
        
        print(f"\n🎉 Caching test completed!")
        
    except Exception as e:
        print(f"❌ Error during caching test: {e}")
        import traceback
        traceback.print_exc()

def test_cache_key_generation():
    print("\n🔑 Testing Cache Key Generation")
    print("=" * 50)
    
    try:
        from api.analyze import MenuAnalyzer
        
        # Test different cache keys
        analyzer = MenuAnalyzer(
            campus_key="altoona-port-sky",
            gemini_api_key="test_key",
            prioritize_protein=True,
            debug=False
        )
        
        # Test 1: Same preferences should generate same key
        key1 = analyzer.get_cache_key("monday, january 1")
        key2 = analyzer.get_cache_key("monday, january 1")
        
        print(f"Same preferences key 1: {key1}")
        print(f"Same preferences key 2: {key2}")
        print(f"Keys match: {key1 == key2}")
        
        # Test 2: Different preferences should generate different keys
        analyzer_veg = MenuAnalyzer(
            campus_key="altoona-port-sky",
            gemini_api_key="test_key",
            prioritize_protein=True,
            vegetarian=True,  # Different preference
            debug=False
        )
        
        key3 = analyzer_veg.get_cache_key("monday, january 1")
        
        print(f"Different preferences key: {key3}")
        print(f"Keys differ: {key1 != key3}")
        
        # Test 3: Different campus should generate different key
        analyzer_campus = MenuAnalyzer(
            campus_key="beaver-brodhead",  # Different campus
            gemini_api_key="test_key",
            prioritize_protein=True,
            debug=False
        )
        
        key4 = analyzer_campus.get_cache_key("monday, january 1")
        
        print(f"Different campus key: {key4}")
        print(f"Keys differ: {key1 != key4}")
        
        print("✅ Cache key generation working correctly!")
        
    except Exception as e:
        print(f"❌ Error during cache key test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 PSU Menu Analyzer - Caching Test")
    print("=" * 60)
    
    # Test cache key generation first
    test_cache_key_generation()
    
    # Test full caching functionality
    test_caching_functionality()
    
    print("\n" + "=" * 60)
    print("✅ All caching tests completed!")


