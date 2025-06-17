-- Increase the vector dimension to 4096 and attach the NVIDIA embedding service
ALTER TABLE killrvideo.videos ALTER content_features TYPE vector<float, 4096>;

-- Drop the existing vector index if present
DROP INDEX IF EXISTS videos_content_features_idx;

-- Recreate the SAI index for the enlarged vector column using cosine similarity
CREATE CUSTOM INDEX videos_content_features_idx
ON killrvideo.videos (content_features)
USING 'StorageAttachedIndex'
WITH OPTIONS = {
  'similarity_function': 'COSINE'
}; 