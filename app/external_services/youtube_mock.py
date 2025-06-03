from __future__ import annotations

"""A mocked YouTube service used during development and testing.

This mock simulates minimal interactions required by the background video
processing task without performing any real HTTP requests.
"""

from typing import Optional, Dict, Any


class MockYouTubeService:
    """Return mocked metadata for provided YouTube video IDs."""

    async def get_video_details(self, youtube_video_id: str) -> Optional[Dict[str, Any]]:  # noqa: D401,E501
        """Fetch mocked video details.

        Parameters
        ----------
        youtube_video_id:
            The 11-character YouTube video identifier extracted from the URL.

        Returns
        -------
        dict | None
            A dictionary of video metadata or ``None`` if the ID is considered
            invalid.
        """

        print(f"MOCK YOUTUBE: Fetching details for {youtube_video_id}")

        if youtube_video_id == "known_good_id":
            return {
                "title": "Epic Mock Video Title",
                "description": "This is a fantastic video about mocking.",
                "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "duration_seconds": 212,
            }
        if youtube_video_id == "known_bad_id":
            return None

        # Generic fallback for any other ID – treat as a valid generic video
        return {
            "title": f"Generic Video {youtube_video_id}",
            "description": "A generic description.",
            "thumbnail_url": "https://example.com/generic_thumb.jpg",
            "duration_seconds": 120,
        } 