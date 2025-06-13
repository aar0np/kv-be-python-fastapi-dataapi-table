# YouTube Metadata Fetching – Design Overview

This document explains how KillrVideo's backend fetches and stores
**title, description, thumbnail and tags** for a newly–submitted YouTube
video.  The goal is to populate real data *immediately* when the user
hits **Save**, eliminating the confusing "Generic" placeholder that was
previously shown while a background job processed the record.

---

## 1. High-level flow

```
Client ⇢ POST /videos           ⇢ extract_youtube_video_id(url)
       ⇢ submit_new_video()    ⇢ fetch_youtube_metadata(id)
                                 ├─ Data API v3  (if YOUTUBE_API_KEY)
                                 └─ oEmbed       (fallback)
                              ⇢ build Video model with real metadata
                              ⇢ INSERT videos, latest_videos tables
                              ⇢ enqueue heavy background tasks (captions, AI, …)
```

* The new **`fetch_youtube_metadata`** helper is a small, standalone
  module under `app/external_services/`.  It returns a pydantic model
  with the normalised fields we need.  The helper is *async* and uses
  `httpx.AsyncClient` under the hood.
* A typical submission now completes in **≈200-450 ms** instead of the
  ~15 ms we had before, but the UX gain (instant real title/thumbnail)
  outweighs the added latency.

---

## 2. Retrieval options

| Priority | Method                         | Requires key | Fields returned                         |
|----------|--------------------------------|--------------|-----------------------------------------|
| 1        | **YouTube Data API v3**        | ✔            | title, description, tags, thumbnails, … |
| 2        | **oEmbed endpoint**            | ✖            | title, author, thumbnail                |
| 3*       | HTML scraping (not implemented)| ✖            | title (best-effort)                     |

\* Scraping is brittle; we prefer not to ship it unless both API paths
  become unusable.

### 2.1 Data API v3

```
GET https://www.googleapis.com/youtube/v3/videos
        ?part=snippet,contentDetails
        &id=<VIDEO_ID>
        &key=$YOUTUBE_API_KEY
```

*Quota*: 1 unit per call (~10 000 free units/day).

### 2.2 oEmbed (key-less)

```
GET https://www.youtube.com/oembed
        ?url=https://youtu.be/<VIDEO_ID>
        &format=json
```

Fast, public, but returns only a subset of fields.

---

## 3. Configuration flags

All values are read from environment variables; sensible defaults are
used when unset.

| Variable                  | Default | Purpose                                                 |
|---------------------------|---------|---------------------------------------------------------|
| `YOUTUBE_API_KEY`         | *None*  | Enables Data API calls when provided.                   |
| `YOUTUBE_API_TIMEOUT`     | `3.0`   | Per-request timeout in seconds for both API & oEmbed.   |
| `INLINE_METADATA_DISABLED`| `false` | When `true`, skip inline fetch and fall back to the old
|                           |         | background-task flow.                                   |

---

## 4. Error handling

1. If metadata cannot be fetched within the timeout or YouTube returns a
   non-200 status, the helper raises `MetadataFetchError`.
2. `submit_new_video` translates this into `HTTP 502 Bad Gateway` so the
   client can show "Couldn't retrieve video details – please try again".
3. Unit tests stub the helper to avoid real network calls.

---

## 5. Rollback & emergency switch-off

* **Quick toggle** – set `INLINE_METADATA_DISABLED=true` in the runtime
  environment.  The service will revert to the previous behaviour (insert
  placeholder record and queue the background processor).
* **Full rollback** – redeploy the previous Git tag.  No schema changes
  were required for the new flow, so this is safe.

---

## 6. Future extensions

* Cache successful responses in Redis (TTL 24 h) to save quota and shave
  ~100 ms off subsequent submissions of the same video.
* Extend `fetch_youtube_metadata` to also pull duration and category
  fields once the database schema is updated to hold them.
* Replace oEmbed with a tiny self-hosted proxy service if YouTube ever
  rate-limits oEmbed heavily. 