
import os
from dotenv import load_dotenv
import psycopg
import json
from datetime import datetime, timezone
from nacl.signing import SigningKey

import hash_compute as hc

# Load environment variables from .env file
load_dotenv()

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
    creator_id: str,
    signing_key_hex: str = None,
    key_id: str = "key-2026-01",
    db_url: str = None
) -> dict:
    """
    Register a file in the database with Ed25519 signature.
    
    Args:
        file_path: Path to media file to register
        creator_id: Organization/team ID (e.g., "campaign-team-1")
        signing_key_hex: Ed25519 private key as hex string
                        If None, reads from VERIFIER_PRIVATE_KEY_HEX environment variable
        key_id: Public key identifier (e.g., "key-2026-01")
        db_url: PostgreSQL connection string
               If None, reads from POSTGRES_URL environment variable
    
    Returns:
        dict with registration details
    """
    # Get signing key
    if signing_key_hex is None:
        signing_key_hex = os.getenv("VERIFIER_PRIVATE_KEY_HEX")
    
    if signing_key_hex is None:
        raise ValueError("VERIFIER_PRIVATE_KEY_HEX not set and no signing_key_hex provided")
    
    signing_key = SigningKey(bytes.fromhex(signing_key_hex))
    
    # Get filename
    filename = os.path.basename(file_path)
    
    # Create manifest (includes all hashing)
    print(f"Creating manifest for {filename}...")
    manifest = create_manifest(creator_id, filename, file_path)
    
    # Extract SHA256 from manifest
    sha256 = manifest["sha256"]
    
    # Canonicalize manifest (sorted keys, compact format)
    canonical_json = json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    
    # Sign manifest
    print("Signing manifest with Ed25519...")
    signed = signing_key.sign(canonical_json.encode())
    signature_hex = signed.signature.hex()
    
    # Connect to database
    print("Connecting to database...")
    conn = get_db_connection(db_url)
    
    try:
        # Insert into manifests table
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO manifests (sha256, manifest_json, signature_hex, key_id)
            VALUES (%s, %s::jsonb, %s, %s)
            RETURNING id, created_at
            """,
            (sha256, json.dumps(manifest), signature_hex, key_id)
        )
        
        result = cursor.fetchone()
        asset_id, created_at = result
        
        conn.commit()
        cursor.close()
        
        print(f"✓ Successfully registered: {filename} (ID: {asset_id})")
        
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


def main():
    #match_test()
    register_media(
        file_path="/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images/antilope21.jpg",
        creator_id="campaign-team-1")
    

if __name__ == "__main__":	main()