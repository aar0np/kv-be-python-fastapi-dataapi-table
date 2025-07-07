from __future__ import annotations

"""End-to-end smoke test hitting the *staging* KillrVideo deployment.

The test is **skipped automatically** unless the environment variable
``STAGING_BASE_URL`` is provided.  This allows the regular CI unit-test
matrix (which spins up an isolated in-process FastAPI app) to pass
without requiring external connectivity.

When executed with the variable set, the test performs a single semantic
search request and asserts a successful HTTP 200 response plus the
presence of the expected JSON keys.
"""

import os

import pytest
import httpx


STAGING_BASE_URL = os.getenv("STAGING_BASE_URL")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not STAGING_BASE_URL, reason="STAGING_BASE_URL env var not configured"
    ),
]


@pytest.mark.asyncio
async def test_semantic_search_smoke():  # noqa: D401 – simple smoke test
    """Perform a single semantic-mode search and validate basic schema."""

    async with httpx.AsyncClient(base_url=STAGING_BASE_URL, timeout=10) as client:
        resp = await client.get(
            "/api/v1/search/videos", params={"query": "cats", "mode": "semantic"}
        )

    # --- Assertions -------------------------------------------------------
    assert resp.status_code == 200, resp.text

    payload = resp.json()

    # Basic structural checks – we don't lock-step on exact schema here to
    # remain resilient to future extensions, but we do want the core keys.
    assert isinstance(payload, dict)
    assert "data" in payload, "Missing 'data' key in response"
    assert "pagination" in payload, "Missing 'pagination' key in response"

    # Ensure we actually received *some* results in staging (sanity guard).
    assert isinstance(payload["data"], list)
    # We don't enforce a minimum count (could be empty) but the type must hold.
