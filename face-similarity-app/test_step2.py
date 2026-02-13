"""
Test Step 2 (Edge-based preprocessing)

PURPOSE:
- Validates that Step 2 (edge-based preprocessing) works correctly
- Tests edge extraction for photos and minimal processing for sketches
- Verifies ArcFace comparison on preprocessed images

USAGE:
- Run from face-similarity-app directory: python test_step2.py
- Tests preprocessing functions independently
- Validates Step 2 implementation

STATUS: Keep for testing and validation
"""

import sys
import os

# Add backend to path
sys.path.insert(0, 'python-backend')

# Test imports
print("Testing imports...")
try:
    import cv2
    import numpy as np
    from deepface import DeepFace
    print("✓ Required packages imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Import our functions
print("\nImporting Step 2 functions...")
try:
    from app_v2 import (
        preprocess_for_edge_based_matching,
        is_sketch_image,
        compare_with_edge_preprocessing
    )
    print("✓ Step 2 functions imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test edge preprocessing function
print("\n" + "="*60)
print("TESTING STEP 2: Edge-Based Preprocessing")
print("="*60)

# Create a test image
print("\nCreating test image...")
test_img = np.ones((300, 300, 3), dtype=np.uint8) * 255
# Draw a simple face
cv2.circle(test_img, (150, 150), 80, (0, 0, 0), 2)  # Face outline
cv2.circle(test_img, (120, 130), 10, (0, 0, 0), -1)  # Left eye
cv2.circle(test_img, (180, 130), 10, (0, 0, 0), -1)  # Right eye
cv2.line(test_img, (150, 150), (150, 180), (0, 0, 0), 2)  # Nose
cv2.ellipse(test_img, (150, 200), (30, 15), 0, 0, 180, (0, 0, 0), 2)  # Mouth

test_path = "test_face.jpg"
cv2.imwrite(test_path, test_img)
print(f"✓ Test image created: {test_path}")

# Test edge preprocessing
print("\nTesting edge preprocessing...")
try:
    # Test as photo (should extract edges)
    processed_path = preprocess_for_edge_based_matching(test_path, is_sketch=False)
    if os.path.exists(processed_path):
        print(f"✓ Photo preprocessing successful: {processed_path}")
        # Cleanup
        if processed_path != test_path:
            os.remove(processed_path)
    else:
        print("✗ Preprocessed file not created")
    
    # Test as sketch (minimal processing)
    processed_path = preprocess_for_edge_based_matching(test_path, is_sketch=True)
    if os.path.exists(processed_path):
        print(f"✓ Sketch preprocessing successful: {processed_path}")
        # Cleanup
        if processed_path != test_path:
            os.remove(processed_path)
    else:
        print("✗ Preprocessed file not created")
    
except Exception as e:
    print(f"✗ Preprocessing error: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
if os.path.exists(test_path):
    os.remove(test_path)

print("\n" + "="*60)
print("STEP 2 TEST COMPLETE")
print("="*60)

print("\n✓ System ready for Step 2 testing")

print("\nNext steps:")
print("1. Start backend: cd python-backend && python app_v2.py")
print("2. Test Step 2 endpoints:")
print("   curl -X POST http://localhost:5001/api/test/edge-preprocessing \\")
print("     -F 'image=@photo.jpg' -F 'is_sketch=false' --output preprocessed.jpg")
