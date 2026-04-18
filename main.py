
import os
from dotenv import load_dotenv
import psycopg
import json
import base64
from datetime import datetime, timezone
from nacl.signing import SigningKey
import bcrypt
import uuid

import hash_compute as hc

# Load environment variables from .env file
load_dotenv()

# Global variable to track current logged-in user
current_user = None


# ========== AUTHENTICATION FUNCTIONS ==========

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def register_user(username: str, password: str, db_url: str = None) -> dict:
    """
    Register a new user in the system.
    
    Args:
        username: Username for the account
        password: Password (will be hashed with bcrypt)
        db_url: PostgreSQL connection string
    
    Returns:
        dict with status and user_id
    """
    if len(password) < 8:
        return {"status": "error", "message": "Password must be at least 8 characters"}
    
    try:
        conn = get_db_connection(db_url)
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"status": "error", "message": f"Username '{username}' already exists"}
        
        # Generate unique user_id
        user_id = f"user-{uuid.uuid4().hex[:12]}"
        
        # Hash password and insert
        password_hash = hash_password(password)
        cursor.execute(
            """
            INSERT INTO users (user_id, username, password_hash)
            VALUES (%s, %s, %s)
            """,
            (user_id, username, password_hash)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"  ✓ User '{username}' registered successfully (ID: {user_id})")
        return {"status": "success", "user_id": user_id, "username": username}
        
    except Exception as e:
        print(f"  ✗ Registration failed: {e}")
        return {"status": "error", "message": str(e)}


