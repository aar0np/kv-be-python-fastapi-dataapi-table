# Vector Search Implementation – LLM Build Prompts

> This document supplies a **blueprint** and a **chain of reusable prompts** for a code-generation LLM (e.g. Cursor‐GPT) to implement semantic vector search in KillrVideo **incrementally and test-driven**.  
> Every prompt is independent, yet builds on artifacts produced by the previous one. After completing **each** prompt the LLM must:  
> 1. **Run** `ruff --fix`, `black .`, `pytest -q`  (failing tests → iterate).  
> 2. Commit only when the *entire* suite is green.

---

## 0. Glossary & Conventions
* **NV-Embed** = NVIDIA embedding model (4096-dim) with **512-token** input cap.
* **Data API** = Astra DB `$vectorize` endpoint used for vector search.
* **FastAPI app** lives in `app/`.
* **Test helpers** in `tests/` use `pytest` + `pytest-asyncio`.
* Use **feature flag** `settings.VECTOR_SEARCH_ENABLED` (default **False**).
* Use `HTTP 400` for token-limit violations in search/query paths.

---

## 1. High-Level Blueprint (single narrative)
1. **Schema Migration** – enlarge `content_features` column, attach NVIDIA provider, recreate SAI index, & seed backfill.
2. **Ingestion Changes** – on video submit/update, assemble *title + description + tags*, clip to 512 tokens, store as *string* (server vectorises).
3. **Semantic Search** – new helper in `video_service`, integrate into existing `/search/videos` endpoint, add `mode` param.
4. **Pagination & Validation** – respect `page`/`pageSize`, enforce query length ≤ 512 tokens, keyword fallback when semantic disabled.
5. **OpenAPI & Docs** – update schemas + docs.
6. **Front-end Search UI** – add search box & results list, fallback messaging.
7. **Feature Roll-out** – env flag, smoke tests, monitoring hooks.

---

## 2. Iterative Roadmap → Chunks
| Milestone | Chunk | Output |
|-----------|-------|--------|
| M1 Schema | C1.1 DDL script (JSON & CQL) | `migrations/2025_08_vector.sql` & CI-run JSON |
|           | C1.2 Py backfill job | `scripts/backfill_vectors.py` |
| M2 Ingest | C2.1 `clip_to_512_tokens` util + tests | `app/utils/text.py` |
|           | C2.2 Submit flow rewrite | `video_service.py` patched |
| M3 Search | C3.1 Service helper | `search_semantic()` + unit tests |
|           | C3.2 Router wiring | `/api/v1/search/videos` param, tests |
| M4 Docs   | C4.1 OpenAPI regen | updated yaml |
| M5 Front  | C5.1 Home search UI | React component & e2e tests |
| M6 Roll-out | C6.1 Feature flag infra | settings + toggles |

Chunks are intentionally modest (≈1–3 files each, <150 LoC).

---

## 3. Right-Sized Steps (final cut)
1. **Step 1 – Create DB migration & index recreation**  
2. **Step 2 – Backfill existing videos with `$vectorize` bulk update**  
3. **Step 3 – Add `clip_to_512_tokens()` util + tests**  
4. **Step 4 – Modify `submit_new_video()` to store string & guard token count**  
5. **Step 5 – Implement `search_videos_by_semantic()` helper + unit tests**  
6. **Step 6 – Extend search router with `mode` param, integrate helper**  
7. **Step 7 – Update OpenAPI YAML & regenerate client**  
8. **Step 8 – Add feature flag env var + toggling logic**  
9. **Step 9 – Front-end search bar + API wiring (mocked until backend green)**  
10. **Step 10 – Smoke & load tests, rollout script**

Each step below is accompanied by an LLM prompt.

---

## 4. Prompts (feed sequentially)

### Prompt 1 – DB Migration
```text
You are working inside the KillrVideo FastAPI repo.
Goal: **Enlarge the `videos.content_features` column to `vector<float,4096>` and attach the NVIDIA service**. Also drop & recreate the SAI cosine index.
Tasks:
1. Add *migrations/2025_08_vector.cql* containing the necessary `ALTER TABLE`, `DROP INDEX`, `CREATE INDEX` CQL.
2. Add *migrations/2025_08_vector.json* Data API payload (see docs/vector_search.md §3).
3. Register the SQL script in *scripts/migrate.py* so CI picks it up.
4. Unit test: mock Cassandra session; assert index metadata after migration.
After coding run **ruff, black, pytest**. Ensure all tests pass.
```

