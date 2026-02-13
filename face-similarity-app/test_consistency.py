"""
Test script to verify face recognition consistency

PURPOSE:
- Tests if same inputs produce same outputs (deterministic behavior)
- Validates that face matching results are stable across multiple runs
- Ensures no randomness in the comparison pipeline

USAGE:
- Run after starting backend server
- Compares same images multiple times
- Checks if results are identical

STATUS: Keep for testing and validation
"""

import requests
import json
import sys

def test_consistency(sketch_path, photo_path, num_tests=5):
    """
    Test if the same inputs produce consistent results
    """
    print(f"\n{'='*60}")
    print("CONSISTENCY TEST")
    print(f"{'='*60}")
    print(f"Testing {num_tests} times with same inputs...")
    print(f"Sketch: {sketch_path}")
    print(f"Photo: {photo_path}")
    print()
    
    results = []
    
    for i in range(num_tests):
        print(f"Test {i+1}/{num_tests}...", end=" ")
        
        try:
            with open(sketch_path, 'rb') as sketch_file, open(photo_path, 'rb') as photo_file:
                files = {
                    'sketch': sketch_file,
                    'photo': photo_file
                }
                
                response = requests.post('http://localhost:5001/api/compare', files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    results.append(result)
                    print(f"✓ Distance: {result['distance']:.6f}, Similarity: {result['similarity']*100:.2f}%")
                else:
                    print(f"✗ Error: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"✗ Exception: {e}")
            return False
    
    # Check consistency
    print(f"\n{'='*60}")
    print("CONSISTENCY CHECK")
    print(f"{'='*60}")
    
    if len(results) < 2:
        print("✗ Not enough results to check consistency")
        return False
    
    all_consistent = True
    
    # Check distance consistency
    distances = [r['distance'] for r in results]
    if len(set(distances)) == 1:
        print(f"✓ Distance is consistent: {distances[0]:.6f}")
    else:
        print(f"✗ Distance varies: {distances}")
        all_consistent = False
    
    # Check similarity consistency
    similarities = [r['similarity'] for r in results]
    if len(set(similarities)) == 1:
        print(f"✓ Similarity is consistent: {similarities[0]*100:.2f}%")
    else:
        print(f"✗ Similarity varies: {[f'{s*100:.2f}%' for s in similarities]}")
        all_consistent = False
    
    # Check model_verified consistency
    verified_values = [r.get('model_verified', False) for r in results]
    if len(set(verified_values)) == 1:
        print(f"✓ Model verified is consistent: {verified_values[0]}")
    else:
        print(f"✗ Model verified varies: {verified_values}")
        all_consistent = False
    
    # Check confidence_level consistency
    confidence_levels = [r.get('confidence_level', 'unknown') for r in results]
    if len(set(confidence_levels)) == 1:
        print(f"✓ Confidence level is consistent: {confidence_levels[0]}")
    else:
        print(f"✗ Confidence level varies: {confidence_levels}")
        all_consistent = False
    
    # Check confidence_score consistency
    confidence_scores = [r.get('confidence_score', 0.0) for r in results]
    if len(set(confidence_scores)) == 1:
        print(f"✓ Confidence score is consistent: {confidence_scores[0]:.1f}%")
    else:
        print(f"✗ Confidence score varies: {[f'{s:.1f}%' for s in confidence_scores]}")
        all_consistent = False
    
    print(f"\n{'='*60}")
    if all_consistent:
        print("✓✓✓ ALL TESTS PASSED - SYSTEM IS CONSISTENT ✓✓✓")
    else:
        print("✗✗✗ CONSISTENCY ISSUES DETECTED ✗✗✗")
    print(f"{'='*60}\n")
    
    return all_consistent


def test_cache():
    """
    Test if cache returns same results as fresh computation
    """
    print(f"\n{'='*60}")
    print("CACHE TEST")
    print(f"{'='*60}")
    
    # Clear cache first
    print("Clearing cache...", end=" ")
    try:
        response = requests.post('http://localhost:5001/api/cache/clear')
        if response.status_code == 200:
            print("✓")
        else:
            print(f"✗ Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False
    
    # Make first request (no cache)
    print("First request (no cache)...", end=" ")
    try:
        with open('test_sketch.jpg', 'rb') as sketch_file, open('test_photo.jpg', 'rb') as photo_file:
            files = {'sketch': sketch_file, 'photo': photo_file}
            response = requests.post('http://localhost:5001/api/compare', files=files)
            
            if response.status_code == 200:
                result1 = response.json()
                print(f"✓ from_cache={result1.get('from_cache', False)}")
            else:
                print(f"✗ Error: {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False
    
    # Make second request (from cache)
    print("Second request (from cache)...", end=" ")
    try:
        with open('test_sketch.jpg', 'rb') as sketch_file, open('test_photo.jpg', 'rb') as photo_file:
            files = {'sketch': sketch_file, 'photo': photo_file}
            response = requests.post('http://localhost:5001/api/compare', files=files)
            
            if response.status_code == 200:
                result2 = response.json()
                print(f"✓ from_cache={result2.get('from_cache', False)}")
            else:
                print(f"✗ Error: {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False
    
    # Compare results
    print(f"\n{'='*60}")
    print("CACHE CONSISTENCY CHECK")
    print(f"{'='*60}")
    
    if result1['distance'] == result2['distance']:
        print(f"✓ Distance matches: {result1['distance']:.6f}")
    else:
        print(f"✗ Distance mismatch: {result1['distance']:.6f} vs {result2['distance']:.6f}")
        return False
    
    if result1['similarity'] == result2['similarity']:
        print(f"✓ Similarity matches: {result1['similarity']*100:.2f}%")
    else:
        print(f"✗ Similarity mismatch: {result1['similarity']*100:.2f}% vs {result2['similarity']*100:.2f}%")
        return False
    
    print(f"\n{'='*60}")
    print("✓✓✓ CACHE TEST PASSED ✓✓✓")
    print(f"{'='*60}\n")
    
    return True


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python test_consistency.py <sketch_path> <photo_path> [num_tests]")
        print("Example: python test_consistency.py sketch.jpg photo.jpg 10")
        sys.exit(1)
    
    sketch_path = sys.argv[1]
    photo_path = sys.argv[2]
    num_tests = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    # Run consistency test
    consistency_passed = test_consistency(sketch_path, photo_path, num_tests)
    
    # Run cache test (optional, requires test files)
    # cache_passed = test_cache()
    
    if consistency_passed:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)
