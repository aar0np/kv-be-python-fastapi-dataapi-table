# Acceptance-Testing Plan

This document defines **high-level acceptance criteria** and test-scenarios for the KillrVideo FastAPI backend.  Each feature must satisfy the listed checks before it is deemed *production-ready*.

> NOTE  These scenarios complement unit-tests; they focus on *end-to-end* behaviour through the HTTP API or via background tasks.

---

## 1 Video Processing

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| **Submit video URL** | POST `/videos` with valid YouTube URL while authenticated as *creator*. | • Response `201` with `status=PENDING`.<br>• Background task enqueues processing. |
| **Processing succeeds** | Wait (simulate) until background task completes. | • GET `/videos/{id}` returns `status=READY`.<br>• Title, description & thumbnail populated.<br>• Audit log entry recorded. |
| **Processing fails** | Provide bad or unreachable YouTube ID. | • Final status `ERROR` with explanatory title.<br>• No thumbnail stored. |

## 2 Comment Sentiment Analysis

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| **Positive sentiment** | POST `/videos/{id}/comments` with text *"Love it!"*. | Comment object contains `sentiment="positive"`. |
| **Negative sentiment** | POST with text containing sad emoji. | `sentiment="negative"`. |
| **Indeterminate** | Very short or ambiguous text. | `sentiment` nullable (None). |

## 3 Recommendation Service

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| **Related videos** | GET `/videos/{id}/related?limit=5`. | 5 items, none equal to source video, each with `score∈[0,1]`. |
| **Personalized feed** | GET `/users/{id}/for-you` (authenticated). | Paginated list reflecting user-preferences (once implemented). |

## 4 Vector Embedding Ingestion

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| **Ingest vector** | POST `/embeddings` JSON with `videoId` & `vector` of correct dimension. | Response `{status:"received"}`.<br>Embedding stored in vector DB. |
| **Unknown video** | Same call with non-existent `videoId`. | Response `{status:"error"}` + 404 in HTTP layer. |

## 5 Soft-Delete & Restore

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| **Soft-delete video** | Moderator PATCH `/videos/{id}` `{is_deleted:true}`. | `is_deleted` flagged; listing endpoints omit video. |
| **Restore video** | POST `/videos/{id}/restore`. | Video visible again; audit trail updated. |
| **Soft-delete comment** | Similar flows for `/comments/{id}`. | — |

## 6 Security & Auth

* All modifying endpoints require JWT with proper role (creator, moderator).
* Rate-limiting (e.g. 100 requests/min) enforced; excess results in `429`.
* CSRF/Click-jacking headers present.

## 7 Observability

* Every request logged with `trace_id` & caller IP.
* Prometheus metrics `/metrics` endpoint exposes request-duration histogram.

## 8 Performance Benchmarks

* **Submit video** median latency ≤ 200 ms (excluding background work).
* **List latest videos** p95 latency ≤ 120 ms for 100 k videos.

---

### Exit-Criteria Summary

1. All above scenarios automated (Playwright, pytest-httpx, or k6).
2. CI pipeline green on pull-request (unit + acceptance tests + lint).
3. Documentation updated and reviewed.

A release cannot ship unless each criterion passes on the staging environment.  