---

### Prompt 2 – Vector Backfill Job
```text
Goal: **Populate the new 4096-dim vectors for existing rows**.
1. Create *scripts/backfill_vectors.py*.
   • Scan `videos` where `content_features IS NULL` (page size 100).
   • Build text = title + description + tags.
   • POST Data API `updateMany` with `$vectorize`.
2. Provide CLI entry-point `python -m scripts.backfill_vectors --dry-run`.
3. Add unit tests with `responses` to stub Data API.
Run lints/tests until green.
```

---

### Prompt 3 – Token-Clipping Utility
```text
Goal: Guard 512-token NVIDIA limit.
1. Create *app/utils/text.py* with `clip_to_512_tokens(text: str) -> str` using whitespace splitter.
2. Edge-case: consecutive whitespace, Unicode punctuation.
3. Tests: >512 tokens → clipped length ==512, ≤512 unchanged.
Run ruff/black/pytest.
```

---

### Prompt 4 – Ingestion Pipeline Update
```text
Goal: Use auto-vectorize on insert.
1. In *app/services/video_service.py* → function `submit_new_video`:
   • Build `embedding_text` from name/description/tags.
   • Call `clip_to_512_tokens`.
   • Assign string to `content_features` field.
2. Remove legacy 16-float stub path.
3. Add unit tests with `monkeypatch` to verify Data API payload contains **string**, not list.
Run lints/tests.
```

---

### Prompt 5 – Semantic Search Helper
```text
Goal: Backend ANN search wrapper.
1. Add `search_videos_by_semantic(query: str, page:int, page_size:int)` to *video_service.py*.
   • Validate len(query_tokens) ≤512 else raise `InvalidQueryError` (400).
   • Call Data API `find` with `sort:{"$vectorize": query}`.
2. Return list[VideoSummary] preserving existing pagination schema.
3. Tests: stub API, assert ordering & error path.
Run lints/tests.
```

---

### Prompt 6 – API Router Wiring
```text
Goal: Expose semantic mode.
1. In *routers/search.py* add optional `mode: Literal['semantic','keyword']='semantic'`.
2. If `mode=='semantic' and settings.VECTOR_SEARCH_ENABLED` → call helper; else fallback.
3. Update OpenAPI annotations.
4. Tests: both branches, 400 on long query.
Run lints/tests.
```

---

### Prompt 7 – OpenAPI & Client Regen
```text
Goal: Align docs with new behaviour.
1. Update *docs/killrvideo_openapi.yaml* paths `/search/videos` (`mode` param, 400 response).
2. Run generator (`scripts/gen_client.py`) to refresh `client/` stubs.
3. Ensure CI passes.
```

---

### Prompt 8 – Feature Flag Infrastructure
```text
Goal: Toggle vector search safely.
1. Add `VECTOR_SEARCH_ENABLED: bool = False` to *app/core/config.py* (env-driven).
2. Docs update in README & `.env.example`.
3. Unit test: flag off ⇒ helper not called.
Run lints/tests.
```

---

### Prompt 9 – Front-end Search UI
```text
Goal: New search bar (React / Next.js).
1. Create `components/SemanticSearchBar.tsx`.
2. Call backend `/api/v1/search/videos?q=...`.
3. Display results using existing `VideoCard`.
4. Cypress e2e: search term returns expected mock.
Run `npm run lint && npm run test` until green.
```

---

### Prompt 10 – Smoke & Load Tests + Roll-out Script
```text
Goal: Confidence for production switch.
1. Add *tests/e2e/test_semantic_search.py* hitting a staging DB.
2. Add Locust file *load/semantic_search.py* (RPS 20).
3. Create *scripts/enable_vector_flag.py* that flips env + triggers migration.
4. Update GitHub Actions workflow to run load test nightly.
Run lints/tests.
```

---

**End of prompts.**

Once Prompt 10 passes all checks, the vector search feature is fully integrated, tested and ready for production rollout. 