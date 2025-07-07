"""Light-weight helper to retrieve metadata for a YouTube video.

The function ``fetch_youtube_metadata`` is used by ``submit_new_video`` to
populate the *real* title, description, thumbnail and tags immediately at
submission time.

Retrieval strategy (in priority order):

1. **YouTube Data API v3** – requires an API key provided via
   ``YOUTUBE_API_KEY`` environment variable.  Returns rich metadata.
2. **oEmbed endpoint** – public, key-less; returns title & thumbnail only.

If both sources fail or the response is missing a *title*,
``MetadataFetchError`` is raised so the caller can decide how to handle it.
"""

from __future__ import annotations

from typing import List, Optional

import httpx
from pydantic import BaseModel, Field, validator

# Internal config
from app.core.config import settings


class MetadataFetchError(Exception):
    """Raised when YouTube metadata cannot be retrieved."""


class YouTubeMetadata(BaseModel):
    """Canonical representation of the fields we need."""

    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(default=None, alias="thumbnailUrl")
    tags: List[str] = []

    model_config = {
        "populate_by_name": True,
    }

    # Accept either camelCase or snake_case in JSON responses
    @validator("thumbnail_url", pre=True)
    def _cast_thumbnail(cls, value):  # noqa: D401,N805
        if isinstance(value, dict):
            # Data API returns thumbnails dict – choose *maxres* or *high*
            for key in ("maxres", "high", "default"):
                if key in value and value[key].get("url"):
                    return value[key]["url"]
            return None
        return value


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_v3_api(
    youtube_id: str, api_key: str, timeout: float
) -> YouTubeMetadata:
    """Fetch metadata using the official YouTube Data API v3."""

    # ------------------------------------------------------------------
    # Observability – manual span & histogram timing
    # ------------------------------------------------------------------

    from opentelemetry import trace
    import time
    from app.metrics import YOUTUBE_FETCH_DURATION_SECONDS

    tracer = trace.get_tracer(__name__)

    start_time = time.perf_counter()

    with tracer.start_as_current_span("youtube.fetch_v3_api") as span:
        span.set_attribute("youtube.video_id", youtube_id)

        url = (
            "https://www.googleapis.com/youtube/v3/videos?part=snippet"
            f"&id={youtube_id}&key={api_key}"
        )
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise MetadataFetchError(
                    f"Data API returned HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            items = data.get("items") or []
            if not items:
                raise MetadataFetchError(
                    "Video not found or no snippet returned from Data API"
                )

            snippet = items[0].get("snippet") or {}
            result = YouTubeMetadata(
                title=snippet.get("title", ""),
                description=snippet.get("description"),
                thumbnail_url=snippet.get("thumbnails"),  # handled by validator
                tags=snippet.get("tags", []),
            )

            # Record duration & size metrics
            duration = time.perf_counter() - start_time
            YOUTUBE_FETCH_DURATION_SECONDS.labels(method="v3_api").observe(duration)
            span.set_attribute("duration_ms", int(duration * 1000))
            span.set_attribute("title_length", len(result.title))

            return result


async def _fetch_oembed(youtube_id: str, timeout: float) -> YouTubeMetadata:
    """Fetch metadata using YouTube's public oEmbed endpoint."""

    from opentelemetry import trace
    import time
    from app.metrics import YOUTUBE_FETCH_DURATION_SECONDS

    tracer = trace.get_tracer(__name__)

    start_time = time.perf_counter()

    with tracer.start_as_current_span("youtube.fetch_oembed") as span:
        span.set_attribute("youtube.video_id", youtube_id)

        url = (
            "https://www.youtube.com/oembed?format=json&url="
            f"https://youtu.be/{youtube_id}"
        )
        print(f"DEBUG _fetch_oembed: url={url}")
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise MetadataFetchError(
                    f"oEmbed returned HTTP {resp.status_code}: {resp.text[:200]}"
                )
            print(f"DEBUG _fetch_oembed: resp={resp.text}")
            data = resp.json()
            title = data.get("title")
            if not title:
                raise MetadataFetchError("oEmbed response missing title field")
            thumb = (
                data.get("thumbnail_url")
                or f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg"
            )

            result = YouTubeMetadata(
                title=title,
                description=None,  # oEmbed does not provide description
                thumbnail_url=thumb,
                tags=[],
            )

            duration = time.perf_counter() - start_time
            YOUTUBE_FETCH_DURATION_SECONDS.labels(method="oembed").observe(duration)
            span.set_attribute("duration_ms", int(duration * 1000))

            return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch_youtube_metadata(youtube_id: str) -> YouTubeMetadata:  # noqa: D401,E501
    """Return metadata for *youtube_id*.

    The function first attempts the YouTube Data API v3 if ``YOUTUBE_API_KEY``
    is present in the process environment.  If that call fails (network
    error, non-200 response, invalid JSON, etc.) **or** if the key is not
    provided, it falls back to the public oEmbed endpoint.

    Raises
    ------
    MetadataFetchError
        When no method could retrieve *at least* the video title.
    """

    timeout = settings.YOUTUBE_API_TIMEOUT

    api_key = settings.YOUTUBE_API_KEY
    if api_key:
        try:
            return await _fetch_v3_api(youtube_id, api_key, timeout)
        except Exception as exc:  # pragma: no cover – log and fall back
            # Log and fall back to oEmbed. In real setup, use proper logger.
            print(f"Data API fetch failed – falling back to oEmbed. Reason: {exc}")

    # Fallback path – oEmbed
    return await _fetch_oembed(youtube_id, timeout)
