from PIL import Image, ImageOps
import imagehash
import cv2
import os

import hashlib
import generate_keys as gk

import cv2
import io
import numpy as np

def compute_hashes_by_type(file_path: str) -> dict:
    """
    Compute hashes based on file type.
    For images: return phash, dhash
    For videos: return list of keyframe phashes
    
    Args:
        file_path: path to image or video file
    
    Returns:
        dict with keys:
        - media_type: "image" or "video"
        - phash: str (for images) or None
        - dhash: str (for images) or None
        - phash_keyframes: list[str] (for videos) or None
    """
    
    # Get file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # Image types
    image_ext = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
    video_ext = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".flv"}
    
    if ext in image_ext:
        return _compute_image_hashes(file_path)
    elif ext in video_ext:
        return _compute_video_hashes(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _compute_image_hashes(file_path: str) -> dict:
    """
    Compute hashes for image: SHA-256, pHash, dHash.
    Includes border removal and normalization.
    
    Returns:
        dict with:
        - media_type: "image"
        - sha256: file hash (hex string)
        - phash: perceptual hash as array
        - dhash: difference hash as array
    """
    try:
        # Compute SHA-256
        sha256 = compute_sha256(file_path)
        
        # Compute perceptual hashes with normalization
        ph, dh, ah = compute_pdahash_norm(file_path)
        
        return {
            "media_type": "image",
            "sha256": sha256,
            "phash": [ph],  # Store as array for consistency with video
            "dhash": [dh],
            "ahash": [ah]
        }
    except Exception as e:
        raise ValueError(f"Could not process image: {e}")


def _compute_video_hashes(file_path: str) -> dict:
    """
    Compute hashes for video (not yet implemented).
    Currently just passes and returns media type.
    
    Returns:
        dict with:
        - media_type: "video"
        - phash: None
        - dhash: None
    """
    print(f"⊘ Video processing not yet implemented: {file_path}")
    return {
        "media_type": "video",
        "phash": None,
        "dhash": None,
        "ahash": None
    }
    

def compute_sha256(path):
	h = hashlib.sha256()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(8192), b""):
			h.update(chunk)
	sha256 = h.hexdigest()
	print("SHA-256 hash of the file:", sha256)
	return sha256

def hamming_distance(hash_hex_a: str, hash_hex_b: str) -> int:
	a = imagehash.hex_to_hash(hash_hex_a)
	b = imagehash.hex_to_hash(hash_hex_b)
	return int(a - b)

def hash_to_vector(hash_hex: str) -> list[float]:
	"""
	Convert a hex hash string to a 64-dimensional vector for pgvector.
	
	Each hex character (4 bits) is converted to a float value.
	Example: "e79249c66c631ecc..." → [0.9375, 0.5625, 1.0, 0.375, ...]
	
	Args:
		hash_hex: Hex string representation of hash
	
	Returns:
		list of 64 float values (0.0 to 1.0)
	"""
	# Remove any non-hex characters
	hash_hex = ''.join(c for c in hash_hex if c in '0123456789abcdef')
	
	# Convert each hex char to float (0-15 normalized to 0.0-1.0)
	vector = []
	for char in hash_hex:
		value = int(char, 16) / 15.0  # Normalize 0-15 to 0.0-1.0
		vector.append(value)
	
	# Ensure we have exactly 64 dimensions
	if len(vector) < 64:
		# Pad with zeros if necessary
		vector.extend([0.0] * (64 - len(vector)))
	elif len(vector) > 64:
		# Truncate if necessary
		vector = vector[:64]
	
	return vector
     
