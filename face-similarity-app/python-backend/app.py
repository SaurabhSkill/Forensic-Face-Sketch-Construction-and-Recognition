import os
import tempfile
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
    """Get all criminals from the database"""
    try:
        db = next(get_db())
        criminals = db.query(Criminal).all()
        
        criminals_list = []
        for criminal in criminals:
            criminals_list.append({
                "id": criminal.id,
                "name": criminal.name,
                "crime": criminal.crime,
                "description": criminal.description,
                "photo_filename": criminal.photo_filename,
                "created_at": criminal.created_at.isoformat()
            })
        
        return jsonify({"criminals": criminals_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/criminals', methods=['POST'])
def add_criminal():
    """Add a new criminal to the database"""
    try:
        if 'photo' not in request.files:
            return jsonify({"error": "Photo file is required"}), 400
        
        photo_file = request.files['photo']
        name = request.form.get('name', '').strip()
        crime = request.form.get('crime', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name or not crime:
            return jsonify({"error": "Name and crime are required"}), 400
        
        # Read photo data
        photo_data = photo_file.read()
        
        # Create new criminal record
        db = next(get_db())
        new_criminal = Criminal(
            name=name,
            crime=crime,
            description=description,
            photo_data=photo_data,
            photo_filename=photo_file.filename
        )
        
        db.add(new_criminal)
        db.commit()
        db.refresh(new_criminal)
        
        return jsonify({
            "message": "Criminal added successfully",
            "criminal": {
                "id": new_criminal.id,
                "name": new_criminal.name,
                "crime": new_criminal.crime,
                "description": new_criminal.description,
                "created_at": new_criminal.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/criminals/<int:criminal_id>/photo', methods=['GET'])
def get_criminal_photo(criminal_id):
    """Get criminal photo by ID"""
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


@app.route('/api/criminals/search', methods=['POST'])
def search_criminals():
    """Search for criminals using a sketch"""
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
                                    "name": criminal.name,
                                    "crime": criminal.crime,
                                    "description": criminal.description,
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


@app.route('/api/criminals/<int:criminal_id>', methods=['DELETE'])
def delete_criminal(criminal_id):
    """Delete a criminal from the database"""
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        db.delete(criminal)
        db.commit()
        
        return jsonify({"message": "Criminal deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=False)


