def compute_ph_dh(path: str, hash_size: int = 8) -> tuple[str, str]:
	with Image.open(path) as img:
		img = ImageOps.exif_transpose(img).convert("RGB")
		ph = imagehash.phash(img, hash_size=hash_size)
		dh = imagehash.dhash(img, hash_size=hash_size)
		print("Perceptual Hash (pHash):", ph)
		print("Difference Hash (dHash):", dh)
		return str(ph), str(dh)
	
def compute_ph_dh_aspect_normalized_old(path: str, target_size: int = 256, hash_size: int = 8) -> tuple[str, str]:
    """
    Deprecated: Use compute_ph_dh_aspect_normalized() instead.
    This kept for reference if we need to compare old (crop) vs new (pad) approach.
    """
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        cropped = img.crop((left, top, right, bottom))
        resized = cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)
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
        ph = imagehash.phash(normalized_img, hash_size=hash_size)
        dh = imagehash.dhash(normalized_img, hash_size=hash_size)
        return str(ph), str(dh)

def normalize_image_to_disk(input_path: str, output_dir: str = "Output") -> str:
    """
    Apply full normalization pipeline (border removal, padding, CLAHE) and save to disk.
    
    Args:
        input_path: path to input image
        output_dir: directory to save normalized image (created if doesn't exist)
    
    Returns:
        path to the saved normalized image
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    with Image.open(input_path) as img:
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
        resized = padded.resize((256, 256), Image.Resampling.LANCZOS)
        
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
        
        # Step 6: Save the normalized image
        input_filename = os.path.basename(input_path)
        name, ext = os.path.splitext(input_filename)
        output_filename = f"{name}_normalized.png"
        output_path = os.path.join(output_dir, output_filename)
        
        normalized_img.save(output_path)
        print(f"Saved normalized image: {output_path}")
        
        return output_path
    

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


def histogram_similarity(img_path_1: str, img_path_2: str) -> float:
    """
    Compute color histogram similarity between two images.
    Very robust to scaling, compression, and aspect ratio changes.
    Returns score 0.0-1.0 (1.0 = identical histograms).
    """
    import numpy as np
    
    try:
        with Image.open(img_path_1) as img1:
            img1 = ImageOps.exif_transpose(img1).convert("RGB")
        with Image.open(img_path_2) as img2:
            img2 = ImageOps.exif_transpose(img2).convert("RGB")
        
        # Convert to BGR for OpenCV
        img1_array = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2BGR)
        img2_array = cv2.cvtColor(np.array(img2), cv2.COLOR_RGB2BGR)
        
        # Compute 3D color histograms (8x8x8 bins per channel)
        hist_1 = cv2.calcHist(
            [img1_array], [0, 1, 2], None,
            [8, 8, 8],
            [0, 256, 0, 256, 0, 256]
        )
        hist_2 = cv2.calcHist(
            [img2_array], [0, 1, 2], None,
            [8, 8, 8],
            [0, 256, 0, 256, 0, 256]
        )
        
        # Normalize histograms
        cv2.normalize(hist_1, hist_1, alpha=1, beta=0, norm_type=cv2.NORM_L2)
        cv2.normalize(hist_2, hist_2, alpha=1, beta=0, norm_type=cv2.NORM_L2)
        
        # Compare using Bhattacharyya distance (0=identical, 1=completely different)
        bhatta = cv2.compareHist(hist_1, hist_2, cv2.HISTCMP_BHATTACHARYYA)
        
        # Convert to similarity (1.0 = identical, 0.0 = completely different)
        similarity = 1.0 - min(1.0, bhatta)
        
        return similarity
    except Exception as e:
        print(f"Histogram similarity error: {e}")
        return 0.0


def structural_similarity(img_path_1: str, img_path_2: str) -> float:
    """
    Compute Structural Similarity Index (SSIM) between two images.
    Naturally crop-resistant: compares local structure, not pixel-by-pixel.
    Robust to compression, resizing, and partial crops.
    
    Returns score 0.0-1.0 (1.0 = identical structure).
    """
    try:
        from skimage.metrics import structural_similarity as skimage_ssim
        
        with Image.open(img_path_1) as img1:
            img1 = ImageOps.exif_transpose(img1).convert("RGB")
        with Image.open(img_path_2) as img2:
            img2 = ImageOps.exif_transpose(img2).convert("RGB")
        
        # Resize both to same size for fair comparison (256x256 standard)
        img1_resized = img1.resize((256, 256), Image.Resampling.LANCZOS)
        img2_resized = img2.resize((256, 256), Image.Resampling.LANCZOS)
        
        # Convert to grayscale for SSIM comparison
        img1_gray = cv2.cvtColor(np.array(img1_resized), cv2.COLOR_RGB2GRAY)
        img2_gray = cv2.cvtColor(np.array(img2_resized), cv2.COLOR_RGB2GRAY)
        
        # Compute SSIM (range: -1.0 to 1.0, normalized to 0.0 to 1.0)
        ssim_score = skimage_ssim(img1_gray, img2_gray, data_range=255)
        similarity = max(0.0, (ssim_score + 1.0) / 2.0)  # Normalize to 0.0-1.0
        
        return similarity
    except ImportError:
        # Fallback if scikit-image not available: use correlation-based method
        try:
            with Image.open(img_path_1) as img1:
                img1 = ImageOps.exif_transpose(img1).convert("RGB")
            with Image.open(img_path_2) as img2:
                img2 = ImageOps.exif_transpose(img2).convert("RGB")
            
            img1_resized = img1.resize((256, 256), Image.Resampling.LANCZOS)
            img2_resized = img2.resize((256, 256), Image.Resampling.LANCZOS)
            
            img1_array = np.array(img1_resized).flatten()
            img2_array = np.array(img2_resized).flatten()
            
            # Compute correlation coefficient
            correlation = np.corrcoef(img1_array, img2_array)[0, 1]
            similarity = max(0.0, (correlation + 1.0) / 2.0)  # Normalize to 0.0-1.0
            
            return similarity
        except Exception as e:
            print(f"SSIM fallback error: {e}")
            return 0.0
    except Exception as e:
        print(f"SSIM error: {e}")
        return 0.0







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



def match_test():
    # Example usage of the functions
    print("Testing hash computation with histogram similarity...")
    file_path = "/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images/antilope21.jpg"
    
    # Compute original hashes
    print(f"\nOriginal file: antilope21.jpg")
    og_sha256 = compute_sha256(file_path)
    og_ph, og_dh, og_ah = compute_pdahash_norm(file_path)
    print(f"Original pHash: {og_ph}")
    print(f"Original dHash: {og_dh}")
    print(f"Original aHash: {og_ah}\n")
    
    # Test images
    print("Testing other images:")
    print("-" * 140)
    
    # Track statistics
    high_confidence_count = 0
    test_count = 0
    
    for img in os.listdir("/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images"):
        if img == "antilope21.jpg":
            continue

        test_path = os.path.join("/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/test_images", img)
        
        try:
            test_count += 1
            test_sha256 = compute_sha256(test_path)
            test_ph, test_dh, test_ah = compute_pdahash_norm(test_path)
            
            # Calculate Hamming distances
            ph_distance = hamming_distance(og_ph, test_ph)
            dh_distance = hamming_distance(og_dh, test_dh)
            ah_distance = hamming_distance(og_ah, test_ah)

            # Determine match signals
            exact_match = og_sha256 == test_sha256
            total_distance = ph_distance + dh_distance + ah_distance
            phash_match = ph_distance <= 8
            dhash_match = dh_distance <= 8
            ahash_match = ah_distance <= 8
            
            if total_distance <= 8:  # Total Hamming distance threshold
                confidence = "tier1"
            elif total_distance <= 16:  # Moderate threshold for tier2
                confidence = "tier2"
            elif total_distance <= 24:  # Higher threshold for tier3
                confidence = "tier3"
            else:
                confidence = "no match"

            print(f"\nFile: {img}")
            print(f"  SHA-256 exact match: {exact_match}")
            print(f"  pHash distance: {ph_distance:2d} {'✓' if phash_match else '✗'}")
            print(f"  dHash distance: {dh_distance:2d} {'✓' if dhash_match else '✗'}")
            print(f"  aHash distance: {ah_distance:2d} {'✓' if ahash_match else '✗'}")
            print(f"  Confidence: {confidence}")
            
        except Exception as e:
            print(f"\nFile: {img}")
            print(f"  Error: {e}")

