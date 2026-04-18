"""
Flask API wrapper for Media Provenance System
Exposes the main functions as REST endpoints
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from werkzeug.utils import secure_filename

# Import main module functions
import main

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = '/tmp/media_provenance_uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tif', 'tiff'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "API is running"})


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """
    Login endpoint
    Expected JSON: {"username": "...", "password": "..."}
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400
    
    result = main.login(username, password)
    
    if result["status"] == "success":
        # Set the current_user in main module
        main.current_user = {
            "user_id": result["user_id"],
            "username": result["username"]
        }
        return jsonify({"status": "success", "user": {"username": result["username"], "user_id": result["user_id"]}}), 200
    else:
        return jsonify({"status": "error", "message": result.get("message", "Login failed")}), 401


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """
    Register new user endpoint
    Expected JSON: {"username": "...", "password": "..."}
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400
    
    result = main.register_user(username, password)
    
    if result["status"] == "success":
        return jsonify({"status": "success", "message": "User registered successfully"}), 201
    else:
        return jsonify({"status": "error", "message": result.get("message", "Registration failed")}), 400


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Logout endpoint"""
    main.logout()
    return jsonify({"status": "success", "message": "Logged out"}), 200


@app.route('/api/media/register', methods=['POST'])
def api_register_media():
    """
    Register media file
    Expected: multipart/form-data with 'file' field
    """
    if not main.current_user:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "File type not allowed"}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    try:
        result = main.register_media(file_path)
        
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if result["status"] == "registered":
            return jsonify({
                "status": "success",
                "message": "Image registered successfully",
                "data": {
                    "sha256": result["sha256"],
                    "asset_id": result["asset_id"],
                    "filename": result.get("manifest", {}).get("filename", filename),
                    "created_at": result["created_at"]
                }
            }), 200
        elif result["status"] == "duplicate":
            return jsonify({
                "status": "duplicate",
                "message": "Image already registered",
                "data": {
                    "sha256": result["sha256"],
                    "asset_id": result["asset_id"],
                    "created_at": result["created_at"]
                }
            }), 200
        else:
            return jsonify({"status": "error", "message": result.get("message", "Registration failed")}), 400
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/media/check', methods=['POST'])
def api_check_provenance():
    """
    Check image provenance using bruteforce search
    Expected: multipart/form-data with 'file' field
    """
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "File type not allowed"}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    try:
        matches = main.find_closest_match_bruteforce(file_path)
        
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if not matches:
            return jsonify({
                "status": "success",
                "message": "No matches found in database",
                "data": {
                    "matches": [],
                    "total_in_db": 0
                }
            }), 200
        
        # Format results
        top_match = matches[0] if matches else None
        
        return jsonify({
            "status": "success",
            "message": f"Found {len(matches)} matches",
            "data": {
                "top_match": {
                    "filename": top_match["filename"],
                    "similarity_score": top_match["similarity_score"],
                    "confidence_tier": top_match["confidence_tier"],
                    "creator_id": top_match["creator_id"],
                    "sha256": top_match["sha256"],
                    "created_at": top_match["created_at"],
                    "phash_distance": top_match["phash_distance"],
                    "dhash_distance": top_match["dhash_distance"],
                    "ahash_distance": top_match["ahash_distance"],
                    "avg_distance": top_match["avg_distance"],
                    "image_base64": top_match.get("image_base64")
                } if top_match else None,
                "all_matches": [
                    {
                        "rank": i + 1,
                        "filename": m["filename"],
                        "similarity_score": m["similarity_score"],
                        "confidence_tier": m["confidence_tier"],
                        "creator_id": m["creator_id"],
                        "sha256": m["sha256"],
                        "avg_distance": m["avg_distance"],
                        "image_base64": m.get("image_base64")
                    }
                    for i, m in enumerate(matches[:20])  # Top 20
                ],
                "total_matches": len(matches)
            }
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/status', methods=['GET'])
def api_status():
    """Get current auth status"""
    if main.current_user:
        return jsonify({
            "authenticated": True,
            "user": main.current_user
        }), 200
    else:
        return jsonify({
            "authenticated": False,
            "user": None
        }), 200


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
