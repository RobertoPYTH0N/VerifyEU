-- Migration: Add image_data column to manifests table
-- Purpose: Store actual image files in the database for retrieval and display

ALTER TABLE manifests 
ADD COLUMN IF NOT EXISTS image_data BYTEA DEFAULT NULL;

-- Add comment to document the column
COMMENT ON COLUMN manifests.image_data IS 'Binary image data (stored as BYTEA)';
