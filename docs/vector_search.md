# Vector Search Integration Plan

## 1. Objective
Enable semantic (“natural-language”) search across the KillrVideo catalogue by leveraging Astra DB’s vector search on the `videos.content_features` column and NVIDIA’s **NV-Embed** model.

* User story*  > As a viewer I can type *“Find me videos about cats that can talk”* in the search box and receive the most relevant videos, ranked by similarity.

## 2. High-level architecture
1. **Client (web / mobile)** – new search box on the landing page.
2. **FastAPI backend**
   • Accepts query at `GET /api/v1/search/videos` (existing path).  
   • Performs ANN search via Data API `$vectorize` on `videos`.
3. **Astra DB**
   • `videos.content_features` is a vector column with NVIDIA integration (COSINE metric).  
   • A dedicated Storage-Attached Index (SAI) drives ANN retrieval.

```
Client ──▶ /api/v1/search/videos?q=... ──▶ FastAPI ──▶ Data API find(sort={"$vectorize": ...}) ──▶ Astra DB
```

## 3. Schema work
| Table | Column | Change | Notes |
|-------|--------|--------|-------|
| `killrvideo.videos` | `content_features` | Alter type to `vector<float, 4096>` (was 16) and attach NVIDIA service | NV-Embed-v2 outputs 4096-dim vectors (HuggingFace card).|

Example Data API alteration (one-off, run from CI or manual):
```jsonc
{
  "alterTable": {
    "name": "videos",
    "addColumns": {
      "content_features": {
        "type": "vector",
        "dimension": 4096,
        "service": {
          "provider": "nvidia",
          "modelName": "NV-Embed-QA"
        }
      }
    }
  }
}
```
The existing SAI needs to be dropped & recreated to match the new dimension:
```cql
DROP INDEX IF EXISTS videos_content_features_idx;
CREATE CUSTOM INDEX videos_content_features_idx
ON killrvideo.videos(content_features)
USING 'StorageAttachedIndex'
WITH OPTIONS = {'similarity_function':'COSINE'};
```

## 4. Data ingestion pipeline
### 4.1 Where
`app/services/video_service.py::submit_new_video()`

### 4.2 How
1. Concatenate title, description and tag list into a single string `embedding_text`.
2. Insert **that string** into `content_features`  – Astra will auto-vectorize via NVIDIA.
3. Keep current list-of-floats fallback for unit-test stub collections.

Pseudo-snippet:
```python
embedding_text = "\n".join([
    new_video.name,
    new_video.description or "",
    " ".join(new_video.tags or []),
])
video_doc["content_features"] = embedding_text  # triggers $vectorize
```

### 4.3 🔒 Token limit guard (512)
According to the NVIDIA integration docs, `$vectorize` payloads **MUST NOT** exceed **512 tokens**.

Implementation guidelines:
* **Helper `clip_to_512_tokens(text: str) -> str`** – rough tokenizer based on whitespace or sentencepiece once provider offers an official tokenizer.
* Apply guard **before** assigning to `video_doc["content_features"]`.
* Apply guard on **search queries** – if the user submits >512-token text, return `400` with validation error or truncate and warn.
* Unit tests: long description (>3000 chars) should be gracefully clipped, insert succeeds.

(The ↩︎ 512-token budget covers title + description + tags, so we may need to drop trailing tokens when the combined string is too long.)

## 5. Search endpoint
### 5.1 Backend Service
New helper `search_videos_by_semantic(query: str, ...)` in `video_service.py`:
```python
db_table.find(
    filter={},
    sort={"$vectorize": query},  # Data API will embed with NV-Embed
    limit=page_size,
)
```
• Pagination: skip/limit still applies.  
• Optional keyword fallback when `$vectorize` fails (e.g. provider quota).

### 5.2 API Layer
`routers/search.py` – route already exists.  
Add query-param `mode` (`semantic|keyword`, default = semantic).

## 6. Front-end (brief)
* Add prominent search input on the home page.  
* On submit → call `/api/v1/search/videos?q=text` → render list using existing `VideoSummary` cards.

## 7. Roll-out strategy
1. **Dev DB**: run alter-table & backfill vectors via bulk update with `$vectorize`.
2. **Backend code**: merge feature branch behind `VECTOR_SEARCH_ENABLED` flag.
3. **Smoke tests**: ensure new inserts generate embeddings & search returns expected order.
4. **Prod**: enable flag, monitor latency & application logs.

## 8. Work items
- [ ] DB migration script (`scripts/migrate_2025_08_vector.sql` or Data API JSON).
- [ ] Code: update `submit_new_video`, create semantic search helper.
- [ ] Unit tests for ingestion & search.
- [ ] API docs / OpenAPI schema tweaks (new param).
- [ ] Front-end search UI.

## 9. Open questions / decisions
1. Which NV-Embed model? (`NV-Embed-QA`, `NV-Embed-v2`?) – default QA variant assumed.
2. Do we persist the raw embedding string for transparency? (Proposed yes – stored in the same column.)
3. Hard‐limit max query length (NVIDIA 512-token)? Need validation in endpoint.

---
*Last updated: 2025-06-16* 