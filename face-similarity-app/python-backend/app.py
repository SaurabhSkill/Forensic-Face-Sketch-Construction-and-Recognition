import os
import tempfile
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from deepface import DeepFace
from database import Criminal, get_db, create_tables
import io


app = Flask(__name__)
CORS(app)

# Create database tables
create_tables()


def save_temp_file(file_storage) -> str:
    fd, path = tempfile.mkstemp(suffix='_' + file_storage.filename)
    os.close(fd)
    file_storage.save(path)
    return path

# Save raw bytes to a temporary file and return the path
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
            # SFace is light-weight and robust; uses onnxruntime (CPU) and OpenCV backend
            result = DeepFace.verify(
                img1_path=sketch_path,
                img2_path=photo_path,
                model_name='Facenet512',
                detector_backend='opencv',
                enforce_detection=False,
                align=True,
                distance_metric='cosine'
            )

            # DeepFace returns 'distance' and 'verified'
            return jsonify({
                "distance": float(result.get('distance', -1)),
                "verified": bool(result.get('verified', False))
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
        return jsonify({"error": str(e)}), 500


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
                        # Compare sketch with criminal photo
                        result = DeepFace.verify(
                            img1_path=sketch_path,
                            img2_path=criminal_photo_path,
                            model_name='Facenet512',
                            detector_backend='opencv',
                            enforce_detection=False,
                            align=True,
                            distance_metric='cosine'
                        )
                        
                        distance = result['distance']
                        verified = result['verified']
                        
                        # If similarity is above threshold, add to matches
                        if verified or distance <= threshold:
                            similarity_score = 1 - distance  # Convert distance to similarity
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
                                "verified": bool(verified)
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
    port = int(os.environ.get('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=False)


