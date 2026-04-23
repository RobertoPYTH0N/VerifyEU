<<<<<<< HEAD
# VerifyEU

A web application for registering and verifying the authenticity of digital images using cryptographic hashing, image fingerprinting, and Ed25519 digital signatures.

## Overview

The VerifyEU enables users to:
- **Register** images with cryptographic integrity verification
- **Check provenance** of images by finding similar registered images
- **Verify authenticity** through digital signatures and hash-based similarity matching
- **Track ownership** of media assets with user authentication

This system is designed for organizations, journalists, and content creators who need to establish a verifiable chain of custody for digital media.

## Key Features

✓ **User Authentication** - Secure login/registration with bcrypt password hashing  
✓ **Image Registration** - Store images with SHA-256 fingerprints and Ed25519 signatures  
✓ **Similarity Search** - Find matching images using perceptual hashing (pHash, dHash, aHash)  
✓ **Side-by-Side Comparison** - View queried image alongside best match results  
✓ **Batch Upload** - Register multiple images in one session  
✓ **Ownership Tracking** - Each image records which user registered it  
✓ **Vector Search** - Fast similarity queries using pgvector extension  

## Technology Stack

### Frontend
- **React 18** - UI framework
- **CSS3** - Responsive styling with blue color scheme
- **Fetch API** - REST client

### Backend
- **Python 3** - Server logic
- **Flask** - REST API framework
- **psycopg** - PostgreSQL driver
- **PyNaCl** - Ed25519 cryptography
- **imagehash** - Perceptual hashing (pHash, dHash, aHash)
- **Pillow** - Image processing
- **bcrypt** - Password hashing

### Database
- **PostgreSQL 14+** - Data persistence
- **pgvector** - Vector similarity search
- **BYTEA** - Binary image storage

## Architecture

```
Frontend (React)
    ↓
Flask REST API (main.py, api.py)
    ↓
PostgreSQL Database
    ├── users (user_id, username, password_hash)
    ├── manifests (sha256, manifest_json, signature_hex, phash_vector, dhash_vector, ahash_vector, image_data)
    └── user_registrations (user_id, manifest_sha256)
```

## Setup

### Prerequisites
- Python 3.10+
- Node.js 16+
- PostgreSQL 14+ with pgvector extension
- `.env` file with database and cryptography credentials

### Environment Variables

Create a `.env` file in the project root:

```env
POSTGRES_URL=postgresql://user:password@localhost/media_provenance
VERIFIER_PRIVATE_KEY_HEX=your_ed25519_private_key_hex
VERIFIER_KEY_ID=key-2026-01
```

### Database Setup

1. Create PostgreSQL database:
```sql
CREATE DATABASE media_provenance;
```

2. Enable pgvector extension and create tables:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    last_login TIMESTAMP
);

CREATE TABLE manifests (
    id SERIAL PRIMARY KEY,
    sha256 VARCHAR(64) UNIQUE NOT NULL,
    manifest_json JSONB NOT NULL,
    signature_hex TEXT NOT NULL,
    key_id VARCHAR(50) NOT NULL,
    phash_vector vector(64),
    dhash_vector vector(64),
    ahash_vector vector(64),
    image_data BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_registrations (
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
    manifest_sha256 VARCHAR(64) NOT NULL REFERENCES manifests(sha256),
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, manifest_sha256)
);

-- Create HNSW index for fast similarity search
CREATE INDEX idx_phash_vector ON manifests USING hnsw (phash_vector vector_cosine_ops);
CREATE INDEX idx_dhash_vector ON manifests USING hnsw (dhash_vector vector_cosine_ops);
CREATE INDEX idx_ahash_vector ON manifests USING hnsw (ahash_vector vector_cosine_ops);
```

### Backend Setup

```bash
# Install dependencies
pip install python-dotenv psycopg[binary] pillow imagehash bcrypt pynacl flask flask-cors

# Run Flask server
python api.py
# Server runs on http://localhost:5000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
# Frontend runs on http://localhost:3000
```

## Usage

### Register an Image

1. Click **"Register"** in the home view
2. Login or create an account
3. Upload one or more images
4. Images are registered with:
   - SHA-256 hash for integrity
   - Perceptual hashes (pHash, dHash, aHash) for similarity
   - Ed25519 digital signature for authenticity
   - Binary image storage in database

### Check Image Provenance

1. Click **"Check Provenance"** in the home view
2. Select a query image
3. System finds closest matching registered images
4. Results show:
   - Side-by-side comparison (query image + best match)
   - Similarity percentage
   - Confidence tier
   - Creator/registrant information
   - Registration date
   - Additional matches

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with username/password
- `POST /api/auth/register` - Register new user
- `POST /api/auth/logout` - Logout current user

### Media Management
- `POST /api/media/register` - Register image file
- `POST /api/media/check` - Check provenance of image

### System
- `GET /api/health` - Health check

## Manifest Structure

Each registered image creates a manifest containing:

```json
{
    "filename": "example.jpg",
    "creator_id": "username",
    "timestamp": "2026-04-19T10:30:00Z",
    "algorithm_signature": "Ed25519",
    "sha256": "abc123...",
    "phash": ["0xff00ff00..."],
    "dhash": ["0xff00ff00..."],
    "ahash": ["0xff00ff00..."]
}
```

The manifest is canonicalized and signed with Ed25519, creating an immutable proof of registration.

## Similarity Search

### Confidence Tiers (Outdated)
- **Tier 1**: avg_distance < 0.1 (Very high similarity)
- **Tier 2**: avg_distance < 0.2 (High similarity)  
- **Tier 3**: avg_distance < 0.3 (Moderate similarity)
- **Tier 4**: avg_distance ≥ 0.3 (Low similarity)

### How It Works (Outdated)
1. Compute perceptual hashes for query image
2. Convert hashes to 64-dimensional vectors
3. Query pgvector using cosine distance
4. Average distances across pHash, dHash, aHash
5. Return results sorted by similarity

## Project Structure

```
AI_Policy_Hackathon/
├── main.py                    # Core business logic
├── api.py                     # Flask REST API
├── hash_compute.py            # Image hashing functions
├── generate_keys.py           # Ed25519 key generation
├── frontend/
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── App.css           # Styling
│   │   └── components/
│   │       ├── LoginModal.js
│   │       ├── FileUploader.js
│   │       └── ResultsDisplay.js
│   └── package.json
├── test_images/              # Sample images for testing
├── to_register/              # Batch registration directory
└── .env                       # Environment variables
```

## Development

### Running Tests

Upload test images:
```bash
# Manual registration
python main.py

# Or register from directory
python -c "from main import register_all_from_directory; register_all_from_directory('test_images')"
```

### Debugging

Enable diagnostic logging from SDK:
```python
from main import find_closest_match_bruteforce

# This includes latency and request metrics
matches = find_closest_match_bruteforce('query_image.jpg')
```

**Project Status**: Active Development (AI Policy Hackathon 2026)
=======
# VerifyEU
>>>>>>> ee7ec84b317c290a72f9d01ed31e004b31cde1f0
