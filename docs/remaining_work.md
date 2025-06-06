# Remaining Work Overview

This document enumerates **all pending or partially-implemented tasks** left in the KillrVideo FastAPI backend after completion of the initial **Polish & Packaging** phase.

## 1 Deferred Logic Place-Holders

| Area | Current State | Outstanding Work |
|------|---------------|------------------|
| **Sentiment Analysis** | `MockSentimentAnalyzer` provides deterministic but naive results. | • Integrate a real NLP model (e.g. Hugging Face `distilbert-sentiment`) or external service.<br>• Cache or batch calls for throughput.<br>• Update unit tests to validate real output expectations. |
| **Video Processing Pipeline** | `process_video_submission` fetches mock metadata and simulates processing. | • Implement YouTube (or generic) metadata fetch via HTTP client.<br>• Download and store thumbnails.<br>• Generate vector embeddings for video title/description (links to §4).<br>• Notify recommendation subsystem when processing completes (event bus or direct call). |
| **Recommendation Engine** | `get_related_videos` & `get_personalized_for_you_videos` return latest videos with random scores. | • Build similarity search based on vector embeddings.<br>• Train or integrate personalised ranking (collaborative filtering, embeddings-based).<br>• Add feature flags & fall-backs for A/B testing. |
| **Vector Embedding Ingestion / Storage** | `ingest_video_embedding` validates video and logs a stub. | • Select vector store (AstraDB vector, Chroma, PGVector, etc.).<br>• Persist embeddings and metadata.<br>• Expose similarity-search API wrapper used by recommendations & search. |
| **Soft-Delete & Restore** | `is_deleted` flag exists; `restore_*` methods just log. | • Ensure delete operations set flag and timestamp.<br>• All list/get queries must filter `is_deleted == False` by default.<br>• Implement restore flows with audit logging & authorization. |

## 2 Advanced Features (Functional-spec "Future Considerations")

1. Analytics & BI metrics collection.
2. Ecosystem event integrations (Kafka/Pulsar topics for new video, rating, etc.).
3. Direct file uploads & video transcoding pipeline.
4. Automated content processing (automatic subtitles, translations).
5. Hybrid RAG search combining vectors with metadata filters.

## 3 Production Hardening

* Structured logging (JSON) with correlation IDs.
* Metrics (Prometheus) & tracing (OpenTelemetry).
* Security enhancements: rate-limiting, stricter validation, security headers, OAuth token scopes.
* Load & performance testing (k6, Locust).
* CI/CD pipelines (GitHub Actions) building Docker images, running tests & linters, pushing to registries.
* Configuration/secret management (Vault, AWS SM, Azure Key Vault).

## 4 Refinement of Existing Code

* Error-handling taxonomy and error-response schema.
* Index review for AstraDB collections (text indexes, vector indexes).
* Code refactoring for clarity; introduce `service_interfaces/` for dependency inversion where appropriate.
* Documentation coverage (OpenAPI descriptions, developer guides).

## 5 Documentation & DX

* Complete API reference in `/docs` (Sphinx or MkDocs).
* Add example Jupyter notebooks for embedding ingestion & querying.
* Provide Postman collection / `curl` examples.

## 6 API Path Discrepancies (Implementation ↔ OpenAPI)

The **OpenAPI contract** in `docs/killrvideo_openapi.yaml` defines several paths that **do not map 1-to-1** to the current FastAPI routers.  These need to be normalised (either update code or adjust the spec).

| Spec Path | Implemented Path | Gap / Action |
|-----------|------------------|--------------|
| `/videos/{videoId}` (GET, PUT) | `/videos/id/{video_id}` | Align paths (remove `id/` prefix) or update spec. |
| `/videos/{videoId}/status` | `/videos/id/{video_id}/status` | Same as above. |
| `/videos/{videoId}/view` | `/videos/id/{video_id}/view` | — |
| `/videos/{videoId}/related` | `/videos/id/{video_id}/related` | — |
| `/videos/by-tag/{tag}` | `/videos/by-tag/{tag_name}` *(matches)* | Variable name differs only; okay. |
| `/users/{userId}/videos` | `/videos/by-uploader/{uploader_id}` | Create users-scoped endpoint or amend spec. |
| `/tags/suggest` | `/search/tags/suggest` | Decide preferred placement; duplicate or move route. |
| `/videos/{videoId}/flags` (POST, GET) | **Missing** | Implement per-video flag list/create endpoints. |
| `/videos/{videoId}/flags/{flagId}` (PATCH) | `/moderation/flags/{flagId}/action` | Spec nests flag under video; implementation uses global path. Harmonise. |

> Until these are reconciled the generated OpenAPI docs will not reflect the actual runtime behaviour, and client SDKs produced from the spec will break.

---

### Roadmap Proposal

| Phase | Key Focus | Duration |
|-------|-----------|----------|
| **Phase 3** | Implement real video processing & embedding generation. | 2 weeks |
| **Phase 4** | Recommendation engine & vector search integration. | 3 weeks |
| **Phase 5** | Soft-delete enforcement & advanced content processing (subtitles, translations). | 2 weeks |
| **Phase 6** | Production hardening (logging, observability, security). | 2 weeks |
| **Phase 7** | Analytics, BI, and ecosystem events. | 2 weeks |
| **Phase 8** | Documentation polish & developer-experience improvements. | 1 week |

> Dates are estimates assuming a 1–2 developer team and may shift based on discovery. 