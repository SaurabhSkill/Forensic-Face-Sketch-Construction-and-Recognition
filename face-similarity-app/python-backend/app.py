import os
import tempfile
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from deepface import DeepFace
from database import Criminal, get_db, create_tables
import io
import traceback
import cv2
import numpy as np
import hashlib
import time


app = Flask(__name__)
CORS(app)

# Create database tables
create_tables()

# Global variables for optimization
MODEL_INITIALIZED = False
EMBEDDING_CACHE = {}
RESULT_CACHE = {}
CACHE_MAX_SIZE = 100


def initialize_models():
    """Pre-load DeepFace models to ensure consistent performance"""
    global MODEL_INITIALIZED
    if MODEL_INITIALIZED:
        return
    
    print("=" * 60)
    print("Initializing DeepFace models for consistent results...")
    print("=" * 60)
    
    try:
        # Create a dummy image to trigger model loading
        dummy_img = np.ones((224, 224, 3), dtype=np.uint8) * 128
        dummy_path = tempfile.mktemp(suffix='.jpg')
        cv2.imwrite(dummy_path, dummy_img)
        
        try:
            # Pre-load Facenet512 model
            print("Loading Facenet512 model...")
            DeepFace.represent(
                img_path=dummy_path,
                model_name='Facenet512',
                enforce_detection=False
            )
            print("[OK] Facenet512 model loaded successfully")
            
        except Exception as e:
            print(f"Warning during model initialization: {e}")
        
        finally:
            try:
                os.remove(dummy_path)
            except:
                pass
        
        MODEL_INITIALIZED = True
        print("=" * 60)
        print("Model initialization complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Model initialization error: {e}")
        MODEL_INITIALIZED = True  # Continue anyway


