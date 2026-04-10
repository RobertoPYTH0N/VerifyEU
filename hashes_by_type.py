from PIL import Image, ImageOps
import imagehash
import cv2
import os

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
    """Compute pHash and dHash for image."""
    try:
        with Image.open(file_path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            ph = imagehash.phash(img, hash_size=8)
            dh = imagehash.dhash(img, hash_size=8)
            
            return {
                "media_type": "image",
                "phash": [str(ph)],
                "dhash": [str(dh)],
            }
    except Exception as e:
        raise ValueError(f"Could not process image: {e}")


def _compute_video_hashes(file_path: str) -> dict:
    """Extract keyframes and compute pHash for each."""
    try:
        phashes, dhashes = extract_keyframes_with_phash(file_path, fps=1)
        
        return {
            "media_type": "video",
            "phash": phashes,  
            "dhash": dhashes
        }
    except Exception as e:
        raise ValueError(f"Could not process video: {e}")


def extract_keyframes_with_phash(video_path: str, fps: int = 1) -> list[str]:
    """Extract keyframes and return their pHashes."""
    frames = extract_keyframes(video_path, fps=fps)
    phashes = []
    dhashes = []
    for frame in frames:
        ph = imagehash.phash(frame, hash_size=8)
        dh = imagehash.dhash(frame, hash_size=8)
        phashes.append(str(ph))
        dhashes.append(str(dh))
    return phashes, dhashes


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
    # Image
    result = compute_hashes_by_type("/path/to/image.jpg")
    print(result)
    # Output: {'media_type': 'image', 'phash': '...', 'dhash': '...', 'phash_keyframes': None}
    
    # Video
    result = compute_hashes_by_type("/path/to/video.mp4")
    print(result)
    # Output: {'media_type': 'video', 'phash': None, 'dhash': None, 'phash_keyframes': ['...', '...', ...]}