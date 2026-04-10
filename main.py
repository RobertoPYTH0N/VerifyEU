import hashlib
from PIL import Image, ImageOps
import imagehash
import generate_keys as gk
import os
import psycopg as ps
import json
from datetime import datetime, timezone
from uuid import uuid4
import cv2
import io

import hashes_by_type as hbt

def compute_sha256(path):
	h = hashlib.sha256()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(8192), b""):
			h.update(chunk)
	sha256 = h.hexdigest()
	print("SHA-256 hash of the file:", sha256)
	return sha256

def match_test():
    # Example usage of the functions
    print("Testing hash computation and matching...")
    file_path = "/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images/antilope21.jpg"
    
    # Compute original SHA-256 and pHash/dHash
    print(f"\nOriginal file: antilope21.jpg")
    og_sha256 = compute_sha256(file_path)
    og_ph, og_dh = compute_ph_dh(file_path)
    print(f"Original pHash: {og_ph}")
    print(f"Original dHash: {og_dh}\n")
    
    # Test images
    print("Testing other images:")
    print("-" * 80)
    
    for img in os.listdir("/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images"):
        if img == "antilope21.jpg":
            continue
        
        test_path = os.path.join("/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images", img)
        
        try:
            test_sha256 = compute_sha256(test_path)
            test_ph, test_dh = compute_ph_dh(test_path)
            
            # Calculate Hamming distances
            ph_distance = hamming_distance(og_ph, test_ph)
            dh_distance = hamming_distance(og_dh, test_dh)
            
            # Determine match confidence
            exact_match = og_sha256 == test_sha256
            phash_match = ph_distance <= 8
            dhash_match = dh_distance <= 8
            both_match = phash_match and dhash_match
            
            print(f"\nFile: {img}")
            print(f"  SHA-256 exact match: {exact_match}")
            print(f"  pHash distance: {ph_distance} {'✓ (strong match)' if phash_match else '✗'}")
            print(f"  dHash distance: {dh_distance} {'✓ (strong match)' if dhash_match else '✗'}")
            print(f"  Both hashes match: {both_match}")
            
        except Exception as e:
            print(f"\nFile: {img}")
            print(f"  Error: {e}")

def main():
    match_test()

def compute_ph_dh(path: str, hash_size: int = 8) -> tuple[str, str]:
	with Image.open(path) as img:
		img = ImageOps.exif_transpose(img).convert("RGB")
		ph = imagehash.phash(img, hash_size=hash_size)
		dh = imagehash.dhash(img, hash_size=hash_size)
		print("Perceptual Hash (pHash):", ph)
		print("Difference Hash (dHash):", dh)
		return str(ph), str(dh)

def hamming_distance(hash_hex_a: str, hash_hex_b: str) -> int:
	a = imagehash.hex_to_hash(hash_hex_a)
	b = imagehash.hex_to_hash(hash_hex_b)
	return int(a - b)

def create_manifest(creator_id: str, filename: str, sha256: str, file_path: str) -> dict:
    hash_result = hbt.compute_hashes_by_type(file_path)
    
    manifest = {
        "algorithm_hash": "SHA-256",
        "algorithm_signature": "Ed25519",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "creator_id": creator_id,
        "filename": filename,
        "id": str(uuid4()),
        "media_type": hash_result["media_type"],
        "sha256": sha256,
        "phash": hash_result["phash"],
        "dhash": hash_result["dhash"]
    }

    return manifest

def extract_keyframes(video_path: str, fps: int = 1) -> list[Image.Image]:
    """
    Extract keyframes from video at specified frames per second.
    
    Args:
        video_path: path to video file
        fps: frames per second to extract (1 = one frame per second)
    
    Returns:
        list of PIL Image objects
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    
    if video_fps == 0:
        raise ValueError("Could not determine video FPS")
    
    # Calculate frame interval (e.g., if video is 30 fps and we want 1 fps, skip 30 frames)
    frame_interval = int(video_fps / fps)
    
    keyframes = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Extract every nth frame
        if frame_count % frame_interval == 0:
            # Convert BGR (OpenCV) to RGB (PIL)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            keyframes.append(pil_image)
        
        frame_count += 1
    
    cap.release()
    return keyframes

if __name__ == "__main__":	main()

