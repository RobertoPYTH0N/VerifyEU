# Image Storage Setup Guide

## Overview

The system now stores actual image files in the database and displays them when matches are found. This provides a complete media management solution where everything is in one place.

## Setup Steps

### 1. Apply Database Migration

First, add the `image_data` column to the manifests table:

```bash
psql postgresql://postgres:postgres@localhost/crypto << 'EOF'
ALTER TABLE manifests 
ADD COLUMN IF NOT EXISTS image_data BYTEA DEFAULT NULL;

COMMENT ON COLUMN manifests.image_data IS 'Binary image data (stored as BYTEA)';
EOF
```

**Output**: Should see `ALTER TABLE` (no errors)

### 2. Verify Column was Added

```bash
psql postgresql://postgres:postgres@localhost/crypto -c "\d manifests"
```

Look for the `image_data` column in the output.

### 3. Restart the Backend

If the Flask API (api.py) is running, restart it:

```bash
# Kill the existing process
pkill -f "python.*api.py"

# Restart it
python api.py
```

### 4. Test the Feature

1. **Register a media file** via the frontend (Register Media button)
   - The image will now be stored in the database automatically
   - No changes needed on registration side

2. **Check Provenance** with the same or similar image
   - The matching images will now display in the results
   - Top match will show the largest image
   - All matches can be expanded to view their images

## Technical Details

### Database Changes
- **Column added**: `image_data BYTEA` in the `manifests` table
- **Size impact**: Images are stored as binary data; ~200KB per image on average
- **Performance**: Image retrieval is efficient as it's stored alongside metadata

### API Changes
- `POST /api/media/check` now includes `image_base64` in all match results
- Images are base64-encoded for JSON transport
- `image_base64` will be `null` if image wasn't stored (backward compatible)

### Frontend Changes
- **Top Match**: Displays image above the similarity score
- **All Matches**: Images display in expanded view when clicking a match
- **Graceful Degradation**: Shows placeholder if image fails to load

## Code Changes Summary

**main.py**:
- Added `import base64` 
- `register_media()`: Reads image file and stores as BYTEA
- `find_closest_match_bruteforce()`: Retrieves image_data and encodes to base64

**API**: No changes needed (main.py handles encoding)

**Frontend (ResultsDisplay.js)**:
- Top match displays image in container
- Expanded matches show images on click
- Fallback SVG placeholder if image unavailable

**Styling (ResultsDisplay.css)**:
- `.match-image-container` and `.match-image` for top match
- `.expanded-match-image` for match list images
- Responsive sizing (max 300px for top, 250px for expanded)

## Backward Compatibility

✓ **Old images without image_data**: Will show results but no images (image_base64 = null)
✓ **New API calls**: Include image_data automatically
✓ **Frontend**: Handles null images gracefully with CSS

## Storage Notes

For 212 images (current DB):
- Average image size: ~200-500 KB per file
- Total storage: ~50-100 MB in image_data column
- Database growth: Minimal index overhead (BYTEA not indexed)
- Backup size: All data in one PostgreSQL backup

## Future Optimizations

If needed later:
- **Compression**: GZIP image data in BYTEA
- **Thumbnails**: Create thumbnail column for faster list display
- **Lazy loading**: Load full images only when expanded
- **File storage**: Move images to S3/object storage and store URLs in DB
