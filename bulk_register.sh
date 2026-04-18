#!/bin/bash
# Bulk register images from to_register directory using Flask API

API_URL="http://localhost:5000"
TO_REGISTER_DIR="/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/to_register"

echo "========================================"
echo "BULK REGISTRATION VIA API"
echo "========================================"
echo ""

# Step 1: Register user
echo "Step 1: Creating/logging in user..."
curl -s -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"bulk_uploader","password":"BulkUpload123"}' > /dev/null

curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"bulk_uploader","password":"BulkUpload123"}' > /dev/null

echo "✓ User authenticated"
echo ""

# Step 2: Register all images
echo "Step 2: Registering all images from $TO_REGISTER_DIR..."
echo ""

registered=0
errors=0
duplicates=0

for image in "$TO_REGISTER_DIR"/*.{jpg,jpeg,png,gif,bmp,webp,tif,tiff}; do
    [ -e "$image" ] || continue
    
    filename=$(basename "$image")
    echo -n "  Registering $filename... "
    
    response=$(curl -s -X POST "$API_URL/api/media/register" \
      -F "file=@$image")
    
    status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$status" = "success" ]; then
        echo "✓ Success"
        ((registered++))
    elif [ "$status" = "duplicate" ]; then
        echo "⊘ Already registered"
        ((duplicates++))
    else:
        echo "✗ Error"
        ((errors++))
    fi
done

echo ""
echo "========================================"
echo "REGISTRATION SUMMARY"
echo "========================================"
echo "  Total registered: $registered"
echo "  Duplicates: $duplicates"
echo "  Errors: $errors"
echo "========================================"