def login(username: str, password: str, db_url: str = None) -> dict:
    """
    Authenticate user and return user info.
    
    Args:
        username: Username
        password: Password (will be verified against hash)
        db_url: PostgreSQL connection string
    
    Returns:
        dict with status and user_id if successful
    """
    try:
        conn = get_db_connection(db_url)
        cursor = conn.cursor()
        
        # Find user
        cursor.execute(
            """
            SELECT user_id, password_hash FROM users WHERE username = %s
            """,
            (username,)
        )
        
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return {"status": "error", "message": "Invalid username or password"}
        
        user_id, password_hash = result
        
        # Verify password
        if not verify_password(password, password_hash):
            cursor.close()
            conn.close()
            return {"status": "error", "message": "Invalid username or password"}
        
        # Update last login
        cursor.execute(
            "UPDATE users SET last_login = now() WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "user_id": user_id,
            "username": username,
            "message": f"Welcome, {username}!"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


def auth_menu():
    """
    Display authentication menu and handle login/registration.
    Sets global current_user variable.
    """
    global current_user
    
    while True:
        print("\n" + "="*100)
        print("AUTHENTICATION - MEDIA PROVENANCE SYSTEM")
        print("="*100)
        print("\n1. Login")
        print("2. Create new account")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            username = input("  Username: ").strip()
            password = input("  Password: ").strip()
            
            result = login(username, password)
            
            if result["status"] == "success":
                current_user = {
                    "user_id": result["user_id"],
                    "username": result["username"]
                }
                print(f"\n  ✓ {result['message']}")
                return True
            else:
                print(f"\n  ✗ {result['message']}")
        
        elif choice == "2":
            username = input("  Choose username: ").strip()
            password = input("  Choose password (min 8 chars): ").strip()
            password_confirm = input("  Confirm password: ").strip()
            
            if password != password_confirm:
                print("  ✗ Passwords don't match")
                continue
            
            result = register_user(username, password)
            
            if result["status"] == "success":
                print(f"\n  ✓ Account created! Now log in with your credentials")
            else:
                print(f"  ✗ {result['message']}")
        
        elif choice == "3":
            print("  Exiting...")
            return False
        
        else:
            print("  Invalid choice")


def logout():
    """Log out current user."""
    global current_user
    current_user = None
    print("  ✓ Logged out")


def create_manifest(creator_id: str, filename: str, file_path: str) -> dict:
    """
    Create a manifest for media registration.
    Computes all hashes using hash_compute.
    
    Args:
        creator_id: Organization/team ID
        filename: Original filename
        file_path: Path to media file
    
    Returns:
        Manifest dict with hashes and metadata
    """
    hash_result = hc.compute_hashes_by_type(file_path)
    
    # Skip video files for now
    if hash_result["media_type"] == "video":
        raise ValueError("Video processing not yet implemented")
    
    manifest = {
        "ahash": hash_result["ahash"],
        "algorithm_hash": "SHA-256",
        "algorithm_signature": "Ed25519",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "creator_id": creator_id,
        "dhash": hash_result["dhash"],
        "filename": filename,
        "media_type": hash_result["media_type"],
        "phash": hash_result["phash"],
        "sha256": hash_result["sha256"]
    }

    return manifest


def get_db_connection(db_url: str = None):
    """
    Connect to PostgreSQL database.
    
    Args:
        db_url: Connection string (e.g., "postgres://user:pass@localhost/crypto")
                If None, reads from POSTGRES_URL environment variable
    
    Returns:
        psycopg connection object
    """
    if db_url is None:
        db_url = os.getenv("POSTGRES_URL")
    
    if db_url is None:
        raise ValueError("POSTGRES_URL not set and no db_url provided")
    
    conn = psycopg.connect(db_url)
    return conn


def register_media(
    file_path: str,
    creator_id: str = None,
    signing_key_hex: str = None,
    key_id: str = "key-2026-01",
    db_url: str = None
) -> dict:
    """
    Register a file in the database with Ed25519 signature.
    Requires authenticated user. Checks for duplicates by SHA-256 before registering.
    Tracks which user uploaded the image.
    
    Args:
        file_path: Path to media file to register
        creator_id: Organization/team ID (optional, uses current user if not provided)
        signing_key_hex: Ed25519 private key as hex string
        key_id: Public key identifier (e.g., "key-2026-01")
        db_url: PostgreSQL connection string
    
    Returns:
        dict with registration details or status if already exists
    """
    # Check authentication
    if not current_user:
        print("✗ You must be logged in to register media")
        return {"status": "error", "message": "Not authenticated"}
    
    # Use current user info as creator_id
    if creator_id is None:
        creator_id = current_user["username"]
    
    # Validate file exists
    if not os.path.isfile(file_path):
        print(f"✗ File not found: {file_path}")
        return {"status": "error", "message": "File not found"}
    
    filename = os.path.basename(file_path)
    
    # Get signing key
    if signing_key_hex is None:
        signing_key_hex = os.getenv("VERIFIER_PRIVATE_KEY_HEX")
    
    if signing_key_hex is None:
        raise ValueError("VERIFIER_PRIVATE_KEY_HEX not set and no signing_key_hex provided")
    
    signing_key = SigningKey(bytes.fromhex(signing_key_hex))
    
    # Compute SHA-256 to check for duplicates
    print(f"  Computing SHA-256 for {filename}...")
    manifest = create_manifest(creator_id, filename, file_path)
    sha256 = manifest["sha256"]
    
    # Check if already in database
    try:
        conn = get_db_connection(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT id, created_at FROM manifests WHERE sha256 = %s", (sha256,))
        existing = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if existing:
            asset_id, created_at = existing
            print(f"  ⊘ Already in database (ID: {asset_id}, registered: {created_at})")
            return {
                "status": "duplicate",
                "message": f"Image already registered",
                "asset_id": str(asset_id),
                "sha256": sha256,
                "created_at": str(created_at)
            }
    except Exception as e:
        print(f"  ✗ Database error checking duplicates: {e}")
        return {"status": "error", "message": str(e)}

    
    # Create manifest (already created above for SHA-256 check)
    print(f"  Creating manifest for {filename}...")
    
    # Canonicalize manifest (sorted keys, compact format)
    canonical_json = json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    
    # Sign manifest
    print(f"  Signing manifest with Ed25519...")
    signed = signing_key.sign(canonical_json.encode())
    signature_hex = signed.signature.hex()
    
    # Connect to database
    print(f"  Connecting to database...")
    conn = get_db_connection(db_url)
    
    try:
        # Compute vectors for similarity search
        print("Computing hash vectors for similarity search...")
        phash_vector = hc.hash_to_vector(manifest["phash"][0])
        dhash_vector = hc.hash_to_vector(manifest["dhash"][0])
        ahash_vector = hc.hash_to_vector(manifest["ahash"][0])
        
        # Read image file as binary
        print("Reading image file to store in database...")
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        # Insert into manifests table
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO manifests (sha256, manifest_json, signature_hex, key_id, phash_vector, dhash_vector, ahash_vector, image_data)
            VALUES (%s, %s::jsonb, %s, %s, %s::vector, %s::vector, %s::vector, %s)
            RETURNING id, created_at
            """,
            (sha256, json.dumps(manifest), signature_hex, key_id, phash_vector, dhash_vector, ahash_vector, image_data)
        )
        
        result = cursor.fetchone()
        asset_id, created_at = result
        
        # Track which user registered this image
        cursor.execute(
            """
            INSERT INTO user_registrations (user_id, manifest_sha256)
            VALUES (%s, %s)
            """,
            (current_user["user_id"], sha256)
        )
        
        conn.commit()
        cursor.close()
        
        print(f"  ✓ Successfully registered: {filename} (ID: {asset_id})")
        
        return {
            "asset_id": str(asset_id),
            "sha256": sha256,
            "manifest": manifest,
            "signature": signature_hex,
            "created_at": str(created_at),
            "status": "registered"
        }
    
    except Exception as e:
        conn.rollback()
        print(f"✗ Registration failed: {e}")
        raise
    
    finally:
        conn.close()


<<<<<<< Updated upstream
<<<<<<< Updated upstream
def main():
    #match_test()
    register_media(
        file_path="/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images/antilope21.jpg",
        creator_id="campaign-team-1")
=======
=======
>>>>>>> Stashed changes
def find_closest_match(query_image_path: str = None, top_k: int = 10, db_url: str = None) -> list[dict]:
    """
    Find the closest matching image(s) in database using pgvector similarity search.
    Uses HNSW indexes for sub-linear O(log n) retrieval.
    
    Args:
        query_image_path: Path to the query image (if None, prompts user for input)
        top_k: Number of closest matches to return (default: 10)
        db_url: PostgreSQL connection string (default: POSTGRES_URL from .env)
    
    Returns:
        List of dicts with: sha256, filename, creator_id, distance, confidence_tier
    """
    # Get image path from user if not provided
    if query_image_path is None:
        query_image_path = input("\nEnter path to image to check: ").strip()
    
    if not os.path.isfile(query_image_path):
        print(f"✗ File not found: {query_image_path}")
        return []
    
    print(f"\n[SIMILARITY SEARCH] Query image: {os.path.basename(query_image_path)}")
    print(f"  Looking for {top_k} closest matches...")
    
    try:
        # Compute query image hashes
        query_result = hc.compute_hashes_by_type(query_image_path)
        
        if query_result["media_type"] == "video":
            raise ValueError("Video similarity search not yet implemented")
        
        # Convert hashes to vectors
        query_phash_vector = hc.hash_to_vector(query_result["phash"][0])
        query_dhash_vector = hc.hash_to_vector(query_result["dhash"][0])
        query_ahash_vector = hc.hash_to_vector(query_result["ahash"][0])
        
        # Connect to database
        conn = get_db_connection(db_url)
        cursor = conn.cursor()
        
        # Query for top-k nearest neighbors using pHash (can also use dHash or aHash)
        # The HNSW index enables fast similarity search via cosine distance
        # Distance = 1 - cosine_similarity, so smaller distance = more similar
        cursor.execute(
            """
            SELECT 
                sha256,
                manifest_json->>'filename' as filename,
                manifest_json->>'creator_id' as creator_id,
                phash_vector <-> %s::vector as phash_distance,
                dhash_vector <-> %s::vector as dhash_distance,
                ahash_vector <-> %s::vector as ahash_distance,
                created_at
            FROM manifests
            ORDER BY phash_vector <-> %s::vector
            LIMIT %s
            """,
            (query_phash_vector, query_dhash_vector, query_ahash_vector, 
             query_phash_vector, top_k)
        )
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Process results
        matches = []
        for i, row in enumerate(results, 1):
            sha256, filename, creator_id, phash_dist, dhash_dist, ahash_dist, created_at = row
            
            # Handle None values (NULL vectors in database)
            if phash_dist is None or dhash_dist is None or ahash_dist is None:
                print(f"\n  ⚠ Warning: Image {filename} has incomplete vector data in database")
                print(f"     This image may need to be re-registered with vector computation")
                continue
            
            # Calculate confidence tier based on vector distances
            # Smaller distance = more similar
            avg_distance = (phash_dist + dhash_dist + ahash_dist) / 3.0
            
            if avg_distance < 0.1:
                tier = "tier1"  # Very high similarity
            elif avg_distance < 0.2:
                tier = "tier2"  # High similarity
            elif avg_distance < 0.3:
                tier = "tier3"  # Moderate similarity
            else:
                tier = "tier4"  # Low similarity
            
            match_info = {
                "rank": i,
                "sha256": sha256,
                "filename": filename,
                "creator_id": creator_id,
                "phash_distance": round(phash_dist, 4),
                "dhash_distance": round(dhash_dist, 4),
                "ahash_distance": round(ahash_dist, 4),
                "avg_distance": round(avg_distance, 4),
                "confidence_tier": tier,
                "created_at": str(created_at)
            }
            matches.append(match_info)
            
            print(f"\n  #{i} MATCH ({tier})")
            print(f"     Filename: {filename}")
            print(f"     Creator: {creator_id}")
            print(f"     Similarity: {round((1 - avg_distance) * 100, 1)}%")
            print(f"     SHA-256: {sha256[:16]}...")
        
        return matches
        
    except Exception as e:
        print(f"✗ Search failed: {e}")
        raise


def find_closest_match_bruteforce(query_image_path: str = None, db_url: str = None) -> list[dict]:
    """
    Find the closest matching image(s) using brute-force Hamming distance comparison.
    Bypasses pgvector entirely and compares against every image in database.
    
    Time Complexity: O(n) where n = number of images in database
    Useful for: Verification, debugging, or when vector indexes aren't reliable
    
    Args:
        query_image_path: Path to the query image (if None, prompts user for input)
        db_url: PostgreSQL connection string (default: POSTGRES_URL from .env)
    
    Returns:
        List of dicts sorted by overall similarity (best match first)
    """
    # Get image path from user if not provided
    if query_image_path is None:
        query_image_path = input("\nEnter path to image to check: ").strip()
    
    if not os.path.isfile(query_image_path):
        print(f"✗ File not found: {query_image_path}")
        return []
    
    print(f"\n[BRUTEFORCE SEARCH] Query image: {os.path.basename(query_image_path)}")
    print(f"  Comparing against ALL images in database (O(n) scan)...")
    
    try:
        # Compute query image hashes
        query_result = hc.compute_hashes_by_type(query_image_path)
        
        if query_result["media_type"] == "video":
            raise ValueError("Video comparison not yet implemented")
        
        # Extract query hashes as hex strings
        query_phash = query_result["phash"][0]
        query_dhash = query_result["dhash"][0]
        query_ahash = query_result["ahash"][0]
        
        # Connect to database
        conn = get_db_connection(db_url)
        cursor = conn.cursor()
        
        # Get ALL manifests from database (full scan)
        print(f"  Scanning database...")
        cursor.execute("""
            SELECT id, sha256, manifest_json, created_at, image_data
            FROM manifests
            ORDER BY created_at DESC
        """)
        
        db_records = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not db_records:
            print(f"  ✗ No images found in database")
            return []
        
        print(f"  Found {len(db_records)} records in database")
        print(f"  Computing Hamming distances...\n")
        
        # Compute distances for all records
        matches = []
        
        for record_id, sha256, manifest_json, created_at, image_data in db_records:
            try:
                manifest = json.loads(manifest_json) if isinstance(manifest_json, str) else manifest_json
                
                # Extract stored hashes
                db_phash = manifest.get("phash", [None])[0]
                db_dhash = manifest.get("dhash", [None])[0]
                db_ahash = manifest.get("ahash", [None])[0]
                
                # Skip if hashes missing
                if not all([db_phash, db_dhash, db_ahash]):
                    continue
                
                # Compute Hamming distances
                phash_distance = hc.hamming_distance(query_phash, db_phash)
                dhash_distance = hc.hamming_distance(query_dhash, db_dhash)
                ahash_distance = hc.hamming_distance(query_ahash, db_ahash)
                
                # Calculate average distance (lower is better)
                avg_distance = (phash_distance + dhash_distance + ahash_distance) / 3.0
                
                # Calculate similarity score (0-100%)
                # Based on Hamming: 64-bit hash, max distance = 64
                # Similarity = (1 - distance/64) * 100
                similarity_score = max(0, (1 - (avg_distance / 64.0)) * 100)
                
                # Assign confidence tier
                if avg_distance <= 5:
                    tier = "tier1"  # Excellent match
                elif avg_distance <= 10:
                    tier = "tier2"  # Good match
                elif avg_distance <= 20:
                    tier = "tier3"  # Moderate match
                else:
                    tier = "tier4"  # Weak match
                
                # Encode image as base64 if available
                image_base64 = None
                if image_data:
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                match_info = {
                    "sha256": sha256,
                    "filename": manifest.get("filename", "unknown"),
                    "creator_id": manifest.get("creator_id", "unknown"),
                    "phash_distance": phash_distance,
                    "dhash_distance": dhash_distance,
                    "ahash_distance": ahash_distance,
                    "avg_distance": round(avg_distance, 2),
                    "similarity_score": round(similarity_score, 1),
                    "confidence_tier": tier,
                    "created_at": str(created_at),
                    "image_base64": image_base64
                }
                matches.append(match_info)
                
            except Exception as e:
                # Skip records with errors
                continue
        
        # Sort by avg_distance (closest first)
        matches.sort(key=lambda x: x["avg_distance"])
        
        # Display results
        if not matches:
            print(f"✗ No valid comparisons could be made")
            return []
        
        print(f"{'='*120}")
        print(f"{'RANK':<6} {'FILENAME':<30} {'pHash':<8} {'dHash':<8} {'aHash':<8} {'Avg Dist':<12} {'Similarity':<12} {'Tier':<10}")
        print(f"{'='*120}")
        
        for i, match in enumerate(matches[:20], 1):  # Show top 20
            print(f"{i:<6} {match['filename']:<30} {match['phash_distance']:<8} {match['dhash_distance']:<8} {match['ahash_distance']:<8} {match['avg_distance']:<12.2f} {match['similarity_score']:<11.1f}% {match['confidence_tier']:<10}")
            
            if i == 1:  # Print details for top match
                print(f"\n  🏆 TOP MATCH: {match['filename']}")
                print(f"     Creator: {match['creator_id']}")
                print(f"     SHA-256: {match['sha256']}")
                print(f"     Similarity: {match['similarity_score']:.1f}%")
                print(f"     Confidence: {match['confidence_tier'].upper()}")
                print(f"     Registered: {match['created_at']}\n")
        
        print(f"{'='*120}\n")
        
        return matches
        
    except Exception as e:
        print(f"✗ Search failed: {e}")
        raise


def match_test():
    """
    Test algorithm accuracy by comparing all test images against the original.
    Computes hashes using compute_hashes_by_type() and calculates confidence tiers.
    """
    print("=" * 100)
    print("MEDIA VERIFICATION TEST")
    print("=" * 100)
    
    test_images_dir = "/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images"
    original_file = "aaog.jpeg"
    original_path = os.path.join(test_images_dir, original_file)
    
    # Compute original hashes using new interface
    print(f"\n[ORIGINAL] Loading: {original_file}")
    try:
        og_result = hc.compute_hashes_by_type(original_path)
        if og_result["media_type"] == "video":
            print("  ✗ Video processing not yet implemented")
            return
        
        og_sha256 = og_result["sha256"]
        og_ph = og_result["phash"][0]  # Extract from array
        og_dh = og_result["dhash"][0]
        og_ah = og_result["ahash"][0]
        
        print(f"  SHA-256: {og_sha256}")
        print(f"  pHash:   {og_ph}")
        print(f"  dHash:   {og_dh}")
        print(f"  aHash:   {og_ah}\n")
    except Exception as e:
        print(f"  ✗ Error loading original: {e}")
        return
    
    # Test all other images
    print("-" * 100)
    print(f"{'File':<30} {'SHA256':<10} {'pHash':<8} {'dHash':<8} {'aHash':<8} {'Tier':<10}")
    print("-" * 100)
    
    tier_counts = {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0, "no_match": 0}
    test_count = 0
    
    for img in sorted(os.listdir(test_images_dir)):
        
        test_path = os.path.join(test_images_dir, img)
        
        # Skip non-image files
        if not os.path.isfile(test_path):
            continue
        
        try:
            test_count += 1
            
            # Compute test image hashes
            test_result = hc.compute_hashes_by_type(test_path)
            
            # Skip videos for now
            if test_result["media_type"] == "video":
                print(f"{img:<30} {'SKIP':<10} {'-':<8} {'-':<8} {'-':<8} {'VIDEO':<10}")
                continue
            
            test_sha256 = test_result["sha256"]
            test_ph = test_result["phash"][0]  # Extract from array
            test_dh = test_result["dhash"][0]
            test_ah = test_result["ahash"][0]
            
            # Calculate Hamming distances using hash_compute utility
            ph_distance = hc.hamming_distance(og_ph, test_ph)
            dh_distance = hc.hamming_distance(og_dh, test_dh)
            ah_distance = hc.hamming_distance(og_ah, test_ah)
            
            # Determine match signals
            exact_match = og_sha256 == test_sha256
            phash_match = ph_distance <= 8
            dhash_match = dh_distance <= 8
            ahash_match = ah_distance <= 8
            
            # Count matching signals (0-3)
            matching_signals = sum([phash_match, dhash_match, ahash_match])
            
            # Assign confidence tier based on signal agreement and distances
            if exact_match:
                confidence_tier = "tier1"  # Tier 1: Exact SHA-256 match
            elif matching_signals >= 2:  # 2+ signals within tolerance
                confidence_tier = "tier2"  # Tier 2: High confidence fuzzy match
            elif matching_signals == 1:
                max_distance = max(ph_distance, dh_distance, ah_distance)
                if max_distance <= 12:
                    confidence_tier = "tier3"  # Tier 3: Moderate confidence
                else:
                    confidence_tier = "tier4"  # Tier 4: Low confidence
            else:
                confidence_tier = "no_match"  # No match
            
            tier_counts[confidence_tier] += 1
            
            # Format output
            sha256_short = "✓" if exact_match else "✗"
            print(f"{img:<30} {sha256_short:<10} {ph_distance:<8} {dh_distance:<8} {ah_distance:<8} {confidence_tier:<10}")
            
        except Exception as e:
            print(f"{img:<30} {'ERROR':<10} {str(e)[:6]:<8} {'-':<8} {'-':<8} {'-':<10}")
    
    # Summary statistics
    print("-" * 100)
    print(f"\nTEST SUMMARY (Total: {test_count} images)")
    print(f"  Tier 1 (Exact Match):      {tier_counts['tier1']:>3}")
    print(f"  Tier 2 (High Confidence):  {tier_counts['tier2']:>3}")
    print(f"  Tier 3 (Moderate):         {tier_counts['tier3']:>3}")
    print(f"  Tier 4 (Low Confidence):   {tier_counts['tier4']:>3}")
    print(f"  No Match:                  {tier_counts['no_match']:>3}")
    print("=" * 100)


def regenerate_null_vectors(db_url: str = None) -> dict:
    """
    Regenerate vectors for records in database that have NULL vector columns.
    This is needed when existing records were stored before vector generation was implemented.
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    
    Args:
        db_url: PostgreSQL connection string (default: POSTGRES_URL from .env)
    
    Returns:
        dict with statistics on regenerated vectors
    """
    print(f"\n{'='*100}")
    print("REGENERATING NULL VECTORS IN DATABASE")
    print(f"{'='*100}\n")
    
    try:
        conn = get_db_connection(db_url)
        cursor = conn.cursor()
        
        # Find records with NULL vectors
        cursor.execute("""
            SELECT id, sha256, manifest_json
            FROM manifests
            WHERE phash_vector IS NULL OR dhash_vector IS NULL OR ahash_vector IS NULL
        """)
        
        records_to_update = cursor.fetchall()
        
        if not records_to_update:
            print("✓ No records with NULL vectors found")
            cursor.close()
            conn.close()
            return {"status": "success", "updated": 0}
        
        print(f"Found {len(records_to_update)} records with NULL vectors, regenerating...\n")
        
        updated_count = 0
        
        for record_id, sha256, manifest_json in records_to_update:
            try:
                manifest = json.loads(manifest_json) if isinstance(manifest_json, str) else manifest_json
                
                # Extract hashes from manifest
                phash = manifest["phash"][0] if manifest.get("phash") else None
                dhash = manifest["dhash"][0] if manifest.get("dhash") else None
                ahash = manifest["ahash"][0] if manifest.get("ahash") else None
                
                if not all([phash, dhash, ahash]):
                    print(f"  ✗ Record {record_id}: Missing hash data in manifest")
                    continue
                
                # Convert to vectors
                phash_vector = hc.hash_to_vector(phash)
                dhash_vector = hc.hash_to_vector(dhash)
                ahash_vector = hc.hash_to_vector(ahash)
                
                # Update record
                cursor.execute("""
                    UPDATE manifests
                    SET phash_vector = %s::vector,
                        dhash_vector = %s::vector,
                        ahash_vector = %s::vector
                    WHERE id = %s
                """, (phash_vector, dhash_vector, ahash_vector, record_id))
                
                updated_count += 1
                print(f"  ✓ Updated record {record_id} ({sha256[:16]}...)")
                
            except Exception as e:
                print(f"  ✗ Record {record_id}: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n{'='*100}")
        print(f"REGENERATION COMPLETE")
        print(f"  Total updated: {updated_count}/{len(records_to_update)}")
        print(f"{'='*100}\n")
        
        return {"status": "success", "updated": updated_count, "total": len(records_to_update)}
        
    except Exception as e:
        print(f"✗ Error regenerating vectors: {e}")
        return {"status": "error", "message": str(e)}
<<<<<<< Updated upstream
=======


def register_all_from_directory(directory: str) -> dict:
    """
    Register all images from a directory.
    Skips files that are already in the database (checks by SHA-256).
    Uses current authenticated user as creator.
    
    Args:
        directory: Path to directory containing images to register
    
    Returns:
        dict with registration statistics
    """
    if not current_user:
        print("✗ You must be logged in to register media")
        return {"status": "error", "message": "Not authenticated"}
    
    if not os.path.isdir(directory):
        print(f"✗ Directory not found: {directory}")
        return {"status": "error", "message": "Directory not found"}
    
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff'))]
    
    if not image_files:
        print(f"✗ No image files found in {directory}")
        return {"status": "error", "message": "No image files found"}
    
    print(f"\n{'='*100}")
    print(f"BULK REGISTRATION - {len(image_files)} images found")
    print(f"Directory: {directory}")
    print(f"User: {current_user['username']}")
    print(f"User ID: {current_user['user_id']}")
    print(f"{'='*100}\n")
    
    stats = {
        "total": len(image_files),
        "registered": 0,
        "duplicates": 0,
        "errors": 0,
        "results": []
    }
    
    for idx, filename in enumerate(image_files, 1):
        file_path = os.path.join(directory, filename)
        print(f"[{idx}/{len(image_files)}] {filename}...")
        
        result = register_media(file_path)
        
        if result["status"] == "registered":
            stats["registered"] += 1
            print(f"        ✓ Registered")
        elif result["status"] == "duplicate":
            stats["duplicates"] += 1
            print(f"        ☐ Already in database")
        else:
            stats["errors"] += 1
            print(f"        ✗ Error: {result.get('message', 'Unknown error')}")
        
        stats["results"].append(result)
    
    # Summary
    print(f"\n{'='*100}")
    print(f"REGISTRATION SUMMARY")
    print(f"  Total processed:   {stats['total']}")
    print(f"  New registrations: {stats['registered']}")
    print(f"  Already in DB:     {stats['duplicates']}")
    print(f"  Errors:            {stats['errors']}")
    print(f"{'='*100}\n")
    return stats


def main():
    # Show auth menu first
    if not auth_menu():
        return
    
    # Main menu loop
    while True:
        print("\n" + "="*100)
        print(f"MEDIA PROVENANCE SYSTEM - MAIN MENU (User: {current_user['username']})")
        print("="*100)
        print("1. Register all images from directory")
        print("2. Check image (pgvector similarity search - O(log n))")
        print("3. Check image (bruteforce Hamming distance - O(n))")
        print("4. Run match_test()")
        print("5. Regenerate NULL vectors in database")
        print("6. Logout")
        print("7. Exit")
        
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == "1":
            directory = input("Enter directory path (default: /home/.../to_register): ").strip()
            if not directory:
                directory = "/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/to_register"
            register_all_from_directory(directory)
        elif choice == "2":
            find_closest_match()
        elif choice == "3":
            find_closest_match_bruteforce()
        elif choice == "4":
            match_test()
        elif choice == "5":
            regenerate_null_vectors()
        elif choice == "6":
            logout()
            if auth_menu():
                continue
            else:
                break
        elif choice == "7":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter 1-7.")

>>>>>>> Stashed changes


def register_all_from_directory(directory: str) -> dict:
    """
    Register all images from a directory.
    Skips files that are already in the database (checks by SHA-256).
    Uses current authenticated user as creator.
    
    Args:
        directory: Path to directory containing images to register
    
    Returns:
        dict with registration statistics
    """
    if not current_user:
        print("✗ You must be logged in to register media")
        return {"status": "error", "message": "Not authenticated"}
    
    if not os.path.isdir(directory):
        print(f"✗ Directory not found: {directory}")
        return {"status": "error", "message": "Directory not found"}
    
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff'))]
    
    if not image_files:
        print(f"✗ No image files found in {directory}")
        return {"status": "error", "message": "No image files found"}
    
    print(f"\n{'='*100}")
    print(f"BULK REGISTRATION - {len(image_files)} images found")
    print(f"Directory: {directory}")
    print(f"User: {current_user['username']}")
    print(f"User ID: {current_user['user_id']}")
    print(f"{'='*100}\n")
    
    stats = {
        "total": len(image_files),
        "registered": 0,
        "duplicates": 0,
        "errors": 0,
        "results": []
    }
    
    for idx, filename in enumerate(image_files, 1):
        file_path = os.path.join(directory, filename)
        print(f"[{idx}/{len(image_files)}] {filename}...")
        
        result = register_media(file_path)
        
        if result["status"] == "registered":
            stats["registered"] += 1
            print(f"        ✓ Registered")
        elif result["status"] == "duplicate":
            stats["duplicates"] += 1
            print(f"        ☐ Already in database")
        else:
            stats["errors"] += 1
            print(f"        ✗ Error: {result.get('message', 'Unknown error')}")
        
        stats["results"].append(result)
    
    # Summary
    print(f"\n{'='*100}")
    print(f"REGISTRATION SUMMARY")
    print(f"  Total processed:   {stats['total']}")
    print(f"  New registrations: {stats['registered']}")
    print(f"  Already in DB:     {stats['duplicates']}")
    print(f"  Errors:            {stats['errors']}")
    print(f"{'='*100}\n")
    return stats


def main():
    # Show auth menu first
    if not auth_menu():
        return
    
    # Main menu loop
    while True:
        print("\n" + "="*100)
        print(f"MEDIA PROVENANCE SYSTEM - MAIN MENU (User: {current_user['username']})")
        print("="*100)
        print("1. Register all images from directory")
        print("2. Check image (pgvector similarity search - O(log n))")
        print("3. Check image (bruteforce Hamming distance - O(n))")
        print("4. Run match_test()")
        print("5. Regenerate NULL vectors in database")
        print("6. Logout")
        print("7. Exit")
        
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == "1":
            directory = input("Enter directory path (default: /home/.../to_register): ").strip()
            if not directory:
                directory = "/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/to_register"
            register_all_from_directory(directory)
        elif choice == "2":
            find_closest_match()
        elif choice == "3":
            find_closest_match_bruteforce()
        elif choice == "4":
            match_test()
        elif choice == "5":
            regenerate_null_vectors()
        elif choice == "6":
            logout()
            if auth_menu():
                continue
            else:
                break
        elif choice == "7":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please enter 1-7.")


<<<<<<< Updated upstream
if __name__ == "__main__":	main()
=======
if __name__ == "__main__":	main()



"""“I’m building a cryptographic media provenance system 
that uses hashing and digital signatures to verify the 
<<<<<<< Updated upstream
authenticity of digital media.” """
>>>>>>> Stashed changes
=======
authenticity of digital media.” """
>>>>>>> Stashed changes