def compute_pdahash_norm(path: str, target_size: int = 256, hash_size: int = 8) -> tuple[str, str, str]:
    """
    Compute pHash, dHash, and aHash with improved aspect ratio normalization.
    Handles stretching, letterboxing, and lighting variations.
    Uses padding (not cropping) to preserve all original content.
    """
    with Image.open(path) as img:
        # Step 1: Handle EXIF and convert to RGB
        img = ImageOps.exif_transpose(img).convert("RGB")
        
        # Step 2: Remove uniform color borders (letterboxing, padding)
        img = remove_borders(img, edge_threshold=40)
        
        img_array = np.array(img)
        
        # Step 3: Normalize aspect ratio by padding to square
        # This preserves all original content without discarding pixels
        height, width = img_array.shape[:2]
        max_dim = max(width, height)
        
        # Calculate padding needed (distribute evenly on both sides)
        left_pad = (max_dim - width) // 2
        right_pad = max_dim - width - left_pad
        top_pad = (max_dim - height) // 2
        bottom_pad = max_dim - height - top_pad
        
        # Pad with neutral gray (128, 128, 128) to minimize hash artifacts
        padded = ImageOps.expand(img, (left_pad, top_pad, right_pad, bottom_pad), fill=(128, 128, 128))
        
        # Step 4: Resize to standard size (256x256)
        resized = padded.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Step 5: Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # This normalizes lighting variations from compression/quality loss
        resized_array = np.array(resized)
        resized_bgr = cv2.cvtColor(resized_array, cv2.COLOR_RGB2BGR)
        lab = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2LAB)
        
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)
        
        enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        enhanced_rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)
        normalized_img = Image.fromarray(enhanced_rgb)
        
        # Step 6: Compute hashes on normalized image
        ph = imagehash.phash(normalized_img, hash_size=hash_size)
        dh = imagehash.dhash(normalized_img, hash_size=hash_size)
        ah = imagehash.average_hash(normalized_img, hash_size=hash_size)
        
        return str(ph), str(dh), str(ah)


def remove_borders(img: Image.Image, edge_threshold: int = 80, safety_margin: int = 5) -> Image.Image:
    """
    Detect and remove uniform color borders (padding) from image.
    Scans from edges to find where actual content begins.
    Includes safety margin to avoid over-cropping content.
    """
    img_array = np.array(img)
    height, width = img_array.shape[:2]
    
    def is_uniform_edge(arr, threshold):
        """Check if a row/column is uniform (border)."""
        return np.std(arr) < threshold
    
    # Find content boundaries by scanning from edges
    top, bottom, left, right = 0, height, 0, width
    
    # Scan from top
    for i in range(height):
        row = img_array[i, :]
        if not is_uniform_edge(row, edge_threshold):
            top = max(0, i - safety_margin)  # Pull back by safety_margin
            break
    
    # Scan from bottom
    for i in range(height - 1, -1, -1):
        row = img_array[i, :]
        if not is_uniform_edge(row, edge_threshold):
            bottom = min(height, i + 1 + safety_margin)  # Pull back by safety_margin
            break
    
    # Scan from left
    for j in range(width):
        col = img_array[:, j, :]
        if not is_uniform_edge(col.flatten(), edge_threshold):
            left = max(0, j - safety_margin)  # Pull back by safety_margin
            break
    
    # Scan from right
    for j in range(width - 1, -1, -1):
        col = img_array[:, j, :]
        if not is_uniform_edge(col.flatten(), edge_threshold):
            right = min(width, j + 1 + safety_margin)  # Pull back by safety_margin
            break
    
    # Ensure we have valid bounds
    if top >= bottom or left >= right:
        return img  # No borders detected, return original
    
    return img.crop((left, top, right, bottom))


def extract_keyframes(video_path: str, fps: int = 1) -> list[Image.Image]:
    """Extract keyframes from video."""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    
    if video_fps == 0:
        raise ValueError("Could not determine video FPS")
    
    frame_interval = int(video_fps / fps)
    keyframes = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            keyframes.append(pil_image)
        
        frame_count += 1
    
    cap.release()
    return keyframes


# Example usage:
if __name__ == "__main__":
    # Test with actual image from test_images
    test_image = "/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images/antilope21.jpg"
    
    if os.path.exists(test_image):
        result = compute_hashes_by_type(test_image)
        print("Image result:")
        print(result)
    else:
        print(f"Test image not found: {test_image}")