def get_file_hash(file_path: str) -> str:
    """Generate MD5 hash of file content for caching"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def normalize_image(image_path: str) -> str:
    """
    Normalize image for consistent comparison results
    - Resize to standard dimensions
    - Apply CLAHE for brightness normalization
    - Enhance contrast
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        
        # Resize to standard size (max 800px)
        height, width = img.shape[:2]
        max_dim = 800
        if max(height, width) > max_dim:
            scale = max_dim / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel (brightness normalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge channels
        lab = cv2.merge([l, a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Apply slight sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        img = cv2.filter2D(img, -1, kernel)
        
        # Save normalized image
        normalized_path = tempfile.mktemp(suffix='_normalized.jpg')
        cv2.imwrite(normalized_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        return normalized_path
        
    except Exception as e:
        print(f"Image normalization warning: {e}")
        return image_path


def get_face_embedding(image_path: str, use_cache: bool = True) -> np.ndarray:
    """
    Get face embedding with caching to ensure consistency
    """
    global EMBEDDING_CACHE
    
    # Check cache
    if use_cache:
        file_hash = get_file_hash(image_path)
        if file_hash and file_hash in EMBEDDING_CACHE:
            print(f"[OK] Using cached embedding")
            return EMBEDDING_CACHE[file_hash]
    
    # Generate embedding
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name='Facenet512',
            enforce_detection=False,
            align=True
        )
        
        if isinstance(result, list) and len(result) > 0:
            embedding = np.array(result[0]['embedding'])
        else:
            embedding = np.array(result['embedding'])
        
        # Cache the embedding
        if use_cache and file_hash:
            if len(EMBEDDING_CACHE) >= CACHE_MAX_SIZE:
                # Remove oldest entry
                EMBEDDING_CACHE.pop(next(iter(EMBEDDING_CACHE)))
            EMBEDDING_CACHE[file_hash] = embedding
        
        return embedding
        
    except Exception as e:
        print(f"Embedding generation error: {e}")
        raise


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    return float(similarity)


def optimized_face_comparison(sketch_path: str, photo_path: str, use_cache: bool = True) -> dict:
    """
    Optimized face comparison with:
    - Model pre-initialization
    - Image normalization
    - Embedding caching
    - Consistent distance calculation
    """
    global RESULT_CACHE
    
    # Ensure models are initialized
    initialize_models()
    
    start_time = time.time()
    print(f"\nStarting optimized face comparison...")
    
    # Check result cache
    cache_key = None
    if use_cache:
        hash1 = get_file_hash(sketch_path)
        hash2 = get_file_hash(photo_path)
        if hash1 and hash2:
            cache_key = f"{hash1}_{hash2}"
            if cache_key in RESULT_CACHE:
                cached_result = RESULT_CACHE[cache_key].copy()
                cached_result['from_cache'] = True
                cached_result['processing_time'] = round(time.time() - start_time, 3)
                print(f"[OK] Result retrieved from cache (instant)")
                return cached_result
    
    normalized_sketch = None
    normalized_photo = None
    
    try:
        # Normalize images
        print("Normalizing images...")
        normalized_sketch = normalize_image(sketch_path)
        normalized_photo = normalize_image(photo_path)
        
        # Get embeddings (with caching)
        print("Generating face embeddings...")
        embedding1 = get_face_embedding(normalized_sketch, use_cache=use_cache)
        embedding2 = get_face_embedding(normalized_photo, use_cache=use_cache)
        
        # Calculate similarity
        print("Calculating similarity...")
        similarity = cosine_similarity(embedding1, embedding2)
        
        # Convert to 0-1 range (cosine similarity is already -1 to 1, but typically 0 to 1 for faces)
        similarity = max(0.0, min(1.0, (similarity + 1) / 2))
        
        # Calculate distance (inverse of similarity)
        distance = 1.0 - similarity
        
        # Determine verification (more lenient for sketch-photo matching)
        verified = similarity > 0.55  # Adjusted threshold for sketch matching
        
        # Determine confidence
        if similarity > 0.75:
            confidence = 'high'
        elif similarity > 0.55:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        elapsed_time = time.time() - start_time
        print(f"[OK] Comparison completed in {elapsed_time:.3f} seconds")
        print(f"  Similarity: {similarity:.4f} ({similarity*100:.2f}%)")
        print(f"  Distance: {distance:.4f}")
        print(f"  Verified: {verified}")
        print(f"  Confidence: {confidence}")
        
        result = {
            'distance': float(distance),
            'similarity': float(similarity),
            'verified': bool(verified),
            'model_used': 'Facenet512',
            'metric_used': 'cosine',
            'confidence': confidence,
            'processing_time': round(elapsed_time, 3),
            'from_cache': False
        }
        
        # Cache the result
        if use_cache and cache_key:
            if len(RESULT_CACHE) >= CACHE_MAX_SIZE:
                RESULT_CACHE.pop(next(iter(RESULT_CACHE)))
            RESULT_CACHE[cache_key] = result.copy()
        
        return result
        
    except Exception as e:
        print(f"Comparison error: {e}")
        traceback.print_exc()
        
        elapsed_time = time.time() - start_time
        return {
            'distance': 1.0,
            'similarity': 0.0,
            'verified': False,
            'model_used': 'failed',
            'metric_used': 'none',
            'confidence': 'low',
            'processing_time': round(elapsed_time, 3),
            'error': str(e),
            'from_cache': False
        }
    
    finally:
        # Cleanup normalized images
        if normalized_sketch and normalized_sketch != sketch_path:
            try:
                os.remove(normalized_sketch)
            except:
                pass
        if normalized_photo and normalized_photo != photo_path:
            try:
                os.remove(normalized_photo)
            except:
                pass


def save_temp_file(file_storage) -> str:
    fd, path = tempfile.mkstemp(suffix='_' + file_storage.filename)
    os.close(fd)
    file_storage.save(path)
    return path


def save_bytes_to_temp(data: bytes, original_filename: str) -> str:
    fd, path = tempfile.mkstemp(suffix='_' + original_filename)
    os.close(fd)
    with open(path, 'wb') as f:
        f.write(data)
    return path


@app.route('/api/compare', methods=['POST'])
def compare_faces():
    try:
        if 'sketch' not in request.files or 'photo' not in request.files:
            return jsonify({"error": "Both 'sketch' and 'photo' files are required"}), 400

        sketch_file = request.files['sketch']
        photo_file = request.files['photo']

        sketch_path = save_temp_file(sketch_file)
        photo_path = save_temp_file(photo_file)

        try:
            # Use optimized face comparison
            result = optimized_face_comparison(sketch_path, photo_path, use_cache=True)
            
            return jsonify({
                "distance": result.get('distance', 1.0),
                "similarity": result.get('similarity', 0.0),
                "verified": result.get('verified', False),
                "model_used": result.get('model_used', 'unknown'),
                "confidence": result.get('confidence', 'low'),
                "metric_used": result.get('metric_used', 'unknown'),
                "processing_time": result.get('processing_time', 0),
                "from_cache": result.get('from_cache', False),
                "success": True
            })
        finally:
            # Cleanup temp files
            try:
                os.remove(sketch_path)
            except Exception:
                pass
            try:
                os.remove(photo_path)
            except Exception:
                pass
    except Exception as e:
        print("/api/compare error:\n" + traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all caches"""
    global RESULT_CACHE, EMBEDDING_CACHE
    result_count = len(RESULT_CACHE)
    embedding_count = len(EMBEDDING_CACHE)
    RESULT_CACHE.clear()
    EMBEDDING_CACHE.clear()
    return jsonify({
        "message": "Caches cleared successfully",
        "result_cache_cleared": result_count,
        "embedding_cache_cleared": embedding_count
    })


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    return jsonify({
        "result_cache_size": len(RESULT_CACHE),
        "embedding_cache_size": len(EMBEDDING_CACHE),
        "max_cache_size": CACHE_MAX_SIZE,
        "model_initialized": MODEL_INITIALIZED
    })


# Criminal Database API Endpoints

@app.route('/api/criminals', methods=['GET'])
def get_criminals():
    """Get all criminals from the database with detailed forensic profiles"""
    db = None
    try:
        db = next(get_db())
        criminals = db.query(Criminal).all()
        
        criminals_list = []
        for criminal in criminals:
            criminals_list.append({
                "id": criminal.id,
                "criminal_id": criminal.criminal_id,
                "status": criminal.status,
                "full_name": criminal.full_name,
                "aliases": criminal.aliases,
                "dob": criminal.dob,
                "sex": criminal.sex,
                "nationality": criminal.nationality,
                "ethnicity": criminal.ethnicity,
                "photo_filename": criminal.photo_filename,
                "appearance": criminal.appearance,
                "locations": criminal.locations,
                "summary": criminal.summary,
                "forensics": criminal.forensics,
                "evidence": criminal.evidence,
                "witness": criminal.witness,
                "created_at": criminal.created_at.isoformat(),
                "updated_at": criminal.updated_at.isoformat() if criminal.updated_at else None
            })
        
        return jsonify({"criminals": criminals_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals', methods=['POST'])
def add_criminal():
    """Add a new criminal to the database with detailed forensic profile"""
    db = None
    try:
        # Validate photo file
        if 'photo' not in request.files:
            return jsonify({"error": "Photo file is required"}), 400
        
        photo_file = request.files['photo']
        
        # Get the JSON data from the 'data' field
        data_json = request.form.get('data', '').strip()
        
        if not data_json:
            return jsonify({"error": "Profile data is required"}), 400
        
        # Parse the JSON data
        try:
            profile_data = json.loads(data_json)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Invalid JSON data: {str(e)}"}), 400
        
        # Validate required fields
        if not profile_data.get('criminal_id'):
            return jsonify({"error": "criminal_id is required"}), 400
        if not profile_data.get('full_name'):
            return jsonify({"error": "full_name is required"}), 400
        if not profile_data.get('status'):
            return jsonify({"error": "status is required"}), 400
        
        # Read photo data
        photo_data = photo_file.read()
        
        # Create new criminal record with detailed profile
        db = next(get_db())
        new_criminal = Criminal(
            criminal_id=profile_data.get('criminal_id'),
            status=profile_data.get('status'),
            full_name=profile_data.get('full_name'),
            aliases=profile_data.get('aliases'),
            dob=profile_data.get('dob'),
            sex=profile_data.get('sex'),
            nationality=profile_data.get('nationality'),
            ethnicity=profile_data.get('ethnicity'),
            photo_data=photo_data,
            photo_filename=photo_file.filename,
            appearance=profile_data.get('appearance'),
            locations=profile_data.get('locations'),
            summary=profile_data.get('summary'),
            forensics=profile_data.get('forensics'),
            evidence=profile_data.get('evidence'),
            witness=profile_data.get('witness')
        )
        
        db.add(new_criminal)
        db.commit()
        db.refresh(new_criminal)
        
        return jsonify({
            "message": "Criminal added successfully",
            "criminal": {
                "id": new_criminal.id,
                "criminal_id": new_criminal.criminal_id,
                "status": new_criminal.status,
                "full_name": new_criminal.full_name,
                "aliases": new_criminal.aliases,
                "dob": new_criminal.dob,
                "sex": new_criminal.sex,
                "nationality": new_criminal.nationality,
                "ethnicity": new_criminal.ethnicity,
                "photo_filename": new_criminal.photo_filename,
                "appearance": new_criminal.appearance,
                "locations": new_criminal.locations,
                "summary": new_criminal.summary,
                "forensics": new_criminal.forensics,
                "evidence": new_criminal.evidence,
                "witness": new_criminal.witness,
                "created_at": new_criminal.created_at.isoformat(),
                "updated_at": new_criminal.updated_at.isoformat() if new_criminal.updated_at else None
            }
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/<int:criminal_id>/photo', methods=['GET'])
def get_criminal_photo(criminal_id):
    """Get criminal photo by ID"""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        return send_file(
            io.BytesIO(criminal.photo_data),
            mimetype='image/jpeg',
            as_attachment=False
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/search', methods=['POST'])
def search_criminals():
    """Search for criminals using a sketch"""
    db = None
    try:
        if 'sketch' not in request.files:
            return jsonify({"error": "Sketch file is required"}), 400
        
        sketch_file = request.files['sketch']
        threshold = float(request.form.get('threshold', 0.6))  # Similarity threshold
        
        # Save sketch to temporary file
        sketch_path = save_temp_file(sketch_file)
        
        try:
            # Get all criminals from database
            db = next(get_db())
            criminals = db.query(Criminal).all()
            
            matches = []
            
            # Compare sketch with each criminal
            for criminal in criminals:
                try:
                    # Save criminal photo bytes to a temporary file
                    criminal_photo_path = save_bytes_to_temp(
                        criminal.photo_data,
                        criminal.photo_filename or 'criminal.jpg'
                    )
                    
                    try:
                        # Use optimized face comparison for database search
                        result = optimized_face_comparison(sketch_path, criminal_photo_path, use_cache=True)
                        
                        similarity_score = result.get('similarity', 0.0)
                        distance = result.get('distance', 1.0)
                        verified = result.get('verified', False)
                        
                        # Lower threshold for sketch matching (more lenient)
                        sketch_threshold = max(0.3, threshold * 0.6)
                        
                        # If similarity is above threshold, add to matches
                        if verified or similarity_score >= sketch_threshold:
                            matches.append({
                                "criminal": {
                                    "id": criminal.id,
                                    "criminal_id": criminal.criminal_id,
                                    "status": criminal.status,
                                    "full_name": criminal.full_name,
                                    "aliases": criminal.aliases,
                                    "dob": criminal.dob,
                                    "sex": criminal.sex,
                                    "nationality": criminal.nationality,
                                    "ethnicity": criminal.ethnicity,
                                    "appearance": criminal.appearance,
                                    "locations": criminal.locations,
                                    "summary": criminal.summary,
                                    "forensics": criminal.forensics,
                                    "evidence": criminal.evidence,
                                    "witness": criminal.witness,
                                    "created_at": criminal.created_at.isoformat()
                                },
                                "similarity_score": float(similarity_score),
                                "distance": float(distance),
                                "verified": bool(verified),
                                "model_used": result.get('model_used', 'unknown'),
                                "confidence": result.get('confidence', 'low')
                            })
                    
                    finally:
                        # Clean up criminal photo temp file
                        try:
                            os.remove(criminal_photo_path)
                        except:
                            pass
                            
                except Exception as e:
                    print(f"Error comparing with criminal {criminal.id}: {e}")
                    continue
            
            # Sort by similarity score (highest first)
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return jsonify({
                "matches": matches,
                "total_matches": len(matches),
                "threshold_used": threshold
            })
            
        finally:
            # Clean up sketch temp file
            try:
                os.remove(sketch_path)
            except:
                pass
                
    except Exception as e:
        print("/api/criminals/search error:\n" + traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/<int:criminal_id>', methods=['GET'])
def get_criminal_by_id(criminal_id):
    """Get a single criminal's detailed profile by ID"""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        return jsonify({
            "criminal": {
                "id": criminal.id,
                "criminal_id": criminal.criminal_id,
                "status": criminal.status,
                "full_name": criminal.full_name,
                "aliases": criminal.aliases,
                "dob": criminal.dob,
                "sex": criminal.sex,
                "nationality": criminal.nationality,
                "ethnicity": criminal.ethnicity,
                "photo_filename": criminal.photo_filename,
                "appearance": criminal.appearance,
                "locations": criminal.locations,
                "summary": criminal.summary,
                "forensics": criminal.forensics,
                "evidence": criminal.evidence,
                "witness": criminal.witness,
                "created_at": criminal.created_at.isoformat(),
                "updated_at": criminal.updated_at.isoformat() if criminal.updated_at else None
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/<int:criminal_id>', methods=['PUT'])
def update_criminal(criminal_id):
    """Update an existing criminal's profile"""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        # Get the JSON data from the 'data' field
        data_json = request.form.get('data', '').strip()
        
        if not data_json:
            return jsonify({"error": "Profile data is required"}), 400
        
        # Parse the JSON data
        try:
            profile_data = json.loads(data_json)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Invalid JSON data: {str(e)}"}), 400
        
        # Update fields if provided
        if profile_data.get('criminal_id'):
            criminal.criminal_id = profile_data.get('criminal_id')
        if profile_data.get('status'):
            criminal.status = profile_data.get('status')
        if profile_data.get('full_name'):
            criminal.full_name = profile_data.get('full_name')
        if 'aliases' in profile_data:
            criminal.aliases = profile_data.get('aliases')
        if 'dob' in profile_data:
            criminal.dob = profile_data.get('dob')
        if 'sex' in profile_data:
            criminal.sex = profile_data.get('sex')
        if 'nationality' in profile_data:
            criminal.nationality = profile_data.get('nationality')
        if 'ethnicity' in profile_data:
            criminal.ethnicity = profile_data.get('ethnicity')
        if 'appearance' in profile_data:
            criminal.appearance = profile_data.get('appearance')
        if 'locations' in profile_data:
            criminal.locations = profile_data.get('locations')
        if 'summary' in profile_data:
            criminal.summary = profile_data.get('summary')
        if 'forensics' in profile_data:
            criminal.forensics = profile_data.get('forensics')
        if 'evidence' in profile_data:
            criminal.evidence = profile_data.get('evidence')
        if 'witness' in profile_data:
            criminal.witness = profile_data.get('witness')
        
        # Update photo if provided
        if 'photo' in request.files:
            photo_file = request.files['photo']
            criminal.photo_data = photo_file.read()
            criminal.photo_filename = photo_file.filename
        
        db.commit()
        db.refresh(criminal)
        
        return jsonify({
            "message": "Criminal updated successfully",
            "criminal": {
                "id": criminal.id,
                "criminal_id": criminal.criminal_id,
                "status": criminal.status,
                "full_name": criminal.full_name,
                "aliases": criminal.aliases,
                "dob": criminal.dob,
                "sex": criminal.sex,
                "nationality": criminal.nationality,
                "ethnicity": criminal.ethnicity,
                "photo_filename": criminal.photo_filename,
                "appearance": criminal.appearance,
                "locations": criminal.locations,
                "summary": criminal.summary,
                "forensics": criminal.forensics,
                "evidence": criminal.evidence,
                "witness": criminal.witness,
                "created_at": criminal.created_at.isoformat(),
                "updated_at": criminal.updated_at.isoformat() if criminal.updated_at else None
            }
        })
        
    except Exception as e:
        if db:
            db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/<int:criminal_id>', methods=['DELETE'])
def delete_criminal(criminal_id):
    """Delete a criminal from the database"""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        db.delete(criminal)
        db.commit()
        
        return jsonify({"message": "Criminal deleted successfully"})
        
    except Exception as e:
        if db:
            db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("FORENSIC FACE RECOGNITION BACKEND - OPTIMIZED VERSION")
    print("=" * 60)
    
    # Initialize models on startup
    initialize_models()
    
    port = int(os.environ.get('PORT', '5001'))
    print(f"\n[OK] Server ready on http://localhost:{port}")
    print("=" * 60)
    print("\nOptimizations enabled:")
    print("  [OK] Model pre-initialization")
    print("  [OK] Image normalization (CLAHE)")
    print("  [OK] Embedding caching")
    print("  [OK] Result caching")
    print("  [OK] Consistent similarity calculation")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
