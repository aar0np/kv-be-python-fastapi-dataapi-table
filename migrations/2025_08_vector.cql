-- Set the vector dimension to 384 for IBM Granite embeddings
ALTER TABLE killrvideo.videos ALTER content_features TYPE vector<float, 384>;

-- Drop the existing vector index if present
DROP INDEX IF EXISTS videos_content_features_idx;

-- Recreate the SAI index for the vector column using cosine similarity
CREATE CUSTOM INDEX videos_content_features_idx
ON killrvideo.videos (content_features)
USING 'StorageAttachedIndex'
WITH OPTIONS = {
  'similarity_function': 'COSINE'
}